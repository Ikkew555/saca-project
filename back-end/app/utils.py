# app/utils.py
import re
import pandas as pd
from unidecode import unidecode
import warnings
import difflib
import os, uuid, subprocess

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

MISHEAR_MAP = {
    # Kriol/phonetic → English
    #new data -----------------------------------
    # ── General / ทั่วไป ─────────────────────────────────────────
    "sik": "sick",
    "mi sik": "sick",
    "mi no gud": "fatigue",
    "no gud": "fatigue",
    "feel sik": "fatigue",
    "weak la bodi": "fatigue",
    "taya": "fatigue",
    "hot bodi": "fever",
    "hot la bodi": "fever",
    "kolda": "chills",
    "shiva": "chills",

    # ── Head / Neuro ────────────────────────────────────────────
    "sik la hed": "headache",
    "sik la head": "headache",
    "hed eik": "headache",
    "hed pain": "headache",
    "hed spin": "dizziness",
    "spinning head": "dizziness",
    "giddy": "dizziness",
    "dizzy": "dizziness",
    "no si gud": "blurred vision",
    "blurry ai": "blurred vision",

    # ── Chest / Respiratory ─────────────────────────────────────
    "sik la chest": "chest pain",
    "sik chest": "chest pain",
    "pain la chest": "chest pain",
    "bref short": "shortness of breath",
    "short bref": "shortness of breath",
    "no breth gud": "shortness of breath",
    "hard fo breth": "shortness of breath",
    "breath hard": "hard to breathe",
    "kof": "cough",
    "got kof": "cough",
    "dry kof": "dry cough",
    "wet kof": "productive cough",
    "wheez": "wheeze",
    "nois brethin": "wheeze",

    # ── Throat / ENT ────────────────────────────────────────────
    "sik la troat": "sore throat",
    "sik la throat": "sore throat",
    "troat pain": "sore throat",
    "troat hot": "sore throat",
    "runny nose": "runny nose",
    "blok nose": "blocked nose",
    "ear pain": "ear pain",
    "sik la iya": "ear pain",

    # ── GI (ท้อง) ───────────────────────────────────────────────
    "bel sik": "abdominal pain",
    "sik la bel": "abdominal pain",
    "bel pain": "abdominal pain",
    "soram bel": "abdominal pain",
    "laf bel": "abdominal cramps",
    "hebi bel": "bloating",
    "puke": "vomiting",
    "sek up": "nausea",
    "feel puke": "nausea",
    "run bel": "diarrhea",
    "runny bel": "diarrhea",
    "stin bel": "constipation",
    "gas bel": "bloating",

    # ── GU / UTI ────────────────────────────────────────────────
    "piss hot": "dysuria",
    "pisi hot": "dysuria",
    "piss planti": "urinary frequency",
    "piss smol smol": "urinary frequency",
    "no piss gud": "urinary retention",
    "bela piss": "hematuria",

    # ── Skin ────────────────────────────────────────────────────
    "rais": "rash",
    "itchi": "itching",
    "skin hot": "rash",
    "skin red": "rash",
    "swellap": "swelling",
    "swolap": "swelling",

    # ── Systemic / อื่น ๆ ──────────────────────────────────────
    "pain evri wea": "body aches",
    "soram bodi": "body aches",
    "joint pain": "joint pain",
    "bon pain": "bone pain",
    "no kaikai": "loss of appetite",
    #old --------------------
    "sik la chest": "chest pain",
    "sik chest": "chest pain",
    "sik la hed": "headache",
    "sik la head": "headache",
    "sik la bel": "abdominal pain",
    "bel sik": "abdominal pain",
    "sik la troat": "sore throat",
    "sik la throat": "sore throat",
    "sik": "sick",
    "hed eik": "headache",
    "hedache": "headache",
    "sot trot": "sore throat",
    "sot troat": "sore throat",
    "sot throat": "sore throat",
    "chest pane": "chest pain",
    "chest pen": "chest pain",
    "breath hard": "hard to breathe",
    "no breath": "cant breathe",
    # English variants / fillers (ลด noise จาก voice)
    "tummy bug": "vomiting",
    "light headed": "lightheaded",
    "flu": "fever",
    "i feel": "",
    "maybe": "",
    "like": "",
    "and": "",
    "dizzy": "dizziness",
    "giddy": "dizziness",
    "head spin": "dizziness",
    "spinning head": "dizziness",
    "vertigo": "dizziness",
}

