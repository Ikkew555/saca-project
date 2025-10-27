"""
train_model.py — Train a disease prediction model using symptom datasets
Author: Nathakorn Wimonwatwethi
Updated: 2025-10-14
"""

import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.utils import resample
from joblib import dump
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# ───────────────────────────────
# 1️⃣ Load dataset
# ───────────────────────────────
if os.path.exists("../data/ml_training_dataset_extended.csv"):
    dataset_path = "../data/ml_training_dataset_extended.csv"
    print("🧩 Using extended dataset (ml_training_dataset_extended.csv)")
else:
    dataset_path = "../data/ml_training_dataset.csv"
    print("📄 Using base dataset (ml_training_dataset.csv)")

df = pd.read_csv(dataset_path)
print(f"🧠 Loaded {len(df)} samples with {len(df.columns) - 1} symptoms.\n")

# ───────────────────────────────
# 2️⃣ Prepare data for training
# ───────────────────────────────
if "disease" not in df.columns:
    raise ValueError("❌ The dataset must contain a 'disease' column.")

# Separate features and target
X = df.drop(columns=["disease"])
y = df["disease"]

# Handle missing values if any
X = X.fillna(0)

# ───────────────────────────────
# 3️⃣ Balance dataset (upsampling rare diseases)
# ───────────────────────────────
print("⚖️ Balancing dataset by upsampling rare diseases...")
df_balanced = df.groupby("disease", group_keys=False).apply(
    lambda x: resample(x, replace=True, n_samples=min(80, len(df)), random_state=42)
)
X = df_balanced.drop(columns=["disease"])
y = df_balanced["disease"]
print(
    f"✅ After balancing: {len(df_balanced)} total samples across {len(y.unique())} diseases.\n"
)

# ───────────────────────────────
# 4️⃣ Train-test split
# ───────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ───────────────────────────────
# 5️⃣ Model training (with light tuning)
# ───────────────────────────────
print("🌲 Training RandomForest model with GridSearchCV (light tuning)...")

param_grid = {
    "n_estimators": [100, 200],
    "max_depth": [10, 20, None],
    "min_samples_split": [2, 5],
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42, class_weight="balanced"),
    param_grid,
    cv=3,
    n_jobs=-1,
    verbose=0,
)

grid_search.fit(X_train, y_train)
model = grid_search.best_estimator_

print(f"✅ Best Params: {grid_search.best_params_}\n")

# ───────────────────────────────
# 6️⃣ Evaluation
# ───────────────────────────────
y_pred = model.predict(X_test)

print("📊 Classification Report:")
print(classification_report(y_test, y_pred, zero_division=0))

acc = accuracy_score(y_test, y_pred)
print(f"✅ Accuracy: {acc:.2f}")

# Show confusion matrix
cm = pd.DataFrame(
    confusion_matrix(y_test, y_pred, labels=model.classes_),
    index=[f"True {c}" for c in model.classes_],
    columns=[f"Pred {c}" for c in model.classes_],
)
print("\n🧩 Confusion Matrix:")
print(cm.head(10))  # print top 10 to avoid long output

# ───────────────────────────────
# 7️⃣ Save trained model
# ───────────────────────────────
dump((model, list(X.columns)), "../data/disease_model.pkl")

print("\n💾 Model saved to '../data/disease_model.pkl'")
print(f"🩺 Features trained: {list(X.columns)[:10]} ... ({len(X.columns)} total)")
print("──────────────────────────────")
