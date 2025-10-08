from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
from .utils import (
    load_kriol_lexicon,
    load_symptom_disease_map,
    extract_symptoms,
    score_diseases,
)

app = FastAPI(title="Kriol Risk Matcher")

# === ใช้ absolute path จากตำแหน่งไฟล์นี้ ===
BASE_DIR = Path(__file__).resolve().parent.parent  # program/
DATA_DIR = BASE_DIR / "data"
LEX_PATH = DATA_DIR / "lexicon_kriol_to_symptom.csv"
MAP_PATH = DATA_DIR / "symptom_to_disease.csv"

# โหลด CSV ตอนสตาร์ท
lex_df = load_kriol_lexicon(str(LEX_PATH))
sym_df = load_symptom_disease_map(str(MAP_PATH))


class In(BaseModel):
    text: str
    topk: int = 3


@app.post("/match")
def match(body: In):
    syms = extract_symptoms(body.text, lex_df)
    ranked = score_diseases(syms, sym_df).head(body.topk)
    return {
        "transcript": body.text,
        "symptoms": syms,
        "predictions": ranked.to_dict(orient="records"),
    }


@app.get("/")
def root():
    return {"ok": True}


def run_api_match(user_input):
    # ตัวอย่างเรียก model จริงของคุณ
    # TODO: แทนด้วย logic เดิมที่ Kew เขียนไว้
    if not user_input:
        return "No input received."
    result = f"[API-MATCH] Predicted for '{user_input}'"
    return result
