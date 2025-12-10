# Install and setting up Rancher AI

Rancher AI installed in the `local` Cluster. This allows you Rancher AI to see all downstream clusters.

To install and setup SUSE Rancher AI Rancher cluster with Rancher 2.13.x installed.
If you cluster in pre-2.13 you need to complete additional steps.

Before the install, you need to create a values.yaml file with you deployment specific information.

For details on how to create you values.yaml in sample-values/README.md

## Install Rancher-AI Agent
```Setup Repo
helm repo add rancher-ai https://rancher-sandbox.github.io/rancher-ai-agent
helm refresh
```

```Install Rancher AI Agent
helm install rancher-ai-agent rancher-ai/agent   --namespace cattle-ai-agent-system   --create-namespace   --devel   -f values.yaml
```

## View Deployments

Check the status of the Rancher AI Agent. There are 2 pods that are deployed to the `cattle-ai-agent-system`

### View the `rancher-mcp-server`

![View MCP](/assets/mcp-log.png)

### View the `racher-ai-agent` log

If you deployed the `enabled` the `RAG` watch the logs until you see `Uvicorn running on http://0.0.0.0:8000`

![View MCP](/assets/rancher-ai-agent-log.gif)


# Setup up backend

## Ollama

## openAI

# Demoing Rancher AI

# Links

## Rancher-AI Quickstart

https://drive.google.com/file/d/1dGjTnJsk4RWv_aqAMUhHiH3BEocmG-8F/view

## Installing NVIDIA drivers

https://github.com/SUSE-Technical-Marketing/suse-ai-demo/blob/main/install/Install-NVIDIA-drivers.md

## SUSE AI on SLES 16

https://lajoie.de/blog2/index.html


## rancher-ai-agent on Github

[text](https://github.com/rancher-sandbox/rancher-ai-agent)

## Rancher MCP

[text](https://github.com/rancher-sandbox/rancher-ai-mcp)

## rancher-ai-ui on Github

[text](https://github.com/torchiaf/rancher-ai-ui)

## SUSE® Rancher Prime: AI - Assistant Early Adopters Program

https://drive.google.com/file/d/1lXopcOwL5hWHJSkQkUKoDxmnqwEuCSfF/

## SUSE Rancher Prime: AI Assistant Liz Deck

https://docs.google.com/presentation/d/19DlHhFwW0RBf1BFcYRZW1BKGfZKknAGpluINRMGXe30/edit?slide=id.g34098e29a71_0_6#slide=id.g34098e29a71_0_6