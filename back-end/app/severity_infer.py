# back-end/app/severity_infer.py
from __future__ import annotations
import os
from typing import Dict, List, Optional, Any
import warnings

import numpy as np
import pandas as pd

try:
    import lightgbm as lgb

    HAVE_LGB = True
except Exception as e:
    HAVE_LGB = False
    _LGB_IMPORT_ERR = e

try:
    import joblib

    HAVE_JOBLIB = True
except Exception as e:
    HAVE_JOBLIB = False
    _JOBLIB_IMPORT_ERR = e


# --------- Fallback (used only if model can't be loaded) --------------------
_RED_FLAGS = {
    "chest pain",
    "shortness of breath",
    "trouble breathing",
    "confusion",
    "fainting",
    "blue lips",
    "bluish lips",
    "stiff neck",
}
_MOD_HINTS = {
    "fever",
    "vomiting",
    "diarrhea",
    "dizziness",
    "shortness of breath",
    "wheeze",
    "wheezing",
    "abdominal pain",
}


def _fallback_rule(symptoms: List[str], slots: Dict[str, Any]) -> Dict[str, Any]:
    syms = {(s or "").strip().lower() for s in (symptoms or [])}
    mild, moderate, severe = 0.55, 0.30, 0.15

    if syms.intersection(_RED_FLAGS):
        severe += 0.30
    if slots.get("redflags") is True:
        severe += 0.50

    t = slots.get("temp_c")
    hr = slots.get("hr")
    spo2 = slots.get("spo2")
    if isinstance(t, (int, float)):
        if t >= 39:
            severe += 0.25
        elif t >= 38:
            moderate += 0.15
    if isinstance(hr, (int, float)):
        if hr >= 120:
            severe += 0.25
        elif hr >= 100:
            moderate += 0.15
    if isinstance(spo2, (int, float)):
        if spo2 < 92:
            severe += 0.35
        elif spo2 < 95:
            moderate += 0.20

    inten = (slots.get("intensity") or "").strip().lower()
    if inten == "severe":
        severe += 0.25
    elif inten == "moderate":
        moderate += 0.15

    dur = slots.get("duration_days")
    age = slots.get("age")
    if isinstance(dur, (int, float)):
        if dur >= 14:
            severe += 0.10
        elif dur >= 7:
            moderate += 0.10
    if isinstance(age, (int, float)) and age >= 65:
        severe += 0.15

    if len(syms.intersection(_MOD_HINTS)) >= 2 or len(syms) >= 3:
        moderate += 0.25

    tot = max(1e-9, mild + moderate + severe)
    probs = {"mild": mild / tot, "moderate": moderate / tot, "severe": severe / tot}
    label = max(probs, key=probs.get)
    return {"label": label, "probabilities": probs}


# --------- LightGBM loader ---------------------------------------------------
# Candidates for where your model lives (override with env var SEVERITY_MODEL_PATH)
_MODEL_CANDIDATES = [
    os.environ.get("SEVERITY_MODEL_PATH"),
    os.path.join("data", "lgbm_severity.joblib"),
    os.path.join("app", "models", "lgbm_severity.joblib"),
    os.path.join("models", "lgbm_severity.joblib"),
]

_TXT_CANDIDATES = [
    os.path.join("data", "lgbm_severity.txt"),
    os.path.join("app", "models", "lgbm_severity.txt"),
    os.path.join("models", "lgbm_severity.txt"),
]

_MODEL = None  # lgb.LGBMClassifier or lgb.Booster
_FEATS = None  # List[str] feature names in training order
_CLASSES = None  # class labels from the model


def _try_load_joblib(path: str):
    global _MODEL, _FEATS, __CLASSES
    if not (HAVE_JOBLIB and HAVE_LGB):
        return False
    try:
        m = joblib.load(path)
        _MODEL = m
        # Feature names
        names = None
        if hasattr(m, "booster_") and m.booster_ is not None:
            try:
                names = list(m.booster_.feature_name())
            except Exception:
                names = None
        if names is None and hasattr(m, "feature_name_"):
            names = list(m.feature_name_)
        if names is None and hasattr(m, "feature_name"):
            try:
                names = list(m.feature_name())
            except Exception:
                names = None
        _FEATS = names

        # Classes
        if hasattr(m, "classes_"):
            _CL = list(m.classes_)
        else:
            _CL = ["mild", "moderate", "severe"]  # best-effort default
        _CL = [str(c).lower() for c in _CL]
        # map 0/1/2 to strings if ints
        mapping = {0: "mild", 1: "moderate", 2: "severe"}
        _CL = [mapping.get(c, str(c)) for c in _CL]
        _GLOBALS = {"mild", "moderate", "severe"}
        # normalize any weird labels
        _CL = [
            (
                c
                if c in _GLOBALS
                else mapping.get(int(c), "mild") if str(c).isdigit() else "mild"
            )
            for c in _CL
        ]
        _CL = list(_CL)
        # order
        global _CLASSES
        _CLASSES = _CL
        print(
            f"🔊 Loaded LightGBM model from {path} with {len(_FEATS) if _FEATS else '?'} features; classes={_CLASSES}"
        )
        return True
    except Exception as e:
        warnings.warn(f"Could not load joblib model at {path}: {e}")
        return False


def _try_load_txt(path: str):
    global _MODEL, _FEATS, _CLASSES
    if not HAVE_LGB:
        return False
    try:
        booster = lgb.Booster(model_file=path)
        _MODEL = booster
        _FEATS = list(booster.feature_name())
        _CLASSES = [
            "mild",
            "moderate",
            "severe",
        ]  # Booster alone doesn't store label names
        print(f"🔊 Loaded LightGBM Booster from {path} with {len(_FEATS)} features.")
        return True
    except Exception as e:
        warnings.warn(f"Could not load LightGBM Booster at {path}: {e}")
        return False


def _ensure_loaded():
    """Ensure a model is loaded, else leave _MODEL=None to use fallback."""
    global _MODEL
    if _MODEL is not None:
        return
    # Try joblib models first
    for p in _MODEL_CANDIDATES:
        if p and os.path.exists(p) and _try_load_joblib(p):
            return
    # Try text booster (version-agnostic)
    for p in _TXT_CANDIDATES:
        if p and os.path.exists(p) and _try_load_txt(p):
            return
    # As a very last resort, try inferring features from a prepared CSV (optional)
    csv_guess = os.path.join("data", "triage_prepared.csv")
    if os.path.exists(csv_guess):
        print(
            "ℹ️ Model not found; will use fallback but cached columns from triage_prepared.csv for debugging only."
        )
    # If we got here, we'll use the fallback scorer.


# --------- Feature building ---------------------------------------------------
def _intensity_to_score(val: Any) -> Optional[float]:
    s = (str(val or "")).strip().lower()
    if s == "mild":
        return 0.0
    if s == "moderate":
        return 1.0
    if s == "severe":
        return 2.0
    try:
        # allow numeric strings like "2"
        return float(s)
    except Exception:
        return None


def _feature_vector(
    symptoms: List[str], slots: Dict[str, Any], feats: List[str]
) -> pd.DataFrame:
    """
    Build a 1xN feature row matching the LightGBM training columns.
    Heuristics:
      - direct numeric: age, duration_days, temp_c, hr, spo2
      - redflags / has_redflags: 0/1
      - intensity: either one-hot (intensity_mild/moderate/severe) or numeric score
      - symptom_* OR plain symptom names: 0/1 by presence
      - unknown columns -> 0
    """
    syms = {(s or "").strip().lower() for s in (symptoms or [])}
    row: Dict[str, float] = {}

    for f in feats:
        fl = (f or "").strip().lower()

        # Directly mapped numeric slots
        if fl in {"age", "duration_days", "temp_c", "hr", "spo2"}:
            v = slots.get(fl)
            row[f] = float(v) if isinstance(v, (int, float)) else np.nan
            continue

        # Red flags binary
        if fl in {"redflags", "has_redflags"}:
            v = slots.get("redflags")
            row[f] = 1.0 if v is True else 0.0 if v is False else 0.0
            continue

        # Intensity encodings
        if fl in {"intensity", "intensity_score"}:
            sc = _intensity_to_score(slots.get("intensity"))
            row[f] = float(sc) if sc is not None else np.nan
            continue
        if fl in {"intensity_mild", "intensity_moderate", "intensity_severe"}:
            target = fl.split("_", 1)[-1]
            row[f] = (
                1.0 if (slots.get("intensity") or "").strip().lower() == target else 0.0
            )
            continue

        # Symptom one-hots: "symptom_xxx" or "symptom:xxx"
        if fl.startswith("symptom_") or fl.startswith("symptom:"):
            name = (
                fl.split("_", 1)[-1]
                if fl.startswith("symptom_")
                else fl.split(":", 1)[-1]
            )
            row[f] = 1.0 if name in syms else 0.0
            continue

        # Plain symptom names as features
        if fl in syms:
            row[f] = 1.0
            continue

        # Default: 0
        row[f] = 0.0

    # NaNs -> sensible fills
    ser = pd.Series(row, index=feats, dtype="float64")
    if "age" in ser.index and pd.isna(ser["age"]):
        ser.loc["age"] = 35.0
    if "duration_days" in ser.index and pd.isna(ser["duration_days"]):
        ser.loc["duration_days"] = 2.0
    # temp/hr/spo2 can stay NaN; LightGBM handles NaNs natively
    return pd.DataFrame([ser.values], columns=feats)


