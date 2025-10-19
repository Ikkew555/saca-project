# back-end/app/chat/predict.py
import numpy as np
import pandas as pd
from joblib import load
from .data import df_symptom

# Load ML model (optional)
try:
    model, features = load("./data/disease_model.pkl")
    print(f"✅ ML model loaded successfully with {len(features)} features.")
except Exception as e:
    model, features = None, []
    print(f"⚠️ ML model not loaded: {e}")


def predict_disease(symptoms):
    matches = df_symptom[df_symptom["symptom"].isin(symptoms)]
    if matches.empty:
        return {}
    agg = matches.groupby("disease")["weight"].sum().sort_values(ascending=False)
    return agg.head(3).to_dict()


def predict_disease_ml(symptoms):
    if model is None or not features:
        return predict_disease(symptoms)
    x_input = np.zeros(len(features))
    for s in symptoms:
        if s in features:
            x_input[features.index(s)] = 1
    x_df = pd.DataFrame([x_input], columns=features)
    proba = model.predict_proba(x_df)[0]
    top_idx = np.argsort(proba)[::-1][:3]
    return {model.classes_[i]: float(proba[i]) for i in top_idx}
