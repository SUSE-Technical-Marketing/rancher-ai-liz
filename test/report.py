#!/usr/bin/env python3
"""
Generate an HTML report of Liz test runs for easy viewing and comparison.

Usage:
  python report.py                         # All runs in results/
  python report.py results/run-a results/run-b   # Specific runs only
  python report.py --list                  # Just print a summary table to stdout
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime


def load_run(run_dir: Path) -> dict | None:
    summary_file = run_dir / "summary.json"
    results_file = run_dir / "results.json"
    if not summary_file.exists():
        return None
    summary = json.loads(summary_file.read_text())
    results = json.loads(results_file.read_text()) if results_file.exists() else []
    return {"dir": run_dir, "summary": summary, "results": results}


def fmt(val, suffix="s"):
    return f"{val:.1f}{suffix}" if val is not None else "—"


def model_label(summary: dict) -> str:
    llm = summary.get("llm", {})
    if llm:
        return f"{llm.get('active','?')} / {llm.get('model','?')}"
    return summary.get("run_label", run_dir_name(summary))


def run_dir_name(summary: dict) -> str:
    return summary.get("run_label", summary.get("timestamp", "")[:19])


def print_table(runs: list[dict]):
    """Print a quick summary table to stdout."""
    # Collect all question names in order
    all_questions = []
    seen = set()
    for run in runs:
        for q in run["summary"].get("questions", []):
            if q["name"] not in seen:
                all_questions.append(q["name"])
                seen.add(q["name"])

    col = 34
    print(f"\n{'Run':<25} {'Model':<30} {'Date':<12} {'Tests':>5} {'Pass':>5}")
    print("-" * 80)
    for run in runs:
        s = run["summary"]
        qs = s.get("questions", [])
        passed = sum(1 for q in qs if q["success_count"] == q["repetitions"])
        date = s.get("timestamp", "")[:10]
        print(f"{run['dir'].name[:24]:<25} {model_label(s)[:29]:<30} {date:<12} {len(qs):>5} {passed:>5}")

    print(f"\n{'Test':<{col}}", end="")
    for run in runs:
        label = run["summary"].get("run_label", run["dir"].name)[:12]
        print(f" {'TTFT':>6} {'Total':>7}", end="")
    print()
    print("-" * (col + len(runs) * 15))

    for name in all_questions:
        print(f"{name[:col-1]:<{col}}", end="")
        for run in runs:
            q = next((q for q in run["summary"].get("questions", []) if q["name"] == name), None)
            if q:
                ttft = fmt(q["ttft_stats"].get("avg"))
                total = fmt(q["total_time_stats"].get("avg"))
                ok = q["success_count"] == q["repetitions"]
                marker = " " if ok else "!"
                print(f"{marker}{ttft:>6} {total:>7}", end="")
            else:
                print(f"  {'—':>6} {'—':>7}", end="")
        print()


def escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_response(resp: str) -> str:
    """Render a response, highlighting MCP data blocks."""
    import re
    def replace_mcp(m):
        try:
            data = json.loads(m.group(1))
            rows = "".join(
                f"<tr><td>{escape(d.get('cluster',''))}</td><td>{escape(d.get('namespace',''))}</td>"
                f"<td>{escape(d.get('kind',''))}</td><td>{escape(d.get('name',''))}</td></tr>"
                for d in data if isinstance(d, dict)
            )
            return (
                f'<details class="mcp"><summary>MCP data ({len(data)} resources)</summary>'
                f'<table><tr><th>Cluster</th><th>NS</th><th>Kind</th><th>Name</th></tr>{rows}</table></details>'
            )
        except Exception:
            return f'<details class="mcp"><summary>MCP data</summary><pre>{escape(m.group(1)[:500])}</pre></details>'

    resp = re.sub(r'<mcp-response>(.*?)</mcp-response>', replace_mcp, resp, flags=re.DOTALL)
    # Render markdown-ish: code blocks
    resp = re.sub(r'```(\w*)\n(.*?)```', lambda m: f'<pre class="code"><code>{escape(m.group(2))}</code></pre>', resp, flags=re.DOTALL)
    # Bold
    resp = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', resp)
    # Headers
    resp = re.sub(r'^### (.+)$', r'<h4>\1</h4>', resp, flags=re.MULTILINE)
    resp = re.sub(r'^## (.+)$', r'<h3>\1</h3>', resp, flags=re.MULTILINE)
    resp = re.sub(r'^# (.+)$', r'<h2>\1</h2>', resp, flags=re.MULTILINE)
    # Suggestions
    resp = re.sub(r'<suggestion>(.*?)</suggestion>', r'<span class="suggestion">💡 \1</span>', resp)
    # Newlines
    resp = resp.replace('\n', '<br>')
    return resp


def generate_html(runs: list[dict], output: Path):
    all_questions = []
    seen = set()
    for run in runs:
        for q in run["summary"].get("questions", []):
            if q["name"] not in seen:
                all_questions.append(q["name"])
                seen.add(q["name"])

    # Index results by (run_dir, test_name, run_number)
    def get_results(run, test_name):
        return [r for r in run["results"] if r.get("test_name") == test_name]

    run_labels = [run["summary"].get("run_label", run["dir"].name) for run in runs]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Liz Test Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #f5f5f5; color: #333; }}
  h1 {{ background: #1a1a2e; color: white; margin: 0; padding: 16px 24px; font-size: 1.2rem; }}
  .runs-bar {{ display: flex; gap: 12px; padding: 12px 24px; background: #16213e; flex-wrap: wrap; }}
  .run-chip {{ background: #0f3460; color: #e0e0e0; border-radius: 6px; padding: 6px 12px; font-size: 0.85rem; }}
  .run-chip strong {{ color: #4fc3f7; }}
  .summary-table {{ margin: 16px 24px; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); width: calc(100% - 48px); }}
  .summary-table th {{ background: #1a1a2e; color: white; padding: 8px 12px; text-align: left; font-size: 0.8rem; }}
  .summary-table td {{ padding: 7px 12px; border-bottom: 1px solid #eee; font-size: 0.85rem; }}
  .summary-table tr:last-child td {{ border-bottom: none; }}
  .summary-table tr:hover td {{ background: #f0f4ff; }}
  .ok {{ color: #2e7d32; font-weight: 600; }}
  .fail {{ color: #c62828; font-weight: 600; }}
  .slower {{ color: #e65100; }}
  .faster {{ color: #2e7d32; }}
  .test-section {{ margin: 16px 24px; }}
  .test-header {{ background: #1a1a2e; color: white; padding: 10px 16px; border-radius: 6px 6px 0 0; font-weight: 600; font-size: 0.95rem; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
  .test-header:hover {{ background: #16213e; }}
  .test-body {{ background: white; border: 1px solid #ddd; border-top: none; border-radius: 0 0 6px 6px; }}
  .question-text {{ padding: 10px 16px; font-style: italic; color: #555; border-bottom: 1px solid #eee; font-size: 0.9rem; }}
  .runs-grid {{ display: grid; gap: 0; }}
  .run-col {{ border-right: 1px solid #eee; }}
  .run-col:last-child {{ border-right: none; }}
  .run-header {{ background: #f8f9fa; padding: 8px 14px; font-size: 0.8rem; font-weight: 600; color: #555; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }}
  .response-block {{ padding: 10px 14px; border-bottom: 1px solid #f0f0f0; font-size: 0.82rem; line-height: 1.5; }}
  .response-block:last-child {{ border-bottom: none; }}
  .run-num {{ font-size: 0.75rem; color: #888; margin-bottom: 4px; }}
  .timing {{ font-size: 0.75rem; color: #666; margin-bottom: 6px; }}
  details.mcp {{ margin: 4px 0; }}
  details.mcp summary {{ cursor: pointer; color: #1565c0; font-size: 0.78rem; }}
  details.mcp table {{ font-size: 0.75rem; border-collapse: collapse; margin-top: 4px; }}
  details.mcp th, details.mcp td {{ border: 1px solid #ddd; padding: 3px 6px; }}
  details.mcp th {{ background: #e3f2fd; }}
  pre.code {{ background: #f5f5f5; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 0.78rem; margin: 4px 0; white-space: pre-wrap; }}
  .suggestion {{ display: inline-block; background: #e8f5e9; color: #1b5e20; border-radius: 4px; padding: 2px 8px; margin: 2px; font-size: 0.78rem; }}
  .no-data {{ color: #aaa; font-style: italic; padding: 10px 14px; }}
  .badge {{ display: inline-block; border-radius: 4px; padding: 1px 6px; font-size: 0.75rem; font-weight: 600; }}
  .badge-ok {{ background: #e8f5e9; color: #2e7d32; }}
  .badge-fail {{ background: #ffebee; color: #c62828; }}
  .delta {{ font-size: 0.75rem; margin-left: 6px; }}
</style>
</head>
<body>
<h1>🤖 Liz AI Agent — Test Report</h1>

<div class="runs-bar">
"""

    for i, run in enumerate(runs):
        s = run["summary"]
        llm = s.get("llm", {})
        model_str = f"{llm.get('active','?')} / {llm.get('model','?')}" if llm else "unknown"
        date = s.get("timestamp", "")[:16].replace("T", " ")
        label = s.get("run_label", run["dir"].name)
        html += f'<div class="run-chip"><strong>Run {i+1}: {escape(label)}</strong><br>{escape(model_str)}<br><span style="opacity:.7">{date}</span></div>\n'

    html += "</div>\n\n"

    # Summary timing table
    html += '<table class="summary-table">\n<thead><tr><th>Test</th>'
    for i, run in enumerate(runs):
        label = run["summary"].get("run_label", run["dir"].name)
        html += f'<th colspan="2">Run {i+1}: {escape(label[:20])}<br><span style="font-weight:normal;font-size:.75rem">{escape(run["summary"].get("llm",{}).get("model","")[:20])}</span></th>'
    html += "</tr>\n<tr><th></th>"
    for _ in runs:
        html += "<th>TTFT avg</th><th>Total avg</th>"
    html += "</tr></thead>\n<tbody>\n"

    for name in all_questions:
        html += f"<tr><td><strong>{escape(name)}</strong></td>"
        row_vals = []
        for run in runs:
            q = next((q for q in run["summary"].get("questions", []) if q["name"] == name), None)
            row_vals.append(q)

        for idx, q in enumerate(row_vals):
            if q is None:
                html += "<td>—</td><td>—</td>"
                continue
            ok = q["success_count"] == q["repetitions"]
            badge = f'<span class="badge badge-{"ok" if ok else "fail"}">{q["success_count"]}/{q["repetitions"]}</span>'
            ttft = q["ttft_stats"].get("avg")
            total = q["total_time_stats"].get("avg")

            # Delta vs first run
            def delta_html(val, base_val):
                if val is None or base_val is None or idx == 0:
                    return ""
                pct = ((val - base_val) / base_val) * 100
                cls = "faster" if pct < -5 else "slower" if pct > 5 else ""
                sign = "+" if pct > 0 else ""
                return f'<span class="delta {cls}">{sign}{pct:.0f}%</span>'

            base_q = row_vals[0]
            base_ttft = base_q["ttft_stats"].get("avg") if base_q else None
            base_total = base_q["total_time_stats"].get("avg") if base_q else None

            html += f"<td>{fmt(ttft)}{delta_html(ttft, base_ttft)} {badge}</td><td>{fmt(total)}{delta_html(total, base_total)}</td>"
        html += "</tr>\n"

    html += "</tbody></table>\n\n"

    # Per-test response sections
    for name in all_questions:
        # Find the question text
        question_text = ""
        for run in runs:
            q = next((q for q in run["summary"].get("questions", []) if q["name"] == name), None)
            if q:
                question_text = q.get("message", "")
                break

        grid_cols = f"repeat({len(runs)}, 1fr)"
        html += f'''<div class="test-section">
<div class="test-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">
  <span>{escape(name)}</span>
  <span style="font-size:.8rem;font-weight:normal">click to expand ▼</span>
</div>
<div class="test-body" style="display:none">
  <div class="question-text">❓ {escape(question_text)}</div>
  <div class="runs-grid" style="grid-template-columns:{grid_cols}">
'''
        for i, run in enumerate(runs):
            label = run["summary"].get("run_label", run["dir"].name)
            results = get_results(run, name)
            q = next((q for q in run["summary"].get("questions", []) if q["name"] == name), None)
            ttft_avg = fmt(q["ttft_stats"].get("avg")) if q else "—"
            total_avg = fmt(q["total_time_stats"].get("avg")) if q else "—"
            success = f'{q["success_count"]}/{q["repetitions"]}' if q else "—"

            html += f'<div class="run-col"><div class="run-header"><span>Run {i+1}: {escape(label[:20])}</span><span>TTFT {ttft_avg} | Total {total_avg} | {success} ok</span></div>\n'
            if results:
                for r in results:
                    ttft_s = fmt(r.get("ttft"))
                    total_s = fmt(r.get("total_time"))
                    ok = r.get("success", False)
                    badge = f'<span class="badge badge-{"ok" if ok else "fail"}">{"OK" if ok else "FAIL"}</span>'
                    rendered = render_response(r.get("response", ""))
                    err = f'<div style="color:#c62828;font-size:.75rem">⚠ {escape(str(r.get("error","")))}</div>' if r.get("error") else ""
                    html += f'<div class="response-block"><div class="run-num">Run #{r["run_number"]} {badge}</div><div class="timing">TTFT {ttft_s} · Total {total_s}</div>{err}{rendered}</div>\n'
            else:
                html += '<div class="no-data">No data for this run</div>\n'
            html += "</div>\n"

        html += "</div></div></div>\n\n"

    html += f"""<div style="text-align:center;color:#aaa;font-size:.75rem;padding:16px">
Generated {datetime.now().strftime("%Y-%m-%d %H:%M")} · {len(runs)} run(s) · {len(all_questions)} test(s)
</div>
</body></html>"""

    output.write_text(html)
    print(f"Report written to: {output}")


def main():
    parser = argparse.ArgumentParser(description="View and compare Liz test results")
    parser.add_argument("runs", nargs="*", help="Run directories to include (default: all in results/)")
    parser.add_argument("--results-dir", default="results", help="Base results directory")
    parser.add_argument("--list", action="store_true", help="Print summary table to stdout only")
    parser.add_argument("--out", default="report.html", help="Output HTML file (default: report.html)")
    args = parser.parse_args()

    base = Path(args.results_dir)

    if args.runs:
        run_dirs = [Path(r) for r in args.runs]
    else:
        run_dirs = sorted([d for d in base.iterdir() if d.is_dir() and (d / "summary.json").exists()])

    if not run_dirs:
        print("No runs found.")
        return

    runs = [r for d in run_dirs if (r := load_run(d)) is not None]

    if not runs:
        print("No valid runs found.")
        return

    print_table(runs)

    if not args.list:
        generate_html(runs, Path(args.out))
        import subprocess
        subprocess.run(["open", args.out], check=False)


if __name__ == "__main__":
    main()
