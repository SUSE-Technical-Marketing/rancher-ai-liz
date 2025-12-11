# Installing self hosted Ollama

Use the Rancher UI or `kubectl` to deploy the `ollama` server and the `ollama service`

```
kubectl apply -f ollama-deployment.yaml
kubectl apply -f ollama-service.yaml
```

ollama-deployment.yaml

```ollama-deployment.yaml
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

ollama-service.yaml

```ollama-service.yaml
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
    nodePort: 31434   # Specific port that ollama will appear on
```

# Pull Ollama models


From the Rancher UI, view the Ollama pod by going to Workload->Pods and view the `ollama` pod in the `ollama` namespace


![View MCP](/assets/ollama-pull.gif)