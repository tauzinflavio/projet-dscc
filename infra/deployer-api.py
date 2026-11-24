"""Je crée ou mets à jour l’API avec l’image testée par la CI."""
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path


def az(*args):
    return subprocess.check_output(["az", *args, "--only-show-errors", "-o", "tsv"], text=True).strip()


group = "rg-projet-ft"
scope = az("group", "show", "-n", group, "--query", "id")
base = scope + "/providers/"
monitor = base + "Microsoft.Insights/components/appi-ft"
environment = base + "Microsoft.App/managedEnvironments/cae-ft"
url = "https://management.azure.com" + base + "Microsoft.App/containerApps/api-ft?api-version=2024-03-01"
connection = az("resource", "show", "--ids", monitor, "--api-version", "2020-02-02",
                "--query", "properties.ConnectionString")
sha = os.environ["DEPLOY_SHA"]
container = {
    "name": "api", "image": "ghcr.io/tauzinflavio/projet-dscc/api:" + sha,
    "env": [{"name": "APPLICATIONINSIGHTS_CONNECTION_STRING", "secretRef": "monitor"},
            {"name": "OTEL_SERVICE_NAME", "value": "wine-api"}],
    "resources": {"cpu": 0.25, "memory": "0.5Gi"},
    "probes": [{"type": kind, "httpGet": {"path": "/health", "port": 8000},
                "initialDelaySeconds": 10, "periodSeconds": 10} for kind in ["Liveness", "Readiness"]]
}
body = {"location": "switzerlandnorth", "tags": {"projet": "dscc", "equipe": "ft"},
        "properties": {"managedEnvironmentId": environment, "configuration": {
            "activeRevisionsMode": "Single", "ingress": {"external": True, "targetPort": 8000},
            "secrets": [{"name": "monitor", "value": connection}]},
            "template": {"containers": [container], "scale": {"minReplicas": 0, "maxReplicas": 2}}}}
with tempfile.TemporaryDirectory() as directory:
    payload = Path(directory) / "app.json"
    payload.write_text(json.dumps(body))
    az("rest", "-m", "put", "-u", url, "-b", "@" + str(payload), "--query", "name")
for _ in range(90):
    state = az("rest", "-m", "get", "-u", url, "--query", "properties.provisioningState")
    if state == "Succeeded":
        break
    if state in {"Failed", "Canceled"}:
        raise SystemExit("Azure n’a pas pu créer la révision.")
    time.sleep(5)
else:
    raise SystemExit("Délai de création de la révision dépassé.")
fqdn = az("rest", "-m", "get", "-u", url, "--query", "properties.configuration.ingress.fqdn")
with open(os.environ["GITHUB_ENV"], "a") as file:
    print("API_URL=https://" + fqdn, file=file)
