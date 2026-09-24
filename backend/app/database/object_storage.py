"""Object Storage adapter - immutable evidence blobs (PDF / image / CSV / text).

Only the blob lives here. Hashes, provenance and chain-of-custody metadata live in
PostgreSQL and the permissioned ledger. Content is written write-once: the original
object is never modified by the application.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from typing import Any, Optional

from ..config import OBJECT_STORAGE_ROOT


class ObjectStorage:
    def __init__(self, root: str = OBJECT_STORAGE_ROOT) -> None:
        self.root = root
        self.profile = "FILESYSTEM_BACKED_OBJECT_STORAGE"
        os.makedirs(self.root, exist_ok=True)

    def _path(self, key: str) -> str:
        safe = key.replace("..", "_").lstrip("/")
        full = os.path.join(self.root, safe)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        return full

    def put_bytes(self, key: str, data: bytes) -> dict[str, Any]:
        path = self._path(key)
        with open(path, "wb") as fh:
            fh.write(data)
        return {"object_key": key, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def put_text(self, key: str, text: str) -> dict[str, Any]:
        return self.put_bytes(key, text.encode("utf-8"))

    def get_bytes(self, key: str) -> Optional[bytes]:
        path = self._path(key)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as fh:
            return fh.read()

    def get_text(self, key: str) -> Optional[str]:
        raw = self.get_bytes(key)
        if raw is None:
            return None
        return raw.decode("utf-8", errors="replace")

    def exists(self, key: str) -> bool:
        return os.path.exists(self._path(key))

    def size(self, key: str) -> int:
        path = self._path(key)
        return os.path.getsize(path) if os.path.exists(path) else 0

    def reset(self) -> None:
        if os.path.isdir(self.root):
            shutil.rmtree(self.root, ignore_errors=True)
        os.makedirs(self.root, exist_ok=True)

    def status(self) -> dict[str, Any]:
        count = sum(len(files) for _, _, files in os.walk(self.root))
        return {
            "component": "Object Storage",
            "profile": self.profile,
            "detail": "Write-once evidence blob store (dev profile: local filesystem volume).",
            "objects": count,
            "root": self.root,
        }


object_storage = ObjectStorage()
