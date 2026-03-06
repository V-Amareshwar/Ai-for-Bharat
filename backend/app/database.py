"""
database.py — Persistent JSON-file-backed storage for Jan-Sahayak.

Replaces the in-memory mock_applications_db dictionary so that data
survives server restarts and multi-day sessions.

Usage:
    from .database import load_db, save_db, get_db

The canonical live dict is obtained via get_db().  Every mutation
must be followed by save_db().  main.py is the only caller of save_db.
"""

import json
import os
import threading
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Path resolution — always relative to this file
# ──────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
# Goes up one level: backend/app/ → backend/
DB_PATH = os.path.join(_HERE, "..", "database.json")

# Thread lock so concurrent FastAPI requests don't corrupt the file
_lock = threading.Lock()

# Single in-process reference — loaded once on import, written on demand
_db: dict = {}


def load_db() -> dict:
    """
    Load (or initialise) the JSON database from disk.

    Called once at application startup.  If the file is missing or
    corrupt, an empty dict is returned and a fresh file is written.
    """
    global _db
    with _lock:
        if os.path.exists(DB_PATH):
            try:
                with open(DB_PATH, "r", encoding="utf-8") as fh:
                    _db = json.load(fh)
                logger.info("Loaded %d records from %s", len(_db), DB_PATH)
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("database.json corrupt or unreadable (%s) — starting fresh.", exc)
                _db = {}
                # Overwrite the broken file immediately so we don't loop on errors
                _write_unsafe()
        else:
            _db = {}
            _write_unsafe()
            logger.info("Created new database.json at %s", DB_PATH)
    return _db


def save_db() -> None:
    """
    Atomically persist the current in-memory dict to disk.

    Uses a temp-file + rename strategy so a crash mid-write never
    produces a half-written (corrupt) JSON file.
    """
    with _lock:
        _write_unsafe()


def _write_unsafe() -> None:
    """Low-level write — caller must hold _lock."""
    tmp_path = DB_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(_db, fh, indent=2, ensure_ascii=False)
        os.replace(tmp_path, DB_PATH)   # atomic on POSIX & Windows (Vista+)
    except OSError as exc:
        logger.error("Failed to write database.json: %s", exc)
        raise


def get_db() -> dict:
    """Return the live in-memory database dict."""
    return _db
