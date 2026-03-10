#!/usr/bin/env bash
# Update the LLM model and/or Ollama URL for the Rancher AI agent.
# The agent restarts automatically after the ConfigMap/Secret changes.
#
# Usage:
#   ./set-model.sh --model qwen3.5:27b
#   ./set-model.sh --model llama3.3:70b --url http://10.9.0.102:11434
#   ./set-model.sh --llm openai --key sk-...

set -euo pipefail

KUBECONFIG="${KUBECONFIG:-$HOME/.kube/liz.yaml}"
CONTEXT="rancher"
NAMESPACE="cattle-ai-agent-system"

MODEL=""
OLLAMA_URL=""
ACTIVE_LLM=""
OPENAI_KEY=""
OPENAI_URL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)  MODEL="$2"; shift 2 ;;
    --url)    OLLAMA_URL="$2"; shift 2 ;;
    --llm)    ACTIVE_LLM="$2"; shift 2 ;;
    --key)    OPENAI_KEY="$2"; shift 2 ;;
    --openai-url) OPENAI_URL="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

KCF="kubectl --kubeconfig=$KUBECONFIG --context=$CONTEXT -n $NAMESPACE"

if [[ -n "$MODEL" ]]; then
  echo "Setting OLLAMA_MODEL=$MODEL"
  $KCF patch configmap llm-config --type=merge -p "{\"data\":{\"OLLAMA_MODEL\":\"$MODEL\"}}"
fi

if [[ -n "$ACTIVE_LLM" ]]; then
  echo "Setting ACTIVE_LLM=$ACTIVE_LLM"
  $KCF patch configmap llm-config --type=merge -p "{\"data\":{\"ACTIVE_LLM\":\"$ACTIVE_LLM\"}}"
fi

if [[ -n "$OLLAMA_URL" ]]; then
  echo "Setting OLLAMA_URL=$OLLAMA_URL"
  ENCODED=$(echo -n "$OLLAMA_URL" | base64)
  $KCF patch secret llm-secret --type=merge -p "{\"data\":{\"OLLAMA_URL\":\"$ENCODED\"}}"
fi

if [[ -n "$OPENAI_KEY" ]]; then
  echo "Setting OPENAI_API_KEY"
  ENCODED=$(echo -n "$OPENAI_KEY" | base64)
  $KCF patch secret llm-secret --type=merge -p "{\"data\":{\"OPENAI_API_KEY\":\"$ENCODED\"}}"
fi

if [[ -n "$OPENAI_URL" ]]; then
  echo "Setting OPENAI_URL=$OPENAI_URL"
  ENCODED=$(echo -n "$OPENAI_URL" | base64)
  $KCF patch secret llm-secret --type=merge -p "{\"data\":{\"OPENAI_URL\":\"$ENCODED\"}}"
fi

# Restart the agent to pick up changes
echo "Restarting rancher-ai-agent..."
$KCF rollout restart deployment/rancher-ai-agent

echo "Waiting for rollout..."
$KCF rollout status deployment/rancher-ai-agent --timeout=120s

echo ""
echo "Current config:"
echo "  ACTIVE_LLM:   $($KCF get configmap llm-config -o jsonpath='{.data.ACTIVE_LLM}')"
echo "  OLLAMA_MODEL: $($KCF get configmap llm-config -o jsonpath='{.data.OLLAMA_MODEL}')"
echo "  OLLAMA_URL:   $($KCF get secret llm-secret -o jsonpath='{.data.OLLAMA_URL}' | base64 -d)"
echo ""
echo "Agent is ready. Run your tests:"
echo "  python liz-test.py --label \"$(${KCF} get configmap llm-config -o jsonpath='{.data.OLLAMA_MODEL}' 2>/dev/null || echo 'run')\""
