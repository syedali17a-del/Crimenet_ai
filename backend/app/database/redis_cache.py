"""Redis adapter - analysis result cache and agent task state.

Uses a real Redis server when CRIMENET_REDIS_URL is set, otherwise a labelled
in-process TTL cache with the same get/set/expire contract.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Any, Optional

from ..config import REDIS_URL


class CacheStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: dict[str, tuple[float, str]] = {}
        self.client = None
        self.profile = "EMBEDDED_TTL_CACHE"
        self.detail = (
            "No Redis server reachable in this environment. Running the labelled embedded "
            "TTL cache with the same key/value + expiry contract."
        )
        self.hits = 0
        self.misses = 0
        if REDIS_URL:
            try:  # pragma: no cover
                import redis  # type: ignore

                self.client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
                self.client.ping()
                self.profile = "REDIS"
                self.detail = "Connected to Redis."
            except Exception as exc:  # pragma: no cover
                self.detail = f"Redis URL configured but unreachable ({exc}). Using embedded cache."

    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        payload = json.dumps(value, default=str)
        if self.client:  # pragma: no cover
            self.client.setex(key, ttl, payload)
            return
        with self._lock:
            self._data[key] = (time.time() + ttl, payload)

    def get(self, key: str) -> Optional[Any]:
        if self.client:  # pragma: no cover
            raw = self.client.get(key)
            if raw is None:
                self.misses += 1
                return None
            self.hits += 1
            return json.loads(raw)
        with self._lock:
            item = self._data.get(key)
            if not item or item[0] < time.time():
                self._data.pop(key, None)
                self.misses += 1
                return None
            self.hits += 1
            return json.loads(item[1])

    def invalidate(self, prefix: str) -> int:
        if self.client:  # pragma: no cover
            keys = list(self.client.scan_iter(match=f"{prefix}*"))
            if keys:
                self.client.delete(*keys)
            return len(keys)
        with self._lock:
            keys = [k for k in self._data if k.startswith(prefix)]
            for k in keys:
                self._data.pop(k, None)
            return len(keys)

    def status(self) -> dict[str, Any]:
        size = len(self._data) if not self.client else -1
        return {
            "component": "Redis",
            "profile": self.profile,
            "detail": self.detail,
            "keys": size,
            "hits": self.hits,
            "misses": self.misses,
        }


cache = CacheStore()
