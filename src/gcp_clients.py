from __future__ import annotations
from typing import Optional, Dict, Any

import os


class GCSUploader:
    def __init__(self, bucket: str | None):
        self.bucket = bucket or ""
        try:
            from google.cloud import storage  # type: ignore
        except Exception:
            storage = None  # type: ignore
        self._storage = storage
        self._client = None
        self._bucket = None

    def available(self) -> bool:
        return bool(self._storage and self.bucket)

    def _ensure(self):
        if not self.available():
            return
        if self._client is None:
            self._client = self._storage.Client()
            self._bucket = self._client.bucket(self.bucket)

    def upload_bytes(self, data: bytes, blob_name: str, content_type: str = "application/octet-stream") -> Optional[str]:
        try:
            self._ensure()
            if not self._bucket:
                return None
            blob = self._bucket.blob(blob_name)
            blob.upload_from_string(data, content_type=content_type)
            return f"gs://{self.bucket}/{blob_name}"
        except Exception:
            return None


class PubSubPublisher:
    def __init__(self, topic_path: str | None):
        self.topic_path = topic_path or ""
        try:
            from google.cloud import pubsub_v1  # type: ignore
        except Exception:
            pubsub_v1 = None  # type: ignore
        self._pubsub = pubsub_v1
        self._publisher = None

    def available(self) -> bool:
        return bool(self._pubsub and self.topic_path)

    def _ensure(self):
        if not self.available():
            return
        if self._publisher is None:
            self._publisher = self._pubsub.PublisherClient()

    def publish_json(self, payload: Dict[str, Any]) -> bool:
        try:
            self._ensure()
            if not self._publisher:
                return False
            import json
            data = json.dumps(payload).encode("utf-8")
            future = self._publisher.publish(self.topic_path, data)
            future.result(timeout=5)
            return True
        except Exception:
            return False
