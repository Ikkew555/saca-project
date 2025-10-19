# back-end/app/i18n_kriol_panlex.py
from __future__ import annotations
import re
from pathlib import Path
import pandas as pd

# ---------- Paths (adjust if needed) ----------
RESOURCE_DIR = Path(__file__).resolve().parents[1] / "resources" / "panlex"
PAIRS_FP = RESOURCE_DIR / "kriol_english_pairs.tsv"
ONE2ONE_FP = RESOURCE_DIR / "kriol_english_one2one.tsv"
GLOSS_FP = RESOURCE_DIR / "kriol_english_gloss.tsv"

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)

# Proper names we usually keep in English
PROTECT_EN = [
    "Northern Territory",
    "Primary Health Care",
    "Centrelink",
    "Services Australia",
    "Traditional Credit Union",
    "EFTPOS",
    "BPAY",
    "SmartCard",
    "service centre",
    "digital wallet",
]

# English → Kriol style choices (orthography/idiom)
EN_TO_KRIOL_OVERRIDES = {
    # frequent health UI terms
    "plenty": "plenti",
    "water": "watta",
    "stomach": "bel",
    "belly": "bel",
    "head": "hed",
    "and": "an",
    "too": "tu",
    "very": "hevi",  # used in e.g., "hevi smol"
    "small": "smol",
    "rest": "rest",
    "pain": "pain",
    "vomit": "sikap",
    "fever": "fiva",
    # short phrases
    "drink plenty of water": "drink plenti watta",
    "go to the clinic": "go klinik",
    "get medical help": "garem help la dokta",
    "shortness of breath": "breath short",
}


def _load_tsv(path: Path, expected_cols=None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=expected_cols or [])
    df = pd.read_csv(path, sep="\t", dtype=str).fillna("")
    if expected_cols:
        for c in expected_cols:
            if c not in df.columns:
                df[c] = ""
        df = df[expected_cols]
    return df


def _normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _build_en2kriol():
    """
    Build English→Kriol resources from your TSVs:
      - phrase_table (multiword, longest-first)
      - dict_en2kr (one-to-one)
      - gloss_en2kr (very rough fallback)
    """
    pairs = _load_tsv(PAIRS_FP, ["kriol", "english"])
    one2one = _load_tsv(ONE2ONE_FP, ["kriol", "english"])
    gloss = _load_tsv(GLOSS_FP, ["kriol", "english_gloss"])

    # Multiword English→Kriol phrase table (prefer shortest Kriol)
    pr = pairs[(pairs["english"].str.contains(r"\s", na=False))]
    phrase_table = {}
    for en, kr in zip(pr["english"], pr["kriol"]):
        enl = _normalize_space(en).lower()
        kr = _normalize_space(kr)
        if not enl or not kr:
            continue
        if enl not in phrase_table or len(kr) < len(phrase_table[enl]):
            phrase_table[enl] = kr
    phrase_keys = sorted(
        phrase_table.keys(), key=lambda s: len(s.split()), reverse=True
    )

    # One-to-one dictionary (English→Kriol)
    dict_en2kr = {
        _normalize_space(en).lower(): _normalize_space(kr)
        for en, kr in zip(one2one["english"], one2one["kriol"])
        if _normalize_space(en)
    }

    # Gloss fallback: map English gloss → shortest Kriol seen
    gloss_en2kr = {}
    if not gloss.empty:
        for kr, en_g in zip(gloss["kriol"], gloss["english_gloss"]):
            kr = _normalize_space(kr)
            eng = _normalize_space(en_g).lower()
            if (
                eng
                and kr
                and (eng not in gloss_en2kr or len(kr) < len(gloss_en2kr[eng]))
            ):
                gloss_en2kr[eng] = kr

    return phrase_table, phrase_keys, dict_en2kr, gloss_en2kr


# Lazy global cache
_RES_EN2KR = None


def _get_en2kr():
    global _RES_EN2KR
    if _RES_EN2KR is None:
        _RES_EN2KR = _build_en2kriol()
    return _RES_EN2KR


def _protect_proper_names(txt: str) -> str:
    t = txt
    for p in PROTECT_EN:
        t = re.sub(rf"\b{re.escape(p)}\b", p.replace(" ", "_"), t)
    return t


def _unprotect_proper_names(txt: str) -> str:
    t = txt
    for p in PROTECT_EN:
        t = t.replace(p.replace(" ", "_"), p)
    return t


def en_to_kriol(text: str) -> str:
    """
    Deterministic EN→Kriol:
      - protect proper names
      - longest phrase match (EN→KR)
      - token-level overrides → dictionary → gloss → copy-through
      - small spacing cleanups
    """
    if text is None:
        return ""
    s = _normalize_space(str(text))
    if not s:
        return s

    phrase_table, phrase_keys, dict_en2kr, gloss_en2kr = _get_en2kr()

    # Protect names
    s = _protect_proper_names(s)
    low = s.lower()

    used = [False] * len(s)
    out_chars = list(s)

    def mark_and_replace(start, end, repl):
        out_chars[start:end] = list(repl.ljust(end - start))
        for i in range(start, end):
            used[i] = True

    # Longest phrase replacement
    for pk in phrase_keys:
        idx = low.find(pk)
        while idx != -1:
            end = idx + len(pk)
            left_ok = (idx == 0) or (not low[idx - 1].isalnum())
            right_ok = (end == len(low)) or (not low[end : end + 1].isalnum())
            if left_ok and right_ok and not any(used[idx:end]):
                mark_and_replace(idx, end, phrase_table[pk])
            idx = low.find(pk, idx + 1)

    # Token-wise pass
    tokens = []
    i = 0
    while i < len(s):
        if used[i]:
            j = i
            while j < len(s) and used[j]:
                j += 1
            tokens.append("".join(out_chars[i:j]).strip())
            i = j
            continue

        m = TOKEN_RE.match(s, i)
        if not m:
            tokens.append(s[i])
            i += 1
            continue

        tok = m.group(0)
        if tok.isalnum():
            base = tok.lower()
            # 1) hard EN→KR overrides (style/orthography)
            kr = EN_TO_KRIOL_OVERRIDES.get(base)
            if not kr:
                # 2) dictionary, 3) gloss fallback
                kr = dict_en2kr.get(base) or gloss_en2kr.get(base)
            tokens.append(kr if kr else tok)
        else:
            tokens.append(tok)
        i = m.end()

    out = re.sub(r"\s+", " ", "".join(tokens)).strip()
    out = re.sub(r"\s+([,.!?;:])", r"\1", out)
    out = _unprotect_proper_names(out)
    return out


# Optional: use the existing Kriol→English translator if available
try:
    # Your uploaded helper provides translate_kriol() and pre_normalize_asr()
    from panlexread import translate_kriol as kriol_to_english  # noqa
    from panlexread import pre_normalize_asr  # noqa
except Exception:

    def kriol_to_english(text: str) -> str:
        # Minimal fallback if panlexread.py isn't present in runtime
        return text

    def pre_normalize_asr(text: str) -> str:
        return text
