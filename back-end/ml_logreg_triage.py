#!/usr/bin/env python3
# ml_logreg_triage.py
# Train / predict triage severity with Logistic Regression (multiclass).
# Usage:
#   py ml_logreg_triage.py train --data data\triage_prepared.csv --out models\logreg_severity.joblib [--target severity]
#   py ml_logreg_triage.py predict --data data\triage_prepared.csv --model models\logreg_severity.joblib --out-csv predictions_logreg.csv

import argparse
import json
import os
import sys
from typing import List, Tuple, Dict

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

# ---------------------------
# Constants / Defaults
# ---------------------------

DEFAULT_TARGET = "severity"
DEFAULT_CLASSES = ["mild", "moderate", "severe"]

# Characters that can cause problems in downstream libs / JSON
SPECIAL_CHARS = ['"', "'", "{", "}", "[", "]", ":", ",", "=", ";", "|", "\\", "/", "(", ")", " "]

# ---------------------------
# Helpers
# ---------------------------

def sanitize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename columns to avoid problematic characters and duplicates.
    Keeps order, guarantees uniqueness, replaces SPECIAL_CHARS with underscores,
    and collapses multiple underscores.
    """
    new_cols = []
    seen = set()
    for c in df.columns:
        nc = str(c)
        for ch in SPECIAL_CHARS:
            nc = nc.replace(ch, "_")
        # collapse multiple underscores
        nc = "_".join(filter(None, nc.split("_")))
        # ensure uniqueness
        base = nc
        k = 1
        while nc in seen:
            k += 1
            nc = f"{base}_{k}"
        seen.add(nc)
        new_cols.append(nc)
    out = df.copy()
    out.columns = new_cols
    return out


def detect_categorical(df: pd.DataFrame) -> List[str]:
    """
    Pick likely categorical columns. We know about 'intensity' and 'age_band' if present.
    Also include any 'object' dtype columns.
    """
    cat = []
    for cand in ["intensity", "age_band"]:
        if cand in df.columns:
            cat.append(cand)
    # Any other text-like columns
    cat += [c for c in df.columns if df[c].dtype == "object" and c not in cat]
    # dedup, preserve order
    return list(dict.fromkeys(cat))


def drop_constant_columns(df: pd.DataFrame, ignore: List[str]) -> Tuple[pd.DataFrame, List[str]]:
    """
    Drop columns with <= 1 unique values, excluding those in ignore.
    Return the reduced df and a list of dropped column names.
    """
    dropped = []
    keep_cols = []
    for c in df.columns:
        if c in ignore:
            keep_cols.append(c)
            continue
        if df[c].nunique(dropna=False) <= 1:
            dropped.append(c)
        else:
            keep_cols.append(c)
    return df[keep_cols].copy(), dropped


def _make_ohe():
    """
    Create a OneHotEncoder that works across sklearn versions.
    sklearn >= 1.2 uses 'sparse_output'; < 1.2 uses 'sparse'.
    """
    try:
        # sklearn >= 1.2
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        # sklearn < 1.2
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_pipeline(num_cols: List[str], cat_cols: List[str]) -> Pipeline:
    """
    Build a robust preprocessing + LogisticRegression pipeline.
    """
    num_pipe = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler(with_mean=True, with_std=True)),
    ])

    cat_pipe = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", _make_ohe()),
    ])

    pre = ColumnTransformer(
        transformers=[
            ("num", num_pipe, num_cols),
            ("cat", cat_pipe, cat_cols),
        ],
        remainder="drop",
    )

    clf = LogisticRegression(max_iter=1000, random_state=42)

    pipe = Pipeline(steps=[
        ("preprocess", pre),
        ("clf", clf),
    ])
    return pipe


def _normalize_target(y: pd.Series) -> pd.Series:
    """
    Normalize target labels to mild / moderate / severe when possible.
    Leaves unknown labels as-is (string).
    """
    y = y.astype(str).str.strip().str.lower()
    return (
        y.replace({
            "mild": "mild",
            "moderate": "moderate",
            "mod": "moderate",
            "sev": "severe",
            "severe": "severe"
        })
    )

# ---------------------------
# Commands
# ---------------------------

def train_cmd(data_csv: str, out_path: str, target_col: str):
    df_raw = pd.read_csv(data_csv)
    df = sanitize_columns(df_raw)

    if target_col not in df.columns:
        print(json.dumps({"error": f"Target column '{target_col}' not found in CSV."}, indent=2))
        sys.exit(2)

    # Target
    y = _normalize_target(df[target_col])

    # Features (pre-drop)
    X = df.drop(columns=[target_col])

    # Detect types
    cat_cols = detect_categorical(X)
    num_cols = [c for c in X.columns if c not in cat_cols]

    # Drop constants (ignore list empty; target already removed)
    X, dropped_constants = drop_constant_columns(X, ignore=[])

    # Re-evaluate types post-drop
    cat_cols = [c for c in cat_cols if c in X.columns]
    num_cols = [c for c in X.columns if c not in cat_cols]

    # Build pipeline
    pipe = build_pipeline(num_cols=num_cols, cat_cols=cat_cols)

    # Train/valid split for quick metrics
    strat = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=strat
    )

    pipe.fit(X_train, y_train)

    # Metrics
    y_pred = pipe.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro")

    macro_roc_auc = None
    try:
        proba = pipe.predict_proba(X_test)
        macro_roc_auc = roc_auc_score(y_test, proba, multi_class="ovr", average="macro")
    except Exception:
        pass

    # Persist expected columns (after sanitize & drop constants)
    expected_features = list(X.columns)

    # Save bundle
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    classes_ = list(getattr(pipe.named_steps["clf"], "classes_", []))
    bundle = {
        "pipeline": pipe,
        "meta": {
            "target": target_col,
            "cat_cols": cat_cols,
            "num_cols": num_cols,
            "dropped_constant": dropped_constants,
            "columns_after_sanitize": list(df.columns),
            "expected_features": expected_features,
            "classes_": classes_,
        },
    }
    joblib.dump(bundle, out_path)

    # Report
    out = {
        "saved": out_path,
        "n_train_rows": int(X_train.shape[0]),
        "n_features_used": int(len(expected_features)),
        "prep_summary": {
            "n_features_before": int(df.drop(columns=[target_col]).shape[1]),
            "n_features_after": int(X.shape[1]),
            "categorical_cols": cat_cols,
            "dropped_constant": dropped_constants,
            "used_features": expected_features,
        },
        "metrics": {
            "acc": acc,
            "macro_f1": macro_f1,
            "macro_roc_auc": macro_roc_auc,
        },
    }
    print(json.dumps(out, indent=2))


def _align_predict_frame(df_in: pd.DataFrame, target_col: str, expected_features: List[str]) -> pd.DataFrame:
    """
    Sanitize columns, drop target if present, add any missing training columns as NaN,
    and drop any extra columns not seen during training. Preserve training column order.
    """
    df = sanitize_columns(df_in)
    X = df.drop(columns=[c for c in [target_col] if c in df.columns]).copy()

    # Add missing expected columns with NaN
    for c in expected_features:
        if c not in X.columns:
            X[c] = np.nan

    # Keep only expected columns, in the exact order
    X = X[expected_features]

    return X


def predict_cmd(data_csv: str, model_path: str, out_csv: str):
    bundle = joblib.load(model_path)
    pipe: Pipeline = bundle["pipeline"]
    meta: Dict = bundle.get("meta", {})
    target_col = meta.get("target", DEFAULT_TARGET)
    classes = meta.get("classes_", DEFAULT_CLASSES)
    expected_features = meta.get("expected_features", None)

    df_raw = pd.read_csv(data_csv)

    if expected_features is None:
        # Fallback: sanitize and just drop target if present (older bundles)
        df = sanitize_columns(df_raw)
        X = df.drop(columns=[c for c in [target_col] if c in df.columns])
    else:
        X = _align_predict_frame(df_raw, target_col=target_col, expected_features=expected_features)

    # Predict
    preds = pipe.predict(X)

    # Predict probabilities if available
    proba_mild = np.zeros(len(preds))
    proba_moderate = np.zeros(len(preds))
    proba_severe = np.zeros(len(preds))

    try:
        probas = pipe.predict_proba(X)  # columns follow pipe.named_steps['clf'].classes_
        proba_map = {cls: probas[:, i] for i, cls in enumerate(classes)}
        proba_mild = proba_map.get("mild", proba_mild)
        proba_moderate = proba_map.get("moderate", proba_moderate)
        proba_severe = proba_map.get("severe", proba_severe)
    except Exception:
        pass

    out_df = X.copy()
    out_df.insert(0, "prediction", preds)
    out_df["proba_mild"] = proba_mild
    out_df["proba_moderate"] = proba_moderate
    out_df["proba_severe"] = proba_severe

    if out_csv:
        out_df.to_csv(out_csv, index=False)

    preview = out_df[["prediction", "proba_mild", "proba_moderate", "proba_severe"]].head(5).to_dict(orient="records")
    out = {
        "model": model_path,
        "n_rows": int(len(out_df)),
        "preview": preview,
        "saved_csv": out_csv,
    }
    print(json.dumps(out, indent=2))


# ---------------------------
# CLI
# ---------------------------

def main():
    p = argparse.ArgumentParser(description="Logistic Regression triage trainer / predictor")
    sub = p.add_subparsers(dest="cmd", required=True)

    pt = sub.add_parser("train", help="Train a logistic regression model")
    pt.add_argument("--data", required=True, help="Path to training CSV")
    pt.add_argument("--out", required=True, help="Path to save model (joblib)")
    pt.add_argument("--target", default=DEFAULT_TARGET, help=f"Target column (default: {DEFAULT_TARGET})")

    pp = sub.add_parser("predict", help="Predict using a saved model")
    pp.add_argument("--data", required=True, help="Path to CSV to score")
    pp.add_argument("--model", required=True, help="Path to saved model (joblib)")
    pp.add_argument("--out-csv", default="predictions_logreg.csv", help="Where to save scored CSV")

    args = p.parse_args()
    if args.cmd == "train":
        train_cmd(args.data, args.out, args.target)
    elif args.cmd == "predict":
        predict_cmd(args.data, args.model, args.out_csv)
    else:
        p.print_help()


if __name__ == "__main__":
    main()