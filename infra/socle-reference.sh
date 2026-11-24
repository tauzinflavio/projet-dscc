#!/usr/bin/env bash
# Section 6 du sujet. Lancer les étapes séparément après validation du budget,
# de la région, du nom d’équipe et de l’image publique disponible sur GHCR.
set -eu
: "${EQ:?nom de l’équipe}" "${LOC:?région vérifiée}" "${IMAGE:?image GHCR publique versionnée}"
RG=rg-projet-$EQ
ST=st${EQ}pipe; COSMOS=cosmos-$EQ; ENV=cae-$EQ; FUNC=func-$EQ; ID=id-github-$EQ
LAW=log-$EQ; AI=appi-$EQ
case "${1:-}" in
groupe)
  az group create -n "$RG" -l "$LOC" --tags projet=dscc equipe="$EQ"
  ;;
cosmos)
  az cosmosdb create -n "$COSMOS" -g "$RG" --enable-free-tier true --locations regionName="$LOC" failoverPriority=0 isZoneRedundant=False
  az cosmosdb sql database create -a "$COSMOS" -g "$RG" -n pipeline --throughput 400
  az cosmosdb sql container create -a "$COSMOS" -g "$RG" -d pipeline -n inferences --partition-key-path /fileName
  ;;
stockage)
  az storage account create -n "$ST" -g "$RG" -l "$LOC" --sku Standard_LRS --kind StorageV2 --min-tls-version TLS1_2 --allow-blob-public-access false
  az storage account blob-service-properties update --account-name "$ST" -g "$RG" --enable-versioning true
  for c in input output rejected models; do az storage container create --account-name "$ST" -n "$c"; done
  az storage queue create --account-name "$ST" -n inference-requests
  az storage blob service-properties update --account-name "$ST" --static-website --index-document index.html
  ;;
supervision)
  az monitor log-analytics workspace create -g "$RG" -n "$LAW" -l "$LOC" --quota 0.2
  LAW_ID=$(az monitor log-analytics workspace show -g "$RG" -n "$LAW" --query id -o tsv)
  az monitor app-insights component create --app "$AI" -g "$RG" -l "$LOC" --workspace "$LAW_ID"
  ;;
applications)
  az containerapp env create -n "$ENV" -g "$RG" -l "$LOC" \
    --logs-workspace-id "$(az monitor log-analytics workspace show -g "$RG" -n "$LAW" --query customerId -o tsv)" \
    --logs-workspace-key "$(az monitor log-analytics workspace get-shared-keys -g "$RG" -n "$LAW" --query primarySharedKey -o tsv)" -o none
  az containerapp create -n "api-$EQ" -g "$RG" --environment "$ENV" --image "$IMAGE" --target-port 8000 --ingress external --cpu 0.25 --memory 0.5Gi --min-replicas 0 --max-replicas 2 -o none
  az functionapp create -n "$FUNC" -g "$RG" --storage-account "$ST" --app-insights "$AI" --flexconsumption-location "$LOC" --runtime python --runtime-version 3.12 --instance-memory 512 -o none
  ;;
droits-functions)
  az functionapp identity assign -n "$FUNC" -g "$RG" -o none
  PID=$(az functionapp identity show -n "$FUNC" -g "$RG" --query principalId -o tsv)
  ST_ID=$(az storage account show -n "$ST" -g "$RG" --query id -o tsv)
  for r in "Storage Blob Data Owner" "Storage Queue Data Contributor"; do
    az role assignment create --role "$r" --assignee-object-id "$PID" --assignee-principal-type ServicePrincipal --scope "$ST_ID"
  done
  az cosmosdb sql role assignment create -a "$COSMOS" -g "$RG" --scope / --principal-id "$PID" --role-definition-id 00000000-0000-0000-0000-000000000002
  ;;
evenements)
  az eventgrid event-subscription create -n blob-to-dispatcher --source-resource-id "$(az storage account show -n "$ST" -g "$RG" --query id -o tsv)" --endpoint-type azurefunction --endpoint "$(az functionapp show -n "$FUNC" -g "$RG" --query id -o tsv)/functions/dispatcher" --included-event-types Microsoft.Storage.BlobCreated --subject-begins-with /blobServices/default/containers/input/
  ;;
oidc)
  : "${OIDC_SUBJECT:?sujet exact du dépôt et de l’environnement production}"
  az identity create -n "$ID" -g "$RG"
  az identity federated-credential create -n github-main --identity-name "$ID" -g "$RG" --issuer https://token.actions.githubusercontent.com --subject "$OIDC_SUBJECT" --audiences api://AzureADTokenExchange
  az role assignment create --role Contributor --assignee-object-id "$(az identity show -n "$ID" -g "$RG" --query principalId -o tsv)" --assignee-principal-type ServicePrincipal --scope "$(az group show -n "$RG" --query id -o tsv)"
  ;;
*) echo 'Choisir : groupe, cosmos, stockage, supervision, applications, droits-functions, evenements, oidc'; exit 2;;
esac
