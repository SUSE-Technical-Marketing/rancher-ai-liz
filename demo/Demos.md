# Here are a collection of `Broken Deployments` that can be used to demonstrate SUSE Rancher AI

## Broken Image

This is one of the most frequent issues. It occurs when Kubernetes cannot fetch the container image defined in the manifest.

The Error: The Pod status will likely show ErrImagePull or ImagePullBackOff. The Cause: In this YAML, the image tag this-tag-does-not-exist is invalid.

## "CrashLoopBackOff" (No Foreground Process)

Newcomers to containers often treat them like Virtual Machines, expecting them to stay running just because they started. However, a container only stays alive as long as its main process is running.

The Error: The Pod status will cycle between Running, Completed, and CrashLoopBackOff. The Cause: The Alpine image runs the echo command, prints the message, and immediately exits with a success code (0). Because the restart policy is Always, Kubernetes restarts it infinitely.

## Bad Probe

The "Probe Failure" Loop
Health checks (Liveness and Readiness probes) are critical, but if misconfigured, they can kill a healthy pod or prevent traffic from reaching it.

The Error: The Pod may appear as Running but 0/1 Ready, or it will restart repeatedly if the Liveness probe fails. The Cause: The Nginx container listens on port 80 by default, but the liveness probe is configured to check port 8080. Kubernetes thinks the app is dead and kills it.

## "Resource Hog" (Over-provisioning)

The Issue: The Pod runs successfully, but it "locks" a large portion of the node's capacity. The Cause: We are requesting 2 full CPU core and 2 Gigabyte of RAM for a tiny web server that typically needs only 10m CPU and 64Mi RAM.

## "Missing Dependency" Error (ConfigMap/Secret)
Kubernetes manifests often reference external configurations (ConfigMaps) or credentials (Secrets). If you reference one that hasn't been created yet, the container will refuse to start.

The Error: The Pod status will likely be CreateContainerConfigError or ConfigMapNotFound. The Cause: The deployment tries to inject environment variables from a ConfigMap named app-config, but that ConfigMap does not exist in the namespace.

## "Impossible Schedule" (Node Affinity)
Sometimes a Pod remains in the Pending state forever, even if your cluster has plenty of CPU and RAM. This often happens when you use constraints that no node in the cluster can satisfy.

The Error: The Pod status stays Pending. kubectl describe pod will show "0/X nodes are available: node(s) didn't match Pod's node affinity." The Cause: We are asking Kubernetes to schedule this pod only on a node that has the label disk=ssd. If you haven't labeled any of your nodes with this specific tag, the scheduler has nowhere to put the pod.

## "Read-Only Filesystem" Crash
Containers are often immutable, but applications sometimes forget that. A common error occurs when an app tries to write logs or temp files to a directory that has been mounted as Read-Only, or to the root filesystem when security policies forbid it.

The Error: The Pod will start, crash, and enter CrashLoopBackOff. The logs (kubectl logs <pod>) will show an error like OSError: [Errno 30] Read-only file system. The Cause: We are mounting a volume at /app/data with readOnly: true, but the command tries to touch (create) a file inside that directory.