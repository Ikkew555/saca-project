# back-end/app/chat/session.py
from typing import Dict, Any

sessions: Dict[str, Dict[str, Any]] = {}


def get_session(user_id: str) -> Dict[str, Any]:
    s = sessions.setdefault(
        user_id,
        {
            "symptoms": [],
            "queue": [],
            "current_symptom": None,
            "step": 0,
            "asked_questions": {},
            "asked_global": set(),
            "done": set(),
            "last_question": None,
            "asked_screen_for": set(),
            # global triage
            "global_slots": {},
            "global_pending": None,
            "severity_once": False,
        },
    )
    return s


def reset_session(user_id: str) -> None:
    sessions.pop(user_id, None)
