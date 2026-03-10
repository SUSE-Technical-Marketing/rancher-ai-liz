# Liz AI Agent Test Suite

Automated testing for the Rancher AI agent (Liz). Sends questions via WebSocket, measures **time to first token (TTFT)** and **total response time**, and logs full responses for quality review.

## Setup

```bash
cd test/
pip install -r requirements.txt
```

Requires Python 3.10+, `~/.kube/liz.yaml` with a valid Rancher token.

---

## Running Tests

### Full test suite
```bash
python liz-test.py --label "model-name"
```

### Specific tests only
```bash
python liz-test.py --tests crash-loop-diagnosis,broken-image-diagnosis --label "my-run"
```

### After changing the model
```bash
# 1. Switch the model
./set-model.sh --model llama3.3:70b

# 2. Run the same tests with a new label
python liz-test.py --label "llama3.3-70b"
```

Results are saved to `results/<timestamp>-<label>/`.

---

## Viewing Results

### HTML report (opens in browser)
```bash
# All runs
python report.py

# Specific runs side by side
python report.py results/run-a results/run-b

# Just a timing table in the terminal
python report.py --list
```

The HTML report shows a timing summary table with % deltas vs the first run, and expandable per-test sections with full response text side by side across runs.

### Compare two runs (terminal)
```bash
python compare.py results/2026-03-09T11-50-33-qwen3.5-27b "results/2026-03-09T12-53-30-gpt-oss:20b"
```

---

## Changing the LLM

```bash
# Change Ollama model
./set-model.sh --model qwen3.5:27b

# Change Ollama server URL
./set-model.sh --url http://10.9.0.102:11434

# Switch to OpenAI
./set-model.sh --llm openai --key sk-...

# Both at once
./set-model.sh --model llama3.3:70b --url http://10.9.0.105:11434
```

The script patches the `llm-config` ConfigMap and `llm-secret` Secret in `cattle-ai-agent-system`, then restarts the agent and waits for it to be ready.

---

## Test Cases (`tests.yaml`)

| Test | What it checks |
|------|---------------|
| `general-hello` | Basic greeting / capability overview |
| `list-clusters` | Can Liz list Rancher clusters |
| `broken-namespace-overview` | Diagnoses all failing deployments at once |
| `crash-loop-diagnosis` | CrashLoopBackOff (container exits immediately) |
| `broken-image-diagnosis` | ImagePullBackOff (invalid image tag) |
| `impossible-schedule-diagnosis` | Pending pod due to unsatisfiable node affinity |
| `missing-config-diagnosis` | CreateContainerConfigError (missing ConfigMap) |
| `readonly-filesystem-diagnosis` | CrashLoop due to write to read-only mount |
| `bad-probe-diagnosis` | Liveness probe port mismatch |
| `resource-rightsizing-broad` | Finds over-provisioned deployments unprompted |
| `resource-rightsizing-focused` | Compares allocated vs actual usage, recommends new values |
| `fix-crash-loop` | Asks for fix steps, not just diagnosis |
| `fix-broken-image` | Asks for fix steps, not just diagnosis |

The resource tests (`resource-rightsizing-*`) are the most demanding — they require multi-step reasoning (list deployments → fetch metrics → compare → recommend). Use these as the primary model quality benchmark.

---

## Results Structure

```
results/
  2026-03-09T11-50-33-qwen3.5-27b/
    summary.json   # Timing stats per question + LLM config used
    results.json   # Full response text + raw timing for every run
    results.csv    # Spreadsheet-friendly format
```

`summary.json` includes the LLM model and Ollama URL that were active when the test ran, so you don't have to rely on the folder name to know which model was tested.

---

## Files

| File | Purpose |
|------|---------|
| `liz-test.py` | Main test runner |
| `tests.yaml` | Test cases and config |
| `report.py` | HTML report + terminal summary |
| `compare.py` | Side-by-side timing comparison of two runs |
| `set-model.sh` | Switch LLM model/URL and restart agent |
| `requirements.txt` | Python dependencies |
