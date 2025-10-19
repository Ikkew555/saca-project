# back-end/app/chat/data.py
import os
import pandas as pd

DATA_DIR = os.path.abspath("./data")

df_symptom = pd.read_csv(os.path.join(DATA_DIR, "symptom_to_disease.csv"))
df_details = pd.read_csv(os.path.join(DATA_DIR, "symptom_details_with_kriol_full.csv"))
df_followup = pd.read_csv(
    os.path.join(DATA_DIR, "followup_questions.csv"),
    encoding="utf-8",
    skip_blank_lines=True,
    on_bad_lines="warn",
)

# Normalize symptom columns once
for df in (df_symptom, df_details, df_followup):
    if "symptom" in df.columns:
        df["symptom"] = (
            df["symptom"]
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace("_", " ")
            .str.replace("\u200b", "", regex=False)
        )

# Convenience:
SYMPTOM_COLUMN = "symptom"
