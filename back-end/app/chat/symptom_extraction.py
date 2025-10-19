# back-end/app/chat/symptom_extraction.py
import re
from .data import df_symptom, SYMPTOM_COLUMN


def extract_symptoms(text: str) -> list[str]:
    """Robust phrase-aware matching; avoids 'pain' over-matching."""
    text = (text or "").lower().strip()
    found = []

    for s in df_symptom[SYMPTOM_COLUMN].dropna().unique():
        s_clean = str(s).strip().lower()

        # exact phrase
        if re.search(rf"\b{re.escape(s_clean)}\b", text):
            found.append(s_clean)
            continue

        # relaxed multi-word containment
        parts = s_clean.split()
        if len(parts) > 1:
            key_words = [w for w in parts if len(w) > 2]
            if all(w in text for w in key_words):
                found.append(s_clean)

    # de-duplicate shortest overlaps
    found = sorted(found, key=len, reverse=True)
    cleaned = []
    for f in found:
        if not any(f in longer for longer in cleaned):
            cleaned.append(f)
    return cleaned