KRIOL_SYNONYMS = {
    # General
    "fever": ["hot bodi", "hot la bodi", "hot body"],
    "chills": ["kolda", "shiva"],
    "fatigue": ["mi no gud", "no gud", "feel sik", "weak la bodi", "taya"],
    "unwell": ["mi no gud", "no gud", "feel sik"],

    # Head / Neuro
    "headache": ["sik la hed", "sik la head", "hed eik", "hed pain"],
    "dizziness": ["hed spin", "head spin", "giddy", "spinning head", "dizzy"],
    "blurred vision": ["no si gud", "blurry ai"],

    # Chest / Respiratory
    "chest pain": ["sik la chest", "sik chest", "pain la chest"],
    "shortness of breath": ["bref short", "short bref", "no breth gud", "hard fo breth"],
    "hard to breathe": ["breath hard"],
    "cough": ["kof", "got kof"],
    "dry cough": ["dry kof"],
    "productive cough": ["wet kof"],
    "wheeze": ["wheez", "nois brethin"],

    # Throat / ENT
    "sore throat": ["sik la troat", "sik la throat", "troat pain", "troat hot"],
    "runny nose": ["runny nose"],
    "blocked nose": ["blok nose"],
    "ear pain": ["sik la iya", "ear pain"],

    # GI
    "abdominal pain": ["bel sik", "sik la bel", "bel pain", "soram bel"],
    "abdominal cramps": ["laf bel"],
    "bloating": ["hebi bel", "gas bel"],
    "vomiting": ["puke"],
    "nausea": ["sek up", "feel puke"],
    "diarrhea": ["run bel", "runny bel"],
    "constipation": ["stin bel"],

    # GU / UTI
    "dysuria": ["piss hot", "pisi hot"],
    "urinary frequency": ["piss planti", "piss smol smol"],
    "urinary retention": ["no piss gud"],
    "hematuria": ["bela piss"],

    # Skin
    "rash": ["rais", "skin hot", "skin red"],
    "itching": ["itchi"],
    "swelling": ["swellap", "swolap"],

    # Systemic
    "body aches": ["pain evri wea", "soram bodi"],
    "joint pain": ["joint pain"],
    "bone pain": ["bon pain"],
    "loss of appetite": ["no kaikai"],
}

def apply_mishear(text: str, mishear_map: dict) -> str:
    """แทนที่คำที่มักได้ยินเพี้ยนแบบ word-boundary (ไม่ไปโดนคำอื่น)"""
    if not text or not mishear_map:
        return text or ""
    pat = re.compile(r"\b(" + "|".join(map(re.escape, mishear_map.keys())) + r")\b", re.IGNORECASE)
    def repl(m):
        return mishear_map.get(m.group(0).lower(), m.group(0))
    return pat.sub(repl, text)

def preprocess_text(raw: str, mishear_map: dict = None) -> str:
    """ขั้นตอนกลางใช้ได้ทั้ง chat/voice: unidecode → mishear → lower → trim spaces"""
    t = (raw or "").strip()
    t = unidecode(t)
    if mishear_map:
        t = apply_mishear(t, mishear_map)
    t = t.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t

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
    "chest pain": ["tight chest", "pressure in chest", "pain in chest", "sik la chest"],
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
    "dizziness": ["lightheaded", "dizzy", "giddy", "head spin", "spinning head", "vertigo"],
    "rash": ["skin rash"],
}


def _build_patterns(lex_df: pd.DataFrame):
    pairs = []
    # จาก lexicon เดิม
    for _, row in lex_df.iterrows():
        term = row["term_norm"]; sym = row["symptom_norm"]
        if term and sym:
            pairs.append((term, sym))

    # จาก synonyms อังกฤษ
    for canonical, variants in SYM_SYNONYMS.items():
        can = normalize_text(canonical)
        for v in variants:
            pairs.append((normalize_text(v), can))
        pairs.append((can, can))

    # ✅ จาก KRIOL_SYNONYMS (ใหม่)
    for canonical, variants in KRIOL_SYNONYMS.items():
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
    compiled.sort(key=lambda x: -len(x[0].pattern))  # ยาวก่อน
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
    for can, vars in SYM_SYNONYMS.items():
        vocab.append(can)
        vocab.extend(vars)
    vocab = [normalize_text(v) for v in vocab if v]

    # --- 4️⃣ Tokenize text into possible words and 2-word phrases ---
    tokens = t.split()
    token_pairs = [" ".join(tokens[i:i+2]) for i in range(len(tokens) - 1)]
    token_triples = [" ".join(tokens[i:i+3]) for i in range(len(tokens) - 2)]
    all_tokens = tokens + token_pairs  # single + two-word phrases

    corrected_words = []
    for token in all_tokens:
        cutoff = 0.6 if len(token) <= 5 else 0.75
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
        mapped = False
        for _, row in match_rows.iterrows():
            symptom_name = row["symptom"]
            if symptom_name not in found:
                found.append(symptom_name)
                mapped = True
        if mapped:
            continue

        for can, vars in SYM_SYNONYMS.items():
            if word == normalize_text(can) or word in [normalize_text(v) for v in vars]:
                if can not in found:
                    found.append(can)
            break

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

def to_wav_16k_mono(src_path: str, out_dir: str = "uploads") -> str:
    """
    Convert any input audio (e.g., webm/m4a/mp3) to 16kHz mono WAV.
    Requires ffmpeg in PATH.
    """
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, f"{uuid.uuid4().hex}.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", src_path, "-ac", "1", "-ar", "16000", "-vn", dst],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return dst
