"""Content-addressed JSON cache on disk."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def cache_key(payload: dict[str, Any]) -> str:
    """Return a SHA-256 hex digest of the payload, independent of dict key order."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class DiskCache:
    """Stores one JSON file per key under `root/<first two hex chars>/<key>.json`."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        """Return the cached value for `key`, or None on a miss."""
        path = self._path(key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, key: str, value: dict[str, Any]) -> None:
        """Write `value` for `key`. The write is atomic, so a crash never leaves a partial file."""
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
