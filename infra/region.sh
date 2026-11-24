#!/usr/bin/env bash
# Section 3.2. Lecture seule pour le choix de région.
set -eu
az policy assignment list --disable-scope-strict-match \
  --query "[?contains(displayName,'region') || contains(displayName,'location')].parameters" -o json
az functionapp list-flexconsumption-locations -o table
