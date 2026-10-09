
import uuid
import pickle
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SESSION_DIR = PROJECT_ROOT / "data" / "sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS = {}


def _session_file(session_id):
    return SESSION_DIR / f"{session_id}.pkl"


def create_session(data, metadata=None):
    session_id = str(uuid.uuid4())
    session = {"data": data.copy(), "metadata": metadata or {}}

    session_file = _session_file(session_id)
    with open(session_file, "wb") as f:
        pickle.dump(session, f, protocol=pickle.HIGHEST_PROTOCOL)

    SESSIONS[session_id] = session
    return session_id


def get_session(session_id):
    if session_id in SESSIONS:
        return SESSIONS[session_id]

    session_file = _session_file(session_id)
    if not session_file.exists():
        raise KeyError("Session not found or expired.")

    try:
        with open(session_file, "rb") as f:
            session = pickle.load(f)

        SESSIONS[session_id] = session
        return session

    except Exception as exc:
        raise KeyError("Session not found or expired.") from exc


def delete_session(session_id):
    SESSIONS.pop(session_id, None)
    session_file = _session_file(session_id)

    if session_file.exists():
        try:
            session_file.unlink()
        except OSError:
            pass


def clear_sessions():
    SESSIONS.clear()

    for session_file in SESSION_DIR.glob("*.pkl"):
        try:
            session_file.unlink()
        except OSError:
            pass