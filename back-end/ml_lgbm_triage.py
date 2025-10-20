#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LightGBM triage trainer / predictor.

Usage:
  Train:
    py ml_lgbm_triage.py train --data PATH --out PATH [--target severity]

  Predict:
    py ml_lgbm_triage.py predict --data PATH --model PATH [--out-csv PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from pandas.api.types import CategoricalDtype

from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split


# -----------------------
# Config / constants
# -----------------------

DEFAULT_TARGET = "severity"
CANDIDATE_NUMERIC_COLS = ["duration_days", "temp_c", "hr", "spo2"]
CANDIDATE_CATEGORICAL_COLS = ["age_band", "intensity"]
SYMPTOM_PREFIX = "symptom:"

DEFAULT_LABELS = ["mild", "moderate", "severe"]  # ensure stable order


@dataclass
class PrepSummary:
    n_features_before: int
    n_features_after: int
    categorical_cols: List[str]
    dropped_constant: List[str]
    used_features: List[str]


# -----------------------
# Helpers
# -----------------------

def _read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    return pd.read_csv(path)


def _split_features_target(df: pd.DataFrame, target_col: str) -> Tuple[pd.DataFrame, pd.Series]:
    if target_col not in df.columns:
        raise ValueError(
            f"Expected target column '{target_col}' not found. Columns: {list(df.columns)}"
        )
    y = df[target_col].astype(str)
    X = df.drop(columns=[target_col])
    return X, y


def _discover_feature_sets(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
    """
    Returns (num_cols, cat_cols, symptom_cols) that actually exist in df.
    """
    num_cols = [c for c in CANDIDATE_NUMERIC_COLS if c in df.columns]
    cat_cols = [c for c in CANDIDATE_CATEGORICAL_COLS if c in df.columns]
    symptom_cols = [c for c in df.columns if c.startswith(SYMPTOM_PREFIX)]
    return num_cols, cat_cols, symptom_cols


def _coerce_types(X: pd.DataFrame, num_cols: List[str], cat_cols: List[str]) -> pd.DataFrame:
    X = X.copy()
    # numerics -> float
    for c in num_cols:
        if c in X.columns:
            X[c] = pd.to_numeric(X[c], errors="coerce")
    # symptoms -> binary ints (0/1)
    for c in [col for col in X.columns if col.startswith(SYMPTOM_PREFIX)]:
        X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0).astype(int)
        X[c] = (X[c] > 0).astype(int)
    # categoricals -> pandas 'category'
    for c in cat_cols:
        if c in X.columns:
            X[c] = X[c].astype("category")
    return X


def _drop_constant_or_allnull(X: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    drops: List[str] = []
    for c in list(X.columns):
        col = X[c]
        if col.isna().all():
            drops.append(c)
            continue
        if isinstance(col.dtype, CategoricalDtype):
            if len(col.cat.categories) <= 1:
                drops.append(c)
        else:
            if col.nunique(dropna=True) <= 1:
                drops.append(c)
    X2 = X.drop(columns=drops) if drops else X
    return X2, drops


# --- NEW: feature-name sanitizer to satisfy LightGBM / JSON constraints ---

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_]+")

def _sanitize_name(name: str) -> str:
    # Replace any non [A-Za-z0-9_] with underscore
    cleaned = SAFE_NAME_RE.sub("_", name)
    # Avoid leading digits (LightGBM is okay, but keep it tidy)
    if cleaned and cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned

def _sanitize_columns(X: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Return a copy of X with safe column names and a mapping {original -> safe}.
    Ensures uniqueness even after sanitization by adding numeric suffixes.
    """
    name_map: Dict[str, str] = {}
    used: Dict[str, int] = {}

    for c in X.columns:
        base = _sanitize_name(c)
        safe = base
        # ensure uniqueness
        while safe in used:
            used[base] = used.get(base, 1) + 1
            safe = f"{base}_{used[base]}"
        used[safe] = 1
        name_map[c] = safe

    X_safe = X.copy()
    X_safe.columns = [name_map[c] for c in X.columns]
    return X_safe, name_map


def _prepare_training_frame(df: pd.DataFrame, target_col: str) -> Tuple[pd.DataFrame, pd.Series, PrepSummary]:
    X, y = _split_features_target(df, target_col)

    num_cols, cat_cols, symptom_cols = _discover_feature_sets(X)

    # Keep only the columns we actually want to consider
    candidate_cols = num_cols + cat_cols + symptom_cols
    X = X[[c for c in candidate_cols if c in X.columns]].copy()

    # Type coercion
    X = _coerce_types(X, num_cols=num_cols, cat_cols=cat_cols)

    # Drop constants / all-null columns
    before = X.shape[1]
    X, dropped = _drop_constant_or_allnull(X)
    after = X.shape[1]

    # Record which of the categorical columns survived
    cat_cols_after = [c for c in cat_cols if c in X.columns]

    return X, y, PrepSummary(
        n_features_before=before,
        n_features_after=after,
        categorical_cols=cat_cols_after,
        dropped_constant=dropped,
        used_features=list(X.columns),
    )


def _build_classifier() -> CalibratedClassifierCV:
    """
    LightGBM wrapped in isotonic calibration.
    Verbosity is suppressed to avoid the “no further splits” floods.
    """
    base = LGBMClassifier(
        objective="multiclass",
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=-1,
        min_data_in_leaf=5,
        min_gain_to_split=0.0,
        feature_fraction=0.9,
        bagging_fraction=0.8,
        bagging_freq=1,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )
    # sklearn >= 1.4 uses `estimator=`
    clf = CalibratedClassifierCV(estimator=base, cv=3, method="isotonic")
    return clf


def _evaluate(y_true: pd.Series, proba: np.ndarray, labels: List[str]) -> Dict[str, float]:
    y_pred = [labels[int(np.argmax(row))] for row in proba]
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro")
    # AUC: one-vs-rest
    try:
        inv = {lab: i for i, lab in enumerate(labels)}
        y_idx = np.array([inv.get(v, -1) for v in y_true])
        mask = y_idx >= 0
        macro_auc = roc_auc_score(
            y_idx[mask],
            proba[mask],
            average="macro",
            multi_class="ovr"
        )
    except Exception:
        macro_auc = float("nan")

    return {"acc": acc, "macro_f1": macro_f1, "macro_roc_auc": macro_auc}


def _align_for_inference(df: pd.DataFrame,
                         feature_names: List[str],
                         cat_idx: List[int]) -> pd.DataFrame:
    """
    Build an inference frame with EXACT columns (order + dtypes) used for training.
    - Missing columns are created (0 for symptoms / NaN for numerics).
    - Extra columns are ignored.
    - Categorical columns (by index) are set to pandas 'category'.
    """
    X = df.copy()

    # Create any missing columns with sensible defaults
    for c in feature_names:
        if c not in X.columns:
            if c.startswith("symptom_"):  # note: sanitized names use underscore
                X[c] = 0
            else:
                X[c] = np.nan

    # keep only used features, in the trained order
    X = X[feature_names].copy()

    # coerce types: guess cats by indices, symptoms by sanitized prefix, rest numerics
    for i, c in enumerate(feature_names):
        if i in cat_idx:
            X[c] = X[c].astype("category")
        elif c.startswith("symptom_"):
            X[c] = pd.to_numeric(X[c], errors="coerce").fillna(0).astype(int)
            X[c] = (X[c] > 0).astype(int)
        else:
            X[c] = pd.to_numeric(X[c], errors="coerce")

    return X


# -----------------------
# Train / Predict commands
# -----------------------

def train_cmd(data_path: str, out_path: str, target_col: str) -> None:
    df = _read_csv(data_path)

    X_all, y_all, prep = _prepare_training_frame(df, target_col)
    labels = sorted(y_all.unique().tolist(), key=lambda k: DEFAULT_LABELS.index(k) if k in DEFAULT_LABELS else 999)

    # --- sanitize feature names before any split / training ---
    X_all_safe, name_map = _sanitize_columns(X_all)

    # Train/validation split
    X_tr, X_te, y_tr, y_te = train_test_split(
        X_all_safe, y_all, test_size=0.20, random_state=42, stratify=y_all
    )

    # Identify categorical feature indexes (by position in columns)
    # map original categorical names -> sanitized names, then locate
    sanitized_cat_cols = [name_map[c] for c in prep.categorical_cols if c in name_map]
    feature_names = list(X_tr.columns)
    cat_idx = [feature_names.index(c) for c in sanitized_cat_cols if c in feature_names]

    clf = _build_classifier()

    # Fit
    clf.fit(X_tr, y_tr)

    # Evaluate
    proba_te = clf.predict_proba(X_te)
    if isinstance(proba_te, list):  # very old sklearn fallback
        proba_te = np.vstack(proba_te).T
    metrics = _evaluate(y_te, proba_te, labels=labels)

    # Bundle for runtime
    bundle = {
        "version": 2,
        "model": clf,
        "labels": labels,
        "feature_names": feature_names,              # sanitized names in order
        "cat_feature_indices": cat_idx,
        "sanitizer": {"pattern": r"[^A-Za-z0-9_]+", "leading_digit_prefix": "_"},
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    joblib.dump(bundle, out_path)

    report = {
        "saved": out_path,
        "n_train_rows": int(X_tr.shape[0]),
        "n_features_used": int(len(feature_names)),
        "prep_summary": {
            "n_features_before": prep.n_features_before,
            "n_features_after": prep.n_features_after,
            "categorical_cols": prep.categorical_cols,
            "dropped_constant": prep.dropped_constant,
            "used_features_original": prep.used_features,
            "used_features_sanitized": feature_names,
        },
        "metrics": metrics,
    }
    print(json.dumps(report, indent=2))


def _sanitize_incoming_like_training(df: pd.DataFrame, sanitizer_cfg: Dict) -> pd.DataFrame:
    """
    Apply the same sanitization logic to an inference frame as training.
    """
    pattern = sanitizer_cfg.get("pattern", r"[^A-Za-z0-9_]+")
    leading_prefix = sanitizer_cfg.get("leading_digit_prefix", "_")
    rx = re.compile(pattern)

    def _clean(col: str) -> str:
        out = rx.sub("_", col)
        if out and out[0].isdigit():
            out = leading_prefix + out
        return out

    X = df.copy()
    # rename columns; if collisions occur here, pandas will allow duplicates,
    # so we must de-duplicate deterministically by suffixing with _2, _3, ...
    new_cols = []
    seen = {}
    for c in X.columns:
        base = _clean(c)
        name = base
        if name in seen:
            seen[base] += 1
            name = f"{base}_{seen[base]}"
        else:
            seen[base] = 1
        new_cols.append(name)
    X.columns = new_cols
    return X


def predict_cmd(data_path: str, model_path: str, out_csv: str | None) -> None:
    df = _read_csv(data_path)

    bundle = joblib.load(model_path)
    clf: CalibratedClassifierCV = bundle["model"]
    labels: List[str] = bundle["labels"]
    feature_names: List[str] = bundle["feature_names"]       # sanitized
    cat_idx: List[int] = bundle.get("cat_feature_indices", [])
    sanitizer_cfg: Dict = bundle.get("sanitizer", {"pattern": r"[^A-Za-z0-9_]+", "leading_digit_prefix": "_"})

    # Apply the same sanitization to incoming columns
    X = _sanitize_incoming_like_training(df, sanitizer_cfg)

    # Align exactly to training features
    X = _align_for_inference(X, feature_names, cat_idx)

    # Predict proba
    proba = clf.predict_proba(X)
    if isinstance(proba, list):
        proba = np.vstack(proba).T

    # Predicted label per row
    pred_idx = np.argmax(proba, axis=1)
    pred_labels = [labels[i] for i in pred_idx]

    # Compose output
    out = pd.DataFrame({
        "prediction": pred_labels,
    })

    # Always produce columns for these three, filling with NaN if not trained
    want = ["mild", "moderate", "severe"]
    name_map = {lab: f"proba_{lab}" for lab in want}
    for lab in want:
        out[name_map[lab]] = np.nan

    # Fill the trained label proba into the proper columns
    for j, lab in enumerate(labels):
        colname = name_map.get(lab, f"proba_{lab}")
        out[colname] = proba[:, j]

    # Optionally save
    if out_csv:
        out.to_csv(out_csv, index=False)
        print(json.dumps({
            "model": model_path,
            "n_rows": int(len(out)),
            "preview": out.head(5).to_dict(orient="records"),
            "saved_csv": out_csv
        }, indent=2))
    else:
        print(out.head().to_string(index=False))


# -----------------------
# CLI
# -----------------------

def main():
    parser = argparse.ArgumentParser(description="LightGBM triage trainer/predictor")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_train = sub.add_parser("train", help="Train LightGBM model")
    p_train.add_argument("--data", required=True, help="Path to prepared CSV")
    p_train.add_argument("--out", required=True, help="Path to save joblib bundle")
    p_train.add_argument("--target", default=DEFAULT_TARGET, help=f"Target column (default: {DEFAULT_TARGET})")

    p_pred = sub.add_parser("predict", help="Predict with saved model")
    p_pred.add_argument("--data", required=True, help="Path to prepared CSV for inference")
    p_pred.add_argument("--model", required=True, help="Path to joblib bundle")
    p_pred.add_argument("--out-csv", default="predictions_lgbm.csv", help="Where to write predictions CSV")

    args = parser.parse_args()

    if args.cmd == "train":
        train_cmd(args.data, args.out, args.target)
    elif args.cmd == "predict":
        predict_cmd(args.data, args.model, args.out_csv)
    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    main()