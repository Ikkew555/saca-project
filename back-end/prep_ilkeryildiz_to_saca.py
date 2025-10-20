#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse, re
import pandas as pd
import numpy as np
from pathlib import Path

SYM_VOCAB = [
    "fever","cough","headache","sore_throat","shortness_of_breath",
    "chest_pain","fatigue","nausea","vomiting","diarrhea","dizziness"
]

LABEL_CANDIDATES = ["triage","class","category","label","priority","ktas_expert","ktas"]
TEXT_CANDIDATES = ["chief", "complain", "complaint", "reason", "symptom", "present", "description"]
AGE_CANDS = ["age"]
TEMP_CANDS = ["bt","temp","temperature","body_temp"]
HR_CANDS = ["hr","heart_rate","pulse"]
SPO2_CANDS = ["spo2","saturation","o2","oxygen"]


def sniff_sep(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        head = f.read(2048)
    return ";" if head.count(";") > head.count(",") else ","


def guess_col(cols, candidates):
    lower = {c.lower(): c for c in cols}
    for g in candidates:
        if g in lower:
            return lower[g]
    for c in cols:
        lc = c.lower()
        if any(g in lc for g in candidates):
            return c
    return None


def to_age_band(x):
    try:
        a = float(str(x).replace(",", "."))
    except Exception:
        return "adult"
    if a < 13:
        return "child"
    if a >= 65:
        return "elder"
    return "adult"


def map_label(v):
    s = str(v).strip().lower()
    # color / word mapping
    if s in ["red","r","1","high","urgent","critical"]:
        return "severe"
    if s in ["yellow","y","2","medium","moderate"]:
        return "moderate"
    if s in ["green","g","3","low","non-urgent","non urgent","not urgent"]:
        return "mild"
    # numeric fallback
    try:
        n = int(float(s))
        if n == 1:
            return "severe"
        if n == 2:
            return "moderate"
        if n == 3:
            return "mild"
    except Exception:
        pass
    return None


def extract_symptoms_from_text(text: str):
    if not isinstance(text, str):
        return []
    t = text.lower()
    found = set()
    rules = {
        "shortness_of_breath": [r"short(ness)? of breath", r"breathless", r"dyspnea", r"\bsob\b"],
        "chest_pain": [r"chest pain", r"tight chest", r"pressure chest"],
        "sore_throat": [r"sore throat", r"throat pain"],
        "fever": [r"\bfever\b", r"high temp", r"temperature"],
        "cough": [r"\bcough"],
        "headache": [r"\bheadache\b", r"migraine"],
        "fatigue": [r"\bfatigue\b", r"tired(ness)?"],
        "nausea": [r"\bnausea\b", r"queasy"],
        "vomiting": [r"\bvomit"],
        "diarrhea": [r"diarrh(o|oe)a"],
        "dizziness": [r"dizz(y|iness)", r"vertigo"],
    }
    for sym, pats in rules.items():
        if any(re.search(p, t) for p in pats):
            found.add(sym)
    return sorted(found)


def coerce_float(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().replace(",", ".")
    try:
        return float(s)
    except Exception:
        return np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", required=True)
    ap.add_argument("--out_csv", default="data/triage_prepared.csv")
    args = ap.parse_args()

    sep = sniff_sep(args.in_csv)
    df = pd.read_csv(args.in_csv, sep=sep)

    label_col = guess_col(df.columns, LABEL_CANDIDATES)
    text_col = guess_col(df.columns, TEXT_CANDIDATES)
    age_col = guess_col(df.columns, AGE_CANDS)
    temp_col = guess_col(df.columns, TEMP_CANDS)
    hr_col = guess_col(df.columns, HR_CANDS)
    spo2_col = guess_col(df.columns, SPO2_CANDS)

    if not label_col:
        raise SystemExit("Could not find a triage label column. Please specify it matches one of: " + ", ".join(LABEL_CANDIDATES))

    rows = []
    for _, r in df.iterrows():
        lbl = map_label(r[label_col])
        if lbl is None:
            continue
        row = {
            "duration_days": 0.0,
            "intensity": "unknown",
            "age_band": to_age_band(r[age_col]) if age_col else "adult",
            "temp_c": coerce_float(r[temp_col]) if temp_col else np.nan,
            "hr": coerce_float(r[hr_col]) if hr_col else np.nan,
            "spo2": coerce_float(r[spo2_col]) if spo2_col else np.nan,
            "severity": lbl,
        }
        syms = extract_symptoms_from_text(r[text_col]) if text_col else []
        for s in SYM_VOCAB:
            row[f"symptom:{s}"] = 1 if s in syms else 0
        rows.append(row)

    out = pd.DataFrame(rows)
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out_csv, index=False)
    print(f"Wrote: {args.out_csv}  Shape: {out.shape}")

if __name__ == "__main__":
    main()