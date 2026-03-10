#!/usr/bin/env python3
"""
Liz AI Agent Test Runner

Sends questions to the Rancher AI agent (Liz) via WebSocket, measures
time to first token (TTFT) and total response time, and logs results.

Usage:
  python liz-test.py                           # Run with tests.yaml
  python liz-test.py --config custom.yaml      # Custom test config
  python liz-test.py --label "qwen3.5-27b"     # Label this run for comparison
  python liz-test.py --no-portforward          # If port-forward already running
  python liz-test.py --tests crash,broken-image  # Run specific tests by name
"""

import asyncio
import csv
import json
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

try:
    import websockets
except ImportError:
    print("Missing dependency: pip install websockets")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("Missing dependency: pip install pyyaml")
    sys.exit(1)

KUBECONFIG = os.path.expanduser("~/.kube/liz.yaml")
KUBE_CONTEXT = "rancher"


def get_token_from_kubeconfig(kubeconfig_path: str = KUBECONFIG) -> str | None:
    """Extract the Bearer token from the kubeconfig file."""
    try:
        with open(kubeconfig_path) as f:
            kc = yaml.safe_load(f)
        for user in kc.get("users", []):
            token = user.get("user", {}).get("token")
            if token:
                return token
    except Exception:
        pass
    return None
RANCHER_HOST = "liz.dna-42.com"
# WebSocket via Rancher API proxy — provides proper auth + cluster access
WS_URL = (
    f"wss://{RANCHER_HOST}/k8s/clusters/local/api/v1/namespaces/"
    f"cattle-ai-agent-system/services/http:rancher-ai-agent:80/proxy/v1/ws/messages"
)


def get_llm_config() -> dict:
    """Read current LLM config from the cluster configmap and secret."""
    try:
        import subprocess
        cm = subprocess.run(
            ["kubectl", f"--kubeconfig={KUBECONFIG}", f"--context={KUBE_CONTEXT}",
             "get", "configmap", "llm-config", "-n", "cattle-ai-agent-system",
             "-o", "jsonpath={.data}"],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(cm.stdout) if cm.returncode == 0 else {}
        # Decode OLLAMA_URL from secret
        sec = subprocess.run(
            ["kubectl", f"--kubeconfig={KUBECONFIG}", f"--context={KUBE_CONTEXT}",
             "get", "secret", "llm-secret", "-n", "cattle-ai-agent-system",
             "-o", "jsonpath={.data.OLLAMA_URL}"],
            capture_output=True, text=True, timeout=10
        )
        if sec.returncode == 0 and sec.stdout:
            import base64
            data["OLLAMA_URL"] = base64.b64decode(sec.stdout).decode()
        return data
    except Exception:
        return {}


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


async def run_query(token: str, message: str, agent_id: str = "rancher", context: dict = None, timeout: float = 120) -> dict:
    """Send a message to Liz and record TTFT, total time, and full response."""
    # Auth via R_SESS cookie (how the Rancher UI authenticates)
    cookies = {"R_SESS": token}
    result = {
        "message": message,
        "agent_id": agent_id,
        "context": context or {},
        "success": False,
        "ttft": None,
        "total_time": None,
        "response": "",
        "chat_id": None,
        "error": None,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    try:
        async with websockets.connect(
            WS_URL,
            additional_headers={
                # Authorization: for Rancher API proxy authentication
                "Authorization": f"Bearer {token}",
                # R_SESS cookie: for the AI agent's per-request user validation
                "Cookie": f"R_SESS={token}",
            },
            open_timeout=15,
            ping_interval=30,
            ping_timeout=30,
        ) as ws:
            # Server expects "prompt" and "agent" (not "message"/"agentId")
            # "context" dict gets injected into the prompt for MCP tool parameter hints
            payload = json.dumps({"prompt": message, "agent": agent_id, "context": context or {}})
            send_time = time.perf_counter()
            await ws.send(payload)

            in_message = False
            full_text = ""
            ttft = None

            while True:
                try:
                    chunk = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    now = time.perf_counter()
                    elapsed = now - send_time

                    if chunk.startswith("<chat-metadata>"):
                        try:
                            meta_str = chunk.replace("<chat-metadata>", "").replace("</chat-metadata>", "")
                            meta = json.loads(meta_str)
                            result["chat_id"] = meta.get("chatId")
                        except Exception:
                            pass

                    elif chunk == "<message>":
                        in_message = True

                    elif chunk == "</message>":
                        result["total_time"] = round(elapsed, 3)
                        result["response"] = full_text
                        result["success"] = True
                        break

                    elif chunk.startswith("<error>"):
                        result["error"] = chunk
                        result["response"] = full_text
                        break

                    elif in_message:
                        if ttft is None:
                            ttft = round(elapsed, 3)
                            result["ttft"] = ttft
                        full_text += chunk

                except asyncio.TimeoutError:
                    result["error"] = f"Timeout after {timeout}s"
                    if full_text:
                        result["response"] = full_text
                        result["success"] = True  # partial success
                    break

                except websockets.exceptions.ConnectionClosed as e:
                    result["error"] = f"Connection closed: {e}"
                    if full_text:
                        result["response"] = full_text
                    break

    except Exception as e:
        result["error"] = str(e)

    return result


def fmt_time(val):
    return f"{val:.2f}s" if val is not None else "N/A"


def stats(vals):
    if not vals:
        return {"min": None, "max": None, "avg": None, "count": 0}
    return {
        "min": round(min(vals), 3),
        "max": round(max(vals), 3),
        "avg": round(sum(vals) / len(vals), 3),
        "count": len(vals),
    }


async def run_test_suite(config: dict, results_dir: Path, label: str = "", test_filter: list = None) -> dict:
    token = config["token"]
    agent_id = config.get("agent_id", "rancher")
    default_reps = config.get("default_repetitions", 3)
    query_delay = config.get("delay_between_queries", 1)

    tests = config.get("tests", [])
    if test_filter:
        tests = [t for t in tests if t["name"] in test_filter]
        if not tests:
            print(f"No tests matched filter: {test_filter}")
            return {}

    all_results = []
    llm_config = get_llm_config()
    summary = {
        "run_label": label,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "config_file": str(config.get("_source", "")),
        "llm": {
            "active": llm_config.get("ACTIVE_LLM", "unknown"),
            "model": llm_config.get("OLLAMA_MODEL") or llm_config.get("OPENAI_MODEL") or llm_config.get("GEMINI_MODEL") or "unknown",
            "ollama_url": llm_config.get("OLLAMA_URL", ""),
        },
        "agent_config": {
            "agent_id": agent_id,
            "default_repetitions": default_reps,
        },
        "questions": [],
    }

    total_tests = len(tests)
    for test_idx, test in enumerate(tests, 1):
        name = test["name"]
        message = test["message"]
        repetitions = test.get("repetitions", default_reps)
        test_agent_id = test.get("agent_id", agent_id)

        print(f"\n[{test_idx}/{total_tests}] {name}")
        print(f"  Q: {message[:90]}{'...' if len(message) > 90 else ''}")
        print(f"  Runs: {repetitions}")

        question_results = []
        ttfts = []
        totals = []

        test_context = test.get("context", {})

        for i in range(1, repetitions + 1):
            result = await run_query(token, message, test_agent_id, context=test_context)
            result["test_name"] = name
            result["run_number"] = i

            status = "OK" if result["success"] else "FAIL"
            ttft_s = fmt_time(result["ttft"])
            total_s = fmt_time(result["total_time"])
            print(f"  Run {i}/{repetitions}: [{status}] TTFT={ttft_s}  Total={total_s}", end="")
            if result["error"]:
                print(f"  Error: {result['error']}", end="")
            print()

            question_results.append(result)
            all_results.append(result)

            if result["ttft"] is not None:
                ttfts.append(result["ttft"])
            if result["total_time"] is not None:
                totals.append(result["total_time"])

            if i < repetitions:
                await asyncio.sleep(query_delay)

        ttft_stats = stats(ttfts)
        total_stats = stats(totals)
        success_count = sum(1 for r in question_results if r["success"])

        print(f"  Summary: {success_count}/{repetitions} succeeded")
        if ttft_stats["count"] > 0:
            print(f"  TTFT:  min={fmt_time(ttft_stats['min'])}  avg={fmt_time(ttft_stats['avg'])}  max={fmt_time(ttft_stats['max'])}")
        if total_stats["count"] > 0:
            print(f"  Total: min={fmt_time(total_stats['min'])}  avg={fmt_time(total_stats['avg'])}  max={fmt_time(total_stats['max'])}")

        summary["questions"].append({
            "name": name,
            "message": message,
            "repetitions": repetitions,
            "success_count": success_count,
            "ttft_stats": ttft_stats,
            "total_time_stats": total_stats,
        })

    # Save results
    results_dir.mkdir(parents=True, exist_ok=True)

    with open(results_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    with open(results_dir / "results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    csv_file = results_dir / "results.csv"
    fields = ["timestamp", "test_name", "run_number", "success", "ttft", "total_time", "error", "response"]
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)

    print(f"\n{'='*60}")
    print(f"Results saved to: {results_dir}/")
    print(f"  summary.json   - timing stats per question")
    print(f"  results.json   - full responses + raw timing")
    print(f"  results.csv    - spreadsheet format")

    return summary


def print_summary_table(summary: dict):
    """Print a final timing table after the run."""
    questions = summary.get("questions", [])
    if not questions:
        return

    print(f"\n{'='*60}")
    print(f"TIMING SUMMARY  (label: {summary.get('run_label', 'unlabeled')})")
    print(f"{'='*60}")
    print(f"{'Test':<35} {'Success':>7} {'TTFT avg':>9} {'Total avg':>10}")
    print(f"{'-'*35} {'-'*7} {'-'*9} {'-'*10}")
    for q in questions:
        name = q["name"][:34]
        ok = f"{q['success_count']}/{q['repetitions']}"
        ttft = fmt_time(q["ttft_stats"].get("avg"))
        total = fmt_time(q["total_time_stats"].get("avg"))
        print(f"{name:<35} {ok:>7} {ttft:>9} {total:>10}")


def main():
    parser = argparse.ArgumentParser(description="Test the Liz (Rancher AI) agent")
    parser.add_argument("--config", default="tests.yaml", help="Test config file (default: tests.yaml)")
    parser.add_argument("--label", default="", help="Label this run for comparison (e.g. model name)")
    parser.add_argument("--results-dir", default="results", help="Base directory for results (default: results/)")
    parser.add_argument("--tests", help="Comma-separated list of test names to run (default: all)")
    parser.add_argument("--timeout", type=float, default=120, help="Per-query timeout in seconds (default: 120)")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        sys.exit(1)

    config = load_config(str(config_path))
    config["_source"] = str(config_path)

    # Token resolution: config file > environment variable > kubeconfig
    if not config.get("token"):
        config["token"] = os.environ.get("LIZ_TOKEN") or get_token_from_kubeconfig()
    if not config.get("token"):
        print("Error: no token found. Set 'token' in config, LIZ_TOKEN env var, or ensure ~/.kube/liz.yaml has a token.")
        sys.exit(1)

    test_filter = [t.strip() for t in args.tests.split(",")] if args.tests else None

    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    label_slug = f"-{args.label.replace(' ', '_')}" if args.label else ""
    results_dir = Path(args.results_dir) / f"{ts}{label_slug}"

    try:
        print(f"\nConfig:  {config_path}")
        if args.label:
            print(f"Label:   {args.label}")
        print(f"Results: {results_dir}/")
        print(f"Agent:   {WS_URL}")

        summary = asyncio.run(run_test_suite(config, results_dir, args.label, test_filter))
        print_summary_table(summary)

    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        pass


if __name__ == "__main__":
    main()
