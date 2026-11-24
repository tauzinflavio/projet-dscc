import json
import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from urllib.parse import unquote

import azure.functions as func
import httpx
from azure.core.exceptions import ResourceExistsError
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.storage.queue import QueueClient, TextBase64EncodePolicy
from pipeline import MAX_BYTES, document_id, validate

app = func.FunctionApp()
http = httpx.Client(timeout=httpx.Timeout(40, connect=5))
log = logging.getLogger(__name__)
PREFIX = "/blobServices/default/containers/input/blobs/"


@lru_cache
def credential():
    return DefaultAzureCredential()


@lru_cache
def storage():
    return BlobServiceClient(os.environ["PipelineStorage__blobServiceUri"], credential())


@lru_cache
def queue():
    return QueueClient(os.environ["PipelineStorage__queueServiceUri"], "inference-requests",
                       credential=credential(), message_encode_policy=TextBase64EncodePolicy())


@lru_cache
def database():
    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], credential())
    return client.get_database_client("pipeline").get_container_client("inferences")


def source(name, etag):
    # Le blob peut avoir été remplacé entre la notification et sa lecture.
    container = storage().get_container_client("input")
    for blob in container.list_blobs(name_starts_with=name, include=["versions"]):
        if blob.name == name and blob.etag.strip('"') == etag.strip('"'):
            return container.get_blob_client(name, version_id=blob.version_id)
    raise LookupError("Version source introuvable")


def write_json(blob, record):
    blob.upload_blob(json.dumps(record, ensure_ascii=False).encode(), overwrite=False,
                     content_settings=ContentSettings(content_type="application/json"))


@app.event_grid_trigger(arg_name="event")
def dispatcher(event: func.EventGridEvent):
    if event.event_type != "Microsoft.Storage.BlobCreated" or not event.subject.startswith(PREFIX):
        return
    data = event.get_json()
    name = unquote(event.subject[len(PREFIX):])
    etag = data["eTag"].strip('"')
    blob = source(name, etag)
    size = blob.get_blob_properties().size
    key = document_id(name, etag)
    try:
        validate(name, size, blob.download_blob().readall() if size <= MAX_BYTES else b"")
    except ValueError as error:
        rejected = storage().get_blob_client("rejected", key + "/original")
        try:
            rejected.upload_blob(blob.download_blob().chunks(), overwrite=False)
        except ResourceExistsError:
            pass
        try:
            write_json(storage().get_blob_client("rejected", key + "/motif.json"),
                       {"fileName": name, "etag": etag, "reason": str(error)})
        except ResourceExistsError:
            pass
        return
    queue().send_message(json.dumps({"fileName": name, "etag": etag, "size": size,
                                     "timestamp": event.event_time.isoformat()}))


@app.queue_trigger(arg_name="msg", queue_name="inference-requests", connection="PipelineStorage")
def worker(msg: func.QueueMessage):
    item = json.loads(msg.get_body())
    name, etag = item["fileName"], item["etag"]
    key = document_id(name, etag)
    target = storage().get_blob_client("output", key + ".json")
    if not target.exists():
        blob = source(name, etag)
        payload = validate(name, item["size"], blob.download_blob().readall())
        response = http.post(os.environ["API_URL"].rstrip("/") + "/predict", json=payload)
        response.raise_for_status()
        result = dict(item, id=key, processedAt=datetime.now(timezone.utc).isoformat(),
                      **response.json())
        try:
            write_json(target, result)
        except ResourceExistsError:
            pass  # Un autre worker a déjà enregistré cette version.
    canonical = json.loads(target.download_blob().readall())
    database().upsert_item(canonical)
    log.info(json.dumps({"event": "wine.persisted", "id": key, "fileName": name,
                         "durationMs": canonical["durationMs"]}))


@app.route(route="recent", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def recent(req: func.HttpRequest):
    query = ("SELECT TOP 20 c.id, c.fileName, c.processedAt, c.prediction, c.confidence, "
             "c.durationMs, c.modelVersion FROM c ORDER BY c.processedAt DESC")
    rows = list(database().query_items(query=query, enable_cross_partition_query=True))
    return func.HttpResponse(json.dumps(rows), mimetype="application/json",
                             headers={"Cache-Control": "no-store"})
