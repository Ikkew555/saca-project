# app/utils.py
import re
import pandas as pd
from unidecode import unidecode
import warnings
import difflib


warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")


# handle misspellings
def correct_spelling(word, vocabulary, cutoff=0.8):
    """
    Finds the closest match for 'word' within the given vocabulary using fuzzy matching.
    Returns the corrected word if a close match is found; otherwise, returns the original.
    """
    match = difflib.get_close_matches(word.lower(), vocabulary, n=1, cutoff=cutoff)
    return match[0] if match else word


# -------- Normalization helpers --------
def normalize_text(s: str) -> str:
    s = unidecode(s or "")
    s = s.casefold()
    s = re.sub(r"[^a-z0-9\s']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# -------- Loaders --------
def load_kriol_lexicon(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    left_col = None
    for cand in ["kriol_phrase", "term", "phrase", "pattern"]:
        if cand in df.columns:
            left_col = cand
            break
    if left_col is None:
        raise ValueError(
            f"Lexicon CSV must have kriol_phrase/term. Found: {df.columns.tolist()}"
        )
    if "symptom" not in df.columns:
        raise ValueError("Lexicon CSV must have a 'symptom' column")

    df["term_raw"] = df[left_col].astype(str)
    df["symptom_raw"] = df["symptom"].astype(str)
    df["term_norm"] = df["term_raw"].map(normalize_text)
    df["symptom_norm"] = df["symptom_raw"].map(normalize_text)

    df = df[(df["term_norm"] != "") & (df["symptom_norm"] != "")]
    df = df.drop_duplicates(subset=["term_norm", "symptom_norm"]).reset_index(drop=True)
    return df


def load_symptom_disease_map(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in ["symptom", "disease", "weight"]:
        if col not in df.columns:
            raise ValueError(
                "symptom_to_disease.csv must contain columns: symptom,disease,weight"
            )
    df["symptom_norm"] = df["symptom"].astype(str).map(normalize_text)
    df["disease"] = df["disease"].astype(str).str.strip()
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(0.0)
    df = df[df["symptom_norm"] != ""].reset_index(drop=True)
    return df


# -------- Synonyms --------
SYM_SYNONYMS = {
    "cough": ["coughing"],
    "chest pain": ["tight chest", "pressure in chest", "pain in chest"],
    "shortness of breath": [
        "breathlessness",
        "hard to breathe",
        "cant breathe",
        "can't breathe",
    ],
    "sore throat": ["throat pain"],
    "diarrhea": ["diarrhoea", "loose stools"],
    "vomiting": ["throwing up"],
    "headache": ["head pain", "migraine"],
    "wheeze": ["wheezing"],
    "fever": ["high temperature", "temperature"],
    "fatigue": ["tiredness", "exhaustion"],
    "dizziness": ["lightheaded"],
    "rash": ["skin rash"],
}


def _build_patterns(lex_df: pd.DataFrame):
    pairs = []
    for _, row in lex_df.iterrows():
        term = row["term_norm"]
        sym = row["symptom_norm"]
        if term and sym:
            pairs.append((term, sym))
    for canonical, variants in SYM_SYNONYMS.items():
        can = normalize_text(canonical)
        for v in variants:
            pairs.append((normalize_text(v), can))
        pairs.append((can, can))
    compiled = []
    for term, sym in pairs:
        if not term:
            continue
        pat = r"\b" + r"\s+".join(map(re.escape, term.split())) + r"\b"
        compiled.append((re.compile(pat), sym))
    compiled.sort(key=lambda x: -len(x[0].pattern))
    return compiled


_patterns_cache = None


import difflib


def extract_symptoms(text: str, lex_df: pd.DataFrame) -> list[str]:
    """
    Extract multiple symptoms from natural language text.
    Uses both regex pattern matching and fuzzy typo correction.
    Also supports partial phrases (e.g. 'hot head' -> 'fever', 'head spin' -> 'dizziness').
    """
    global _patterns_cache
    if _patterns_cache is None:
        _patterns_cache = _build_patterns(lex_df)

    # --- 1️⃣ Normalize text ---
    t = normalize_text(text)
    found, used_spans = [], []

    # --- 2️⃣ Pattern-based matching from lexicon & synonyms ---
    for pat, sym in _patterns_cache:
        for m in pat.finditer(t):
            span = m.span()
            # Skip overlaps with already matched patterns
            if any(a < span[1] and span[0] < b for (a, b) in used_spans):
                continue
            found.append(sym)
            used_spans.append(span)

    # --- 3️⃣ Prepare vocabulary for typo correction ---
    vocab = list(lex_df["symptom"].dropna().unique())
    vocab += list(lex_df["kriol_phrase"].dropna().unique()) if "kriol_phrase" in lex_df.columns else []
    vocab = [normalize_text(v) for v in vocab if v]

    # --- 4️⃣ Tokenize text into possible words and 2-word phrases ---
    tokens = t.split()
    token_pairs = [" ".join(tokens[i:i+2]) for i in range(len(tokens) - 1)]
    all_tokens = tokens + token_pairs  # single + two-word phrases

    corrected_words = []
    for token in all_tokens:
        match = difflib.get_close_matches(token, vocab, n=1, cutoff=0.75)
        if match:
            corrected_words.append(match[0])

    # --- 5️⃣ Add corrected symptom matches if not already found ---
    for word in corrected_words:
        # Try mapping to actual symptom (for kriol/phrase variants)
        match_rows = lex_df[
            (lex_df["symptom"].str.lower() == word)
            | (("kriol_phrase" in lex_df.columns) & (lex_df["kriol_phrase"].str.lower() == word))
        ]
        for _, row in match_rows.iterrows():
            symptom_name = row["symptom"]
            if symptom_name not in found:
                found.append(symptom_name)

    # --- 6️⃣ Clean up duplicates while preserving order ---
    out, seen = [], set()
    for s in found:
        if s not in seen:
            seen.add(s)
            out.append(s)

    return out


# -------- Scoring --------
def score_diseases(symptoms: list[str], sym_df: pd.DataFrame) -> pd.DataFrame:
    if not symptoms:
        return pd.DataFrame(columns=["disease", "score"])
    syms_norm = [normalize_text(s) for s in symptoms if s]
    sub = sym_df[sym_df["symptom_norm"].isin(syms_norm)].copy()
    if sub.empty:
        return pd.DataFrame(columns=["disease", "score"])
    scores = sub.groupby("disease", as_index=False)["weight"].sum()
    scores = scores.rename(columns={"weight": "score"})
    scores = scores.sort_values("score", ascending=False).reset_index(drop=True)
    return scores
