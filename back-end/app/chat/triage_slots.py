# back-end/app/chat/triage_slots.py
import re
from typing import Optional

# Reusable yes/no sets for parsing
YES = {"yes", "y", "yeah", "yep", "true", "1"}
NO = {"no", "n", "nah", "nope", "false", "0", "skip"}


def _num(text: Optional[str]) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)", text or "")
    return float(match.group(1)) if match else None


def _duration_days(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    n = _num(text)
    if n is None:
        return None
    lowered = text.lower()
    if "hour" in lowered or "hr" in lowered or "hrs" in lowered:
        return max(0.1, n / 24.0)
    if "week" in lowered or "wk" in lowered or "wks" in lowered:
        return n * 7.0
    # assume days
    return n


def _temp_c(text: Optional[str]) -> Optional[float]:
    n = _num(text)
    if n is None:
        return None
    lowered = (text or "").lower()
    # If user wrote °F (or mentions F) without °C, convert to C
    if "f" in lowered and "°c" not in lowered:
        return round((n - 32) * 5 / 9, 2)
    return n


def _percent(text: Optional[str]) -> Optional[float]:
    n = _num(text)
    if n is None:
        return None
    if n <= 1.0:  # allow 0.95 style
        n *= 100.0
    return n


def _intensity(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    lowered = (text or "").lower()
    if "severe" in lowered or "serious" in lowered or "bad" in lowered:
        return "severe"
    if "moderate" in lowered or "mid" in lowered:
        return "moderate"
    if "mild" in lowered or "smol" in lowered:
        return "mild"
    return None


def _redflags(text: Optional[str]) -> Optional[bool]:
    """
    Returns True/False/None. True if user indicates any urgent symptom,
    False if explicit 'no', None if unclear.
    """
    if not text:
        return None
    lowered = (text or "").strip().lower()

    if lowered in YES:
        return True
    if lowered in NO:
        return False

    keywords = [
        "trouble breathing",
        "shortness of breath",
        "sob",
        "severe chest pain",
        "chest pain",
        "confusion",
        "faint",
        "fainting",
        "passed out",
        "blue lips",
        "bluish lips",
        "blue face",
        "bluish face",
        "stiff neck",
    ]
    return any(k in lowered for k in keywords) or None


# Ask in this exact order. We include "redflags" after duration.
GLOBAL_ORDER = ["age", "duration_days", "redflags", "temp_c", "hr", "spo2", "intensity"]

PROMPTS = {
    "english": {
        "age": "How old are you (in years)?",
        "duration_days": "How long has this been going on (hours/days/weeks)?",
        "redflags": "Any urgent symptoms like trouble breathing, severe chest pain, confusion, fainting, or blue lips/face? (yes/no)",
        "temp_c": "Do you know your temperature (°C or °F)? You can say 'skip'.",
        "hr": "Do you know your heart rate (beats per minute)? You can say 'skip'.",
        "spo2": "Do you know your oxygen level (SpO₂ %)? You can say 'skip'.",
        "intensity": "How intense is it: mild, moderate, or severe?",
    },
    "kriol": {
        "age": "Yu old la hamas yia?",
        "duration_days": "Diswan bin hapen la hamas taem (awa/dei/wik)?",
        "redflags": "Yu gat eni bigwan sik olsem trabel fo breath, big chest pain, konfiusen, faint, o blu lip/fes? (yes/no)",
        "temp_c": "Yu save yu temp (°C o °F)? Yu ken se 'skip'.",
        "hr": "Yu save hamas yu hat reit (bpm)? Yu ken se 'skip'.",
        "spo2": "Yu save yu oksijin lebel (SpO₂ %)? Yu ken se 'skip'.",
        "intensity": "Im hamas: smol (mild), midol (moderate), o bigwan (severe)?",
    },
}


def parse_answer(key: str, text: Optional[str]):
    if key == "age":
        return _num(text)
    if key == "duration_days":
        return _duration_days(text)
    if key == "redflags":
        return _redflags(text)
    if key == "temp_c":
        return _temp_c(text)
    if key == "hr":
        return _num(text)
    if key == "spo2":
        return _percent(text)
    if key == "intensity":
        return _intensity(text)
    return None


def required_done(slots: dict) -> bool:
    """
    Control WHEN we allow finalization/severity.
    Require these before we say 'triage ready':
      - age
      - duration_days
      - redflags (explicit yes/no or inferred keywords)
      - intensity (mild/moderate/severe)
    Vitals (temp/hr/spo2) remain optional but are asked once via GLOBAL_ORDER.
    """
    need = ("age", "duration_days", "redflags", "intensity")
    return all(k in slots and slots[k] is not None for k in need)


def ask_next(slots: dict, lang: str):
    """
    Find the next missing slot in GLOBAL_ORDER and return (prompt, key).
    Returns (None, None) if everything asked at least once.
    """
    for k in GLOBAL_ORDER:
        if k not in slots:
            return PROMPTS[lang].get(k), k
    return None, None
