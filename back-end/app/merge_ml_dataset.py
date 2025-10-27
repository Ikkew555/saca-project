import pandas as pd

# Load all datasets
df_base = pd.read_csv("../data/ml_training_dataset.csv")
df_kaggle1 = pd.read_csv("../data/Training.csv")
df_kaggle2 = pd.read_csv("../data/train_disease.csv")

# Standardize column names
df_base.rename(columns={"disease": "prognosis"}, inplace=True)
df_kaggle2.rename(columns={"Disease": "prognosis"}, inplace=True)

# Get all symptom columns (union of all)
all_symptoms = set(df_base.columns) | set(df_kaggle1.columns) | set(df_kaggle2.columns)
all_symptoms.discard("prognosis")
all_symptoms = sorted(list(all_symptoms))

def align(df):
    """Ensure all symptom columns exist, fill missing with 0"""
    for col in all_symptoms:
        if col not in df.columns:
            df[col] = 0
    return df[all_symptoms + ["prognosis"]]

# Align all datasets
df_base = align(df_base)
df_kaggle1 = align(df_kaggle1)
df_kaggle2 = align(df_kaggle2)

# Merge all
merged = pd.concat([df_base, df_kaggle1, df_kaggle2], ignore_index=True)

# Clean disease column
merged.rename(columns={"prognosis": "disease"}, inplace=True)
merged["disease"] = merged["disease"].str.strip().str.title()

# Drop duplicates if any
merged.drop_duplicates(inplace=True)

# Save final dataset
merged.to_csv("../data/ml_training_dataset_extended.csv", index=False)
print(f"✅ Combined dataset created with {len(merged)} rows and {len(all_symptoms)} symptoms.")