# --------- Public API (used by routes) ---------------------------------------
def predict_severity(
    symptoms: List[str], global_slots: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Preferred entry point. Uses LightGBM if available and model is loaded,
    otherwise falls back to a rules-based estimate.
    Returns: {"label": "mild|moderate|severe", "probabilities": {...}}
    """
    slots = global_slots or {}
    _ensure_loaded()

    # If we have a model, run it
    if HAVE_LGB and _MODEL is not None:
        try:
            if hasattr(_MODEL, "predict_proba"):
                feats = _FEATS
                if not feats:
                    # last-ditch: pull from booster
                    feats = (
                        list(_MODEL.booster_.feature_name())
                        if hasattr(_MODEL, "booster_")
                        else None
                    )
                if not feats:
                    raise RuntimeError("No feature names found on LightGBM model.")
                X = _feature_vector(symptoms, slots, feats)
                proba = _MODEL.predict_proba(X)[0]
            else:
                # Booster
                feats = _FEATS or []
                if not feats:
                    feats = list(_MODEL.feature_name())
                X = _feature_vector(symptoms, slots, feats)
                proba = _MODEL.predict(X, raw_score=False)
                # Booster.predict returns shape (n_samples,) if num_class=1 or (n_samples, num_class)
                proba = np.atleast_2d(proba)[0]

            # Align to classes
            classes = _CLASSES or ["mild", "moderate", "severe"]
            if len(proba) != len(classes):
                # try to coerce 3-way to (mild, moderate, severe)
                if len(proba) == 3:
                    classes = ["mild", "moderate", "severe"]
                else:
                    raise RuntimeError(
                        f"Model returned {len(proba)} probs but classes={classes}"
                    )

            probs = {
                str(classes[i]).lower(): float(proba[i]) for i in range(len(classes))
            }
            # Normalize / clip
            s = sum(max(0.0, v) for v in probs.values())
            if s <= 0:
                probs = {"mild": 1.0, "moderate": 0.0, "severe": 0.0}
            else:
                probs = {k: max(0.0, v) / s for k, v in probs.items()}

            label = max(probs, key=probs.get)
            return {"label": label, "probabilities": probs}

        except Exception as e:
            warnings.warn(f"LightGBM prediction failed, using fallback: {e}")

    # Fallback if no model or error
    return _fallback_rule(symptoms, slots)


# ---- Back-compat shims (other parts of your app import these) ----------------
def predict_severity_for_session(
    symptoms: List[str], core_answers: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    return predict_severity(symptoms, core_answers)


def predict_severity_for_match(
    payload_or_syms: Any = None, global_slots: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Accepts:
      - list of symptoms, or
      - dict with {"symptoms": [...], "slots": {...}} (names flexible)
    """
    if isinstance(payload_or_syms, list):
        return predict_severity(payload_or_syms, global_slots or {})
    if isinstance(payload_or_syms, dict):
        syms = (
            payload_or_syms.get("symptoms") or payload_or_syms.get("symptom_list") or []
        )
        slots = (
            payload_or_syms.get("slots")
            or payload_or_syms.get("global_slots")
            or global_slots
            or {}
        )
        return predict_severity(syms, slots)
    return predict_severity([], global_slots or {})
