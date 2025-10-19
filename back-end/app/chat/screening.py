# back-end/app/chat/screening.py
import hashlib

SCREEN_BUDDIES = {
    "headache": ["fever", "cough", "sore throat", "nausea", "dizziness"],
    "chest pain": ["shortness of breath", "cough", "fever", "dizziness"],
    "cough": ["fever", "sore throat", "shortness of breath", "wheeze"],
    "fever": ["cough", "sore throat", "headache", "rash", "fatigue"],
    "sore throat": ["cough", "fever", "headache"],
    "shortness of breath": ["cough", "wheeze", "chest pain"],
    "abdominal pain": ["nausea", "vomiting", "diarrhea", "fever"],
    "nausea": ["vomiting", "abdominal pain", "dizziness"],
    "vomiting": ["nausea", "abdominal pain", "diarrhea", "fever"],
    "diarrhea": ["abdominal pain", "vomiting", "fever"],
    "rash": ["fever", "itching", "headache"],
}

TEMPLATES_EN = [
    "Do you also have {list}?",
    "Have you noticed {list} too?",
    "Along with that, any {list}?",
    "Are you experiencing {list} as well?",
]
TEMPLATES_KR = [
    "Yu gat {list} tu?",
    "Wit dat, eni {list}?",
    "Yu bin notis {list} tu?",
    "Yu gat {list} la?",
]


def _choose_template(lang: str, key: str) -> str:
    arr = TEMPLATES_KR if lang == "kriol" else TEMPLATES_EN
    idx = int(hashlib.sha256(key.encode()).hexdigest(), 16) % len(arr)
    return arr[idx]


def _fmt_list(items: list[str], lang: str) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return (
            f"{items[0]} or {items[1]}"
            if lang == "english"
            else f"{items[0]} o {items[1]}"
        )
    return ", ".join(items[:-1]) + (" or " if lang == "english" else " o ") + items[-1]


def get_screening_candidates(current_symptom: str, session, topk: int = 2) -> list[str]:
    if not current_symptom:
        return []
    cand = SCREEN_BUDDIES.get(current_symptom.lower(), [])
    if not cand:
        return []
    asked_global = session.get("asked_global", set())
    known = set(map(str.lower, session.get("symptoms", [])))
    out = []
    for c in cand:
        if c.lower() in known:
            continue
        qkey = f"screen:{current_symptom.lower()}->{c.lower()}"
        if qkey in asked_global:
            continue
        out.append(c)
        if len(out) >= topk:
            break
    return out


def build_screen_question(current_symptom: str, session, lang: str = "english"):
    cands = get_screening_candidates(current_symptom, session, topk=2)
    if not cands:
        return None, None
    lst = _fmt_list(cands, lang)
    template = _choose_template(lang, f"{current_symptom}-{session.get('step',0)}")
    qtext = template.format(list=lst)
    qkey = " && ".join(
        [f"screen:{current_symptom.lower()}->{c.lower()}" for c in cands]
    )
    return qtext, qkey
