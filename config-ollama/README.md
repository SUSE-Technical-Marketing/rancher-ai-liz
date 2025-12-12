# Installing Self-Hosted Ollama

Use the Rancher UI or `kubectl` to deploy the Ollama server and service.

```bash
kubectl apply -f ollama-deployment.yaml
kubectl apply -f ollama-service.yaml
```

## ollama-deployment.yaml

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ollama
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
  namespace: ollama
spec:
  selector:
    matchLabels:
      name: ollama
  template:
    metadata:
      labels:
        name: ollama
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - name: http
          containerPort: 11434
          protocol: TCP
```

## ollama-service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: ollama
  namespace: ollama
spec:
  type: NodePort      
  selector:
    name: ollama
  ports:
  - port: 11434
    name: http
    targetPort: http
    protocol: TCP
    nodePort: 31434   # Specific port that Ollama will be accessible on
```

# Pull Ollama Models

From the Rancher UI, view the Ollama pod by going to **Workload → Pods** and select the `ollama` pod in the `ollama` namespace.

To pull models, execute commands in the pod's shell:

```bash
ollama pull gpt-oss:20b
# For RAG embedding support
ollama pull qwen3-embedding:4b
```

![Ollama Pull](../assets/ollama-pull.gif)

## Verify Models

After pulling models, verify they are available:

```bash
ollama list
```

## Configure Rancher AI to Use Ollama

Once Ollama is deployed and models are pulled, configure your `values.yaml` to point to the Ollama service:

```yaml
activeLLM: ollama
ollamaUrl: "http://ollama.ollama.svc.cluster.local:11434/"
# Or if using NodePort from outside the cluster:
# ollamaUrl: "http://<node-ip>:31434/"
```

See [sample-values/README.md](../sample-values/README.md) for complete configuration examples.
