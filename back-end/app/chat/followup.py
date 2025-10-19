# back-end/app/chat/followup.py
import re
from .data import df_followup


def normalize_qtext(q: str, symptom: str) -> str:
    if not q:
        return ""
    q = q.replace(symptom or "", "{symptom}")
    q = re.sub(r"\s+", " ", q.strip().lower())
    return q


def get_next_question(symptom, step, lang="english", asked=None, asked_global=None):
    if not symptom:
        sub = df_followup[df_followup["symptom"] == "general"]
    else:
        sym_lower = str(symptom).strip().lower()
        sub = df_followup[df_followup["symptom"] == sym_lower]
        if sub.empty:
            sub = df_followup[
                df_followup["symptom"].apply(lambda x: sym_lower in str(x))
            ]
        if sub.empty:
            sub = df_followup[df_followup["symptom"] == "general"]

    col = "question_kriol" if lang == "kriol" else "question_en"
    if col not in sub.columns:
        return None, True

    qs = sub.sort_values("order")[col].dropna().tolist()
    if asked:
        qs = [q for q in qs if q not in asked]

    if asked_global is not None:
        filtered = []
        for q in qs:
            key = normalize_qtext(q, symptom)
            if key not in asked_global:
                filtered.append(q)
        qs = filtered

    if not qs:
        sub = df_followup[df_followup["symptom"] == "general"]
        qs = sub.sort_values("order")[col].dropna().tolist()
        if asked:
            qs = [q for q in qs if q not in asked]
        if asked_global is not None:
            qs = [q for q in qs if normalize_qtext(q, symptom) not in asked_global]

    qs = qs[:4]
    if step < len(qs):
        return qs[step], False
    return None, True


def format_question(q, symptom):
    if not q:
        return f"How long have you had the {symptom}?"
    return q.replace("{symptom}", symptom)
