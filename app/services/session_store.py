import os
import pickle
import time
import uuid
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SESSION_DIR = PROJECT_ROOT / "data" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# In-process cache speeds up repeated requests. Pickle files allow recovery
# after a process restart on the same persistent filesystem only.
SESSIONS = {}
_SESSION_LOCK = threading.RLock()
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "21600"))  # 6 hours


def _session_file(session_id):
    # UUID-only names prevent path traversal from user-supplied IDs.
    try:
        uuid.UUID(str(session_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise KeyError("Session not found or expired.") from exc
    return SESSION_DIR / f"{session_id}.pkl"


def _is_expired(path):
    return time.time() - path.stat().st_mtime > SESSION_TTL_SECONDS


def create_session(data, metadata=None):
    session_id = str(uuid.uuid4())
    session = {
        "data": data.copy(),
        "metadata": metadata or {},
        "created_at": time.time(),
    }
    session_file = _session_file(session_id)
    temporary_file = session_file.with_suffix(".tmp")
    try:
        with temporary_file.open("wb") as handle:
            pickle.dump(session, handle, protocol=pickle.HIGHEST_PROTOCOL)
        temporary_file.replace(session_file)
    finally:
        temporary_file.unlink(missing_ok=True)

    with _SESSION_LOCK:
        SESSIONS[session_id] = session
    return session_id


def get_session(session_id):
    session_file = _session_file(session_id)
    with _SESSION_LOCK:
        cached = SESSIONS.get(session_id)
        if cached is not None:
            return cached

    if not session_file.exists():
        raise KeyError("Session not found or expired.")
    try:
        if _is_expired(session_file):
            session_file.unlink(missing_ok=True)
            with _SESSION_LOCK:
                SESSIONS.pop(session_id, None)
            raise KeyError("Session not found or expired.")
        with session_file.open("rb") as handle:
            session = pickle.load(handle)
        with _SESSION_LOCK:
            SESSIONS[session_id] = session
        return session
    except KeyError:
        raise
    except Exception as exc:
        raise KeyError("Session not found or expired.") from exc


def delete_session(session_id):
    with _SESSION_LOCK:
        SESSIONS.pop(session_id, None)
    try:
        _session_file(session_id).unlink(missing_ok=True)
    except (OSError, KeyError):
        pass


def clear_sessions():
    with _SESSION_LOCK:
        SESSIONS.clear()
    for session_file in SESSION_DIR.glob("*.pkl"):
        try:
            if _is_expired(session_file):
                session_file.unlink(missing_ok=True)
        except OSError:
            pass
