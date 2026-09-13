"""Instance-wide toggles (currently just off_lookup_enabled) editable live
from /admin, persisted to a small JSON file rather than the SQLite database -
there's no need for a real table for a couple of booleans, and this keeps
the read path a plain in-memory dict instead of a query.

Loaded once into memory at startup (init) and kept in sync on every write
(set_bool), so a request never has to touch disk to read a setting. This
assumes a single process (see Dockerfile: gunicorn runs one worker,
multiple threads) - if this ever moves to multiple worker processes, each
would need its own restart (or a poll/reload) to see another worker's
write, since the in-memory cache wouldn't be shared between them.
"""

import json
import os
import threading

_lock = threading.Lock()
_path = None
_cache = {}


def init(path, defaults=None):
    """Loads settings from disk, creating the file (seeded with defaults)
    if it doesn't exist yet. Also backfills any default key missing from
    an existing file - e.g. a setting added after the file was first
    written - without touching keys already present."""
    global _path, _cache
    _path = path
    with _lock:
        if os.path.exists(_path):
            with open(_path) as f:
                _cache = json.load(f)
        else:
            _cache = {}

        changed = False
        for key, value in (defaults or {}).items():
            if key not in _cache:
                _cache[key] = value
                changed = True
        if changed or not os.path.exists(_path):
            _write_locked()


def _write_locked():
    """Write-then-rename so a crash mid-write can't leave a half-written,
    unparseable settings file behind."""
    tmp = f"{_path}.tmp"
    with open(tmp, "w") as f:
        json.dump(_cache, f)
    os.replace(tmp, _path)


def get_bool(key, default=False):
    return bool(_cache.get(key, default))


def set_bool(key, value):
    with _lock:
        _cache[key] = bool(value)
        _write_locked()
