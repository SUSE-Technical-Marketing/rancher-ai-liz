You need to create a values.yaml to define how your Rancher AI will interact with your system.

In this folder you will see examples for various configuration. Below is the vaules-full.yaml

## Agents

The first 2 sections allow us to override the default `aiAgent` and the `mcp` server. This is really just needed when we are in the development of `Rancher AI`

You can find the latest version of both of these modules by going to following urls

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

## active LLM

This section allows you to specify which LLM you will be using.

### ollama

`ollama` - use a self hosted ollama server. Note, depending on what model you are using (or if you are using the RAG option) you will need to use the upstream version of ollama rather than the version that is currently in Application Collection

You will specify your ollama server with this option

```
ollamaUrl: "http://10.9.0.113:31434/"
```

### Google Gemini

`gemini` - This allows you to use a Google Gemini account. You will need a `gemini API` that is linked to your google account.

You will need to specify your Google API Key

```
googleApiKey:
```
### OpenAI

`openai` - This option allows you to use a OpenAI account instead of hosting your own ollama. You will need and `OpenAI API`  

Top use OpenAI you will need to specify your `OpenAI API` and your `OpenAI URL`

```
openaiApiKey:
openaiUrl:
```
## Specify Model to use

You need to specify the model that use. You need to ensure that the model you specify is ready and loaded on your `activeLLM`.

This means that if you are using ollama, you will need to issue any commands needed to load the model. For example with Ollama you will need to do an `ollama pull gpt-oss:20b`

```
llmModel: "gpt-oss:20b"
```
Models that I have used and tested on my NVIDIA 4090

```
gpt-oss:20b - 14GB
qwen3:14b.  - 9.3GB
qwen3:8b    - 5.2Gb
llama3.1:8b - 4.9GB
```

## Enable RAG with embedded rancher documentation

When you enable the RAG option, when the AI Agent loads, it will create a RAG database in the Rancher AI Agent pod and load a bunch of documents. This option leverages the `qwen3-embedding:4b` model (2.5GB).

If you enable this option ensure that you have made the model available in LLM (I.E. `ollama pull qwen3-embedding:4b`)

```
rag:
    enabled: true
    embeddings_model: "qwen3-embedding:4b"
    pvc:
```

## Langfuse

Langfuse is an open-source LLM (Large Language Model) engineering platform for observability, debugging, evaluation, and prompt management

```
langfuseSecretKey:
langfusePublicKey:
langfuseHost:
```
## Set the Log level 
```
log:
  level: info
```