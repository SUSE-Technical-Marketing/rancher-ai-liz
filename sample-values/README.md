# Example values.yaml

You need to create a `values.yaml` file to define how your Rancher AI will interact with your system.

In this folder you will see examples for various configurations. Below is detailed information about the `values-full.yaml` options.

## Agents

The first two sections allow you to override the default `aiAgent` and `mcp` server images. This is typically only needed during development of Rancher AI.

You can find the latest versions of both modules at the following URLs:

### Rancher aiAgent

[https://github.com/rancher-sandbox/rancher-ai-agent/releases](https://github.com/rancher-sandbox/rancher-ai-agent/releases)

### MCP Server

[https://github.com/rancher-sandbox/rancher-ai-mcp/releases](https://github.com/rancher-sandbox/rancher-ai-mcp/releases)

```
aiAgent:  
  image:
    repository: ghcr.io/rancher-sandbox/rancher-ai-agent
    tag: v0.1.1-alpha.15
    pullPolicy: IfNotPresent
mcp:
  image:
    repository: ghcr.io/rancher-sandbox/rancher-ai-mcp
    tag: v0.0.1-alpha.25
    pullPolicy: IfNotPresent
```

## Active LLM

This section allows you to specify which LLM backend you will be using.

### Ollama

`ollama` - Use a self-hosted Ollama server. Depending on which model you are using (or if you are using the RAG option), you may need to use the upstream version of Ollama rather than the version currently in the Application Collection.

Specify your Ollama server with this option:

```yaml
activeLLM: ollama
ollamaUrl: "http://10.9.0.113:31434/"
```

For setup instructions, see [../config-ollama/README.md](../config-ollama/README.md)

### Google Gemini

`gemini` - Use a Google Gemini account. You will need a Gemini API key linked to your Google account.

```yaml
activeLLM: gemini
googleApiKey: "your-api-key-here"
```

### OpenAI

`openai` - Use an OpenAI account instead of hosting your own Ollama. You will need an OpenAI API key.

To use OpenAI, specify your OpenAI API key and URL:

```yaml
activeLLM: openai
openaiApiKey: "your-api-key-here"
openaiUrl: "https://api.openai.com/v1"
```
## Specify Model to Use

You need to specify which model to use. Ensure that the model you specify is ready and loaded on your `activeLLM`.

If you are using Ollama, you will need to pull the model first. For example:

```bash
ollama pull gpt-oss:20b
```

Then specify it in your values.yaml:

```yaml
llmModel: "gpt-oss:20b"
```

### Tested Models (NVIDIA 4090)

| Model | VRAM Usage |
|-------|------------|
| gpt-oss:20b | 14GB |
| qwen3:14b | 9.3GB |
| qwen3:8b | 5.2GB |
| llama3.1:8b | 4.9GB |

## Enable RAG with Embedded Rancher Documentation

When you enable the RAG (Retrieval-Augmented Generation) option, the AI Agent will create a RAG database in the Rancher AI Agent pod and load Rancher documentation. This option uses the `qwen3-embedding:4b` model (2.5GB).

If you enable this option, ensure the embedding model is available in your LLM:

```bash
ollama pull qwen3-embedding:4b
```

Then configure it in your values.yaml:

```yaml
rag:
  enabled: true
  embeddings_model: "qwen3-embedding:4b"
  pvc:
    # Optional: specify PVC configuration for persistent storage
```

## Langfuse

[Langfuse](https://langfuse.com/) is an open-source LLM engineering platform for observability, debugging, evaluation, and prompt management.

To enable Langfuse integration, configure your API keys:

```yaml
langfuseSecretKey: "your-secret-key"
langfusePublicKey: "your-public-key"
langfuseHost: "https://cloud.langfuse.com"  # or your self-hosted instance
```

## Set the Log Level

Control the verbosity of Rancher AI logs:

```yaml
log:
  level: info  # Options: debug, info, warning, error
```

## Example Configuration Files

This directory contains several example configuration files:

- **values-full.yaml** - Complete example with all options
- **values-ollama.yaml** - Configuration for Ollama backend
- **values-openai.yaml** - Configuration for OpenAI backend
- **values-langflow.yaml** - Configuration with Langfuse integration

Choose the example that best matches your setup and customize it with your specific values.