import json
from unittest.mock import Mock

import function_app as pipeline
import pytest


@pytest.mark.parametrize("cosmos_unavailable", [False, True], ids=["duplicate", "retry-after-outage"])
def test_replayed_message_reuses_saved_prediction(monkeypatch, cosmos_unavailable):
    msg = Mock()
    msg.get_body.return_value = b'{"fileName":"vin.json","etag":"abc","size":40}'
    output = Mock()
    output.exists.side_effect = [False, True]
    stored = {}
    output.upload_blob.side_effect = lambda raw, **opts: stored.update(json.loads(raw))
    output.download_blob.return_value.readall.side_effect = lambda: json.dumps(stored).encode()
    storage = Mock()
    storage.get_blob_client.return_value = output
    source = Mock()
    source.return_value.download_blob.return_value.readall.return_value = json.dumps(
        {"features": [1] * 13}).encode()
    db = Mock()
    if cosmos_unavailable:
        db.upsert_item.side_effect = [TimeoutError(), None]
    request = Mock()
    request.return_value.json.return_value = {"prediction": 1, "durationMs": 0.15}
    monkeypatch.setattr(pipeline, "storage", lambda: storage)
    monkeypatch.setattr(pipeline, "database", lambda: db)
    monkeypatch.setattr(pipeline, "source", source)
    monkeypatch.setattr(pipeline.http, "post", request)
    monkeypatch.setenv("API_URL", "https://example.invalid")

    if cosmos_unavailable:
        with pytest.raises(TimeoutError):
            pipeline.worker(msg)
    else:
        pipeline.worker(msg)
    pipeline.worker(msg)

    request.assert_called_once()
    output.upload_blob.assert_called_once()
    assert db.upsert_item.call_count == 2
    assert db.upsert_item.call_args_list[0] == db.upsert_item.call_args_list[1]
    assert stored["id"] == pipeline.document_id("vin.json", "abc")
