from flask import Blueprint, request, jsonify
import pandas as pd
import random
from joblib import load
import numpy as np
import re

api_chat = Blueprint("chat_api", __name__)
suggestion_bp = Blueprint("suggestion_bp", __name__)

# ───────────────────────────────
# Load data from CSV files
# ───────────────────────────────
df_symptom = pd.read_csv("./data/symptom_to_disease.csv")

df_symptom["symptom"] = (
    df_symptom["symptom"]
    .astype(str)
    .str.strip()
    .str.lower()
    .str.replace("_", " ")  # ✅ convert underscores to spaces
)

df_details = pd.read_csv("./data/symptom_details_with_kriol_full.csv")
df_followup = pd.read_csv(
    "./data/followup_questions.csv",
    encoding="utf-8",
    skip_blank_lines=True,
    on_bad_lines="warn",
)

# ✅ Normalize all symptom columns (fix missing follow-ups)
for df in [df_symptom, df_details, df_followup]:
    if "symptom" in df.columns:
        df["symptom"] = (
            df["symptom"]
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace("\u200b", "", regex=False)  # remove hidden spaces
        )

sessions = {}

# ───────────────────────────────
# Load ML model safely (added)
# ───────────────────────────────
try:
    model, features = load("./data/disease_model.pkl")  # โหลด ML มาใช้
    print(f"✅ ML model loaded successfully with {len(features)} features.")
except Exception as e:
    model, features = None, []
    print(f"⚠️ ML model not loaded: {e}")


# ───────────────────────────────
# Helper Functions
# ───────────────────────────────
def detect_language(text: str) -> str:
    """Detect whether the input is in Kriol or English."""
    kriol_keywords = ["bin", "la", "yu", "im", "sik", "plenti", "moa", "wan", "bai"]
    text_lower = text.lower()
    return (
        "kriol" if any(k in text_lower.split() for k in kriol_keywords) else "english"
    )


def extract_symptoms(text):
    """
    Extract possible symptoms mentioned in user message.
    Uses precise word-boundary matching (avoids over-matching 'pain' in all phrases).
    """
    text = text.lower().strip()
    found = []

    for s in df_symptom["symptom"].dropna().unique():
        s_clean = str(s).strip().lower()

        # 1️⃣ exact phrase match (e.g., "chest pain")
        if re.search(rf"\b{re.escape(s_clean)}\b", text):
            found.append(s_clean)
            continue

        # 2️⃣ relaxed matching for confirmations like "yes, I feel back pain"
        # (allow partial match only if the phrase contains more than one word)
        parts = s_clean.split()
        if len(parts) > 1:
            # e.g., check if all important words (>=2 letters) are in text
            key_words = [w for w in parts if len(w) > 2]
            if all(w in text for w in key_words):
                found.append(s_clean)

    # remove duplicates & avoid nested overlaps (e.g., 'back pain' vs 'lower back pain')
    found = sorted(found, key=len, reverse=True)
    cleaned = []
    for f in found:
        if not any(f in longer for longer in cleaned):
            cleaned.append(f)

    return cleaned


# ✅ Improved fuzzy-matching get_next_question()
def get_next_question(symptom, step, lang="english", asked=None, asked_global=None):
    """Retrieve next follow-up question deterministically (max 4)."""
    if not symptom or pd.isna(symptom):
        sub = df_followup[df_followup["symptom"] == "general"]
    else:
        sym_lower = str(symptom).strip().lower()
        sub = df_followup[df_followup["symptom"] == sym_lower]
        if sub.empty:
            sub = df_followup[df_followup["symptom"].apply(lambda x: sym_lower in str(x))]
        if sub.empty:
            sub = df_followup[df_followup["symptom"] == "general"]

    question_col = "question_kriol" if lang == "kriol" else "question_en"
    if question_col not in sub.columns:
        return None

    questions = sub.sort_values("order")[question_col].dropna().tolist()
    # กรองที่ถามไปแล้วในอาการนี้
    if asked:
        questions = [q for q in questions if q not in asked]

    # กรองแบบ global (ข้ามอาการ)
    if asked_global is not None:
        filtered = []
        for q in questions:
            key = normalize_qtext(q, symptom)
            if key not in asked_global:
                filtered.append(q)
        questions = filtered

    # เมื่อคำถามหมด ให้ fallback ไป general (แบบไม่ซ้ำ global)
    if not questions:
        sub = df_followup[df_followup["symptom"] == "general"]
        questions = sub.sort_values("order")[question_col].dropna().tolist()
        if asked:
            questions = [q for q in questions if q not in asked]
        if asked_global is not None:
            questions = [q for q in questions if normalize_qtext(q, symptom) not in asked_global]

    # จำกัดสูงสุด 4 ข้อ และดึงตาม step แบบกำหนดแน่นอน
    questions = questions[:4]
    return questions[step] if step < len(questions) else None


def enqueue_symptoms(s, new_syms):
    """Add detected symptoms into the user's active session."""
    for f in new_syms:
        if f not in s["symptoms"]:
            s["symptoms"].append(f)
        if f not in s["queue"] and f not in s["done"]:
            s["queue"].append(f)


def pick_next_symptom(s):
    """Move to the next symptom waiting in the queue."""
    if s["queue"]:
        s["current_symptom"] = s["queue"].pop(0)
        s["step"] = 0
        return s["current_symptom"]
    s["current_symptom"] = None
    s["step"] = 0
    return None


def format_question(q, symptom):
    """Insert symptom name dynamically into follow-up questions."""
    if not q:
        return f"How long have you had the {symptom}?"
    return q.replace("{symptom}", symptom)


def get_symptom_details(symptom_list):
    """Return bilingual symptom details (English + Kriol) for all symptoms."""
    results = []
    for s in symptom_list:
        row = df_details[df_details["symptom"].str.lower() == s.lower()]
        if not row.empty:
            r = row.iloc[0]
            item = {
                "symptom": s,
                "symptom_kriol": r.get("symptom_kriol", ""),
                "en": {
                    "description": r.get("description_en", ""),
                    "common_causes": r.get("common_causes_en", ""),
                    "advice": r.get("advice_en", ""),
                },
                "kriol": {
                    "description": r.get("description_kriol", ""),
                    "common_causes": r.get("common_causes_kriol", ""),
                    "advice": r.get("advice_kriol", ""),
                },
            }
        else:
            item = {
                "symptom": s,
                "symptom_kriol": "",
                "en": {
                    "description": "No details available.",
                    "common_causes": "N/A",
                    "advice": "N/A",
                },
                "kriol": {
                    "description": "Nating infomesen yet.",
                    "common_causes": "N/A",
                    "advice": "N/A",
                },
            }
        results.append(item)
    return results


# ───────────────────────────────
# ORIGINAL predict_disease (keep)
# ───────────────────────────────
def predict_disease(symptoms):
    """Predict likely diseases based on symptom weights (original rule-based)."""
    matches = df_symptom[df_symptom["symptom"].isin(symptoms)]
    if matches.empty:
        return {}
    agg = matches.groupby("disease")["weight"].sum().sort_values(ascending=False)
    return agg.head(3).to_dict()


# ───────────────────────────────
# ML-based Disease Prediction (new)
# ───────────────────────────────
def predict_disease_ml(symptoms):
    """Predict diseases using trained ML model."""
    if model is None or not features:
        print("⚠️ ML model not loaded, using rule-based fallback.")
        return predict_disease(symptoms)

    x_input = np.zeros(len(features))
    for s in symptoms:
        if s in features:
            x_input[features.index(s)] = 1

    x_df = pd.DataFrame([x_input], columns=features)
    pred_proba = model.predict_proba(x_df)[0]
    top_idx = np.argsort(pred_proba)[::-1][:3]
    return {model.classes_[i]: float(pred_proba[i]) for i in top_idx}


# ───────────────────────────────
# Chat API Route (no major change)
# ───────────────────────────────
@api_chat.route("/api/chat", methods=["POST"])
def chat():
    """Main conversational route — manages symptom detection and follow-up flow."""
    data = request.get_json()
    user_id = data.get("user", "default")
    text = (data.get("text") or "").lower().strip()
    if not text:
        return jsonify({"message": "Please describe what you feel."})

    lang = data.get("lang", detect_language(text))

    # Init / backfill session keys
    if user_id not in sessions:
        sessions[user_id] = {}
    s = sessions[user_id]
    s.setdefault("symptoms", [])
    s.setdefault("queue", [])
    s.setdefault("current_symptom", None)
    s.setdefault("step", 0)
    s.setdefault("asked_questions", {})
    s.setdefault("asked_global", set())   # ✅ สำคัญ
    s.setdefault("done", set())
    s.setdefault("last_question", None)

    # 0️⃣ Handle "yes" response to last question
    if s.get("last_question"):
        for known in df_symptom["symptom"].dropna().unique():
            if known.lower() in s["last_question"].lower():
                if any(w in text for w in ["yes", "yeah", "yep", "i do", "true", "correct"]):
                    enqueue_symptoms(s, [known])
                    s["current_symptom"] = known
                    s["step"] = 0
                    q = get_next_question(
                        known, 0, lang,
                        asked=s["asked_questions"].get(known, []),
                        asked_global=s["asked_global"]               # ✅ เพิ่ม
                    )
                    if q:
                        s["asked_questions"].setdefault(known, []).append(q)
                        s["asked_global"].add(normalize_qtext(q, known))  # ✅ เพิ่ม
                        q = format_question(q, known)
                        s["last_question"] = q
                        print(f"✅ User confirmed symptom: {known}")
                        return jsonify({"message": q, "lang": lang})

    # 1️⃣ Detect new symptom mention
    found = extract_symptoms(text)
    if found:
        enqueue_symptoms(s, found)
        s["current_symptom"] = found[-1]
        s["step"] = 0

        q = get_next_question(
            s["current_symptom"], s["step"], lang,
            asked=s["asked_questions"].get(s["current_symptom"], []),
            asked_global=s["asked_global"]                       # ✅ เพิ่ม
        )
        if q:
            s["asked_questions"].setdefault(s["current_symptom"], []).append(q)
            s["asked_global"].add(normalize_qtext(q, s["current_symptom"]))  # ✅ เพิ่ม
            q_fmt = format_question(q, s["current_symptom"])
        else:
            q_fmt = None
        s["last_question"] = q_fmt

        msg = (
            f"You mentioned {', '.join(found)}. {q_fmt or ''}".strip()
            if lang == "english"
            else f"Yu bin tokbaut {', '.join(found)}. {q_fmt or ''}".strip()
        )
        print(f"🩺 New symptom detected: {found}")
        return jsonify({"message": msg, "lang": lang})

    # 2️⃣ Continue next question for current symptom
    if s["current_symptom"]:
        next_q = get_next_question(
            s["current_symptom"], s["step"] + 1, lang,
            asked=s["asked_questions"].get(s["current_symptom"], []),
            asked_global=s["asked_global"]                       # ✅ มี
        )
        if next_q:
            s["step"] += 1
            s["asked_questions"].setdefault(s["current_symptom"], []).append(next_q)
            s["asked_global"].add(normalize_qtext(next_q, s["current_symptom"]))
            next_q_fmt = format_question(next_q, s["current_symptom"])
            s["last_question"] = next_q_fmt
            print(f"🔁 Follow-up question for {s['current_symptom']}: {next_q_fmt}")
            return jsonify({"message": next_q_fmt, "lang": lang})

        s["done"].add(s["current_symptom"])
        s["current_symptom"] = None
        s["step"] = 0

    # 3️⃣ Move to next symptom in queue
    if pick_next_symptom(s):
        q0 = get_next_question(
            s["current_symptom"], 0, lang,
            asked=s["asked_questions"].get(s["current_symptom"], []),
            asked_global=s["asked_global"]                       # ✅ มี
        )
        if q0:
            s["asked_questions"].setdefault(s["current_symptom"], []).append(q0)
            s["asked_global"].add(normalize_qtext(q0, s["current_symptom"]))
        q0_fmt = format_question(q0, s["current_symptom"]) if q0 else None
        s["last_question"] = q0_fmt
        intro = (
            f"Okay, let's talk about {s['current_symptom']}. {q0_fmt or ''}".strip()
            if lang == "english"
            else f"Orait, yumi tokbaut {s['current_symptom']}. {q0_fmt or ''}".strip()
        )
        print(f"➡️ Switching to next symptom: {s['current_symptom']}")
        return jsonify({"message": intro, "lang": lang})

    # 4️⃣ Ask if user has another symptom
    if any(k in text for k in ["also", "another", "else", "too", "moa", "nara wan"]):
        s["current_symptom"] = None
        s["last_question"] = None
        msg = "Tell me the other symptom you feel." if lang == "english" else "Yu bin feelim nara sik?"
        print("➕ Asking for additional symptoms.")
        return jsonify({"message": msg, "lang": lang})

    print(f"🧩 Current session symptoms: {s['symptoms']}")

    # 5️⃣ Final predictions
    result = predict_disease_ml(s["symptoms"])
    top = list(result.keys())[:2]
    details = get_symptom_details(s["symptoms"])
    msg = (
        f"Based on your symptoms ({', '.join(s['symptoms'])}), it might be {', '.join(top)}."
        if lang == "english"
        else f"From yu sik ({', '.join(s['symptoms'])}), bai im laik {', '.join(top)}."
    )
    response = {
        "message": msg,
        "symptoms": s["symptoms"],
        "symptom_details": details,
        "predictions": [{"disease": d, "score": round(v, 2)} for d, v in result.items()],
        "lang": lang,
        "done": True,
    }

    print("\n🩺 FINAL RESPONSE (to frontend):")
    print(response)
    print("──────────────────────────────")

    # ✅ Reset with all keys (รวม asked_global)
    sessions[user_id] = {
        "symptoms": [],
        "queue": [],
        "done": set(),
        "step": 0,
        "current_symptom": None,
        "last_question": None,
        "asked_questions": {},
        "asked_global": set(),     # ✅ ใส่กลับ
    }
    return jsonify(response)



# =============================================
# ✅ Suggestion API Route
# =============================================
from flask import Blueprint, request, jsonify
import pandas as pd
from datetime import datetime

suggestion_bp = Blueprint("suggestion_bp", __name__)


@suggestion_bp.route("/api/suggestions", methods=["POST"])
def get_suggestions():
    data = request.get_json()
    symptoms = [s.lower().strip() for s in data.get("symptoms", [])]
    lang = data.get("lang", "english").lower()

    print(f"🧭 [LOG] Suggestion API called — Language: {lang}")
    print(f"🩺 Symptoms requested: {symptoms}")

    results = []
    for s in symptoms:
        # ✅ use df_details instead of symptom_df
        match = df_details[df_details["symptom"].str.lower() == s]
        if not match.empty:
            row = match.iloc[0]

            if lang == "kriol":
                results.append(
                    {
                        "symptom": row["symptom_kriol"],
                        "description": row["description_kriol"],
                        "common_causes": row["common_causes_kriol"],
                        "advice": row["advice_kriol"],
                    }
                )
            else:
                results.append(
                    {
                        "symptom": row["symptom"],
                        "description": row["description_en"],
                        "common_causes": row["common_causes_en"],
                        "advice": row["advice_en"],
                    }
                )
        else:
            results.append(
                {
                    "symptom": s,
                    "description": "No description available.",
                    "common_causes": "Unknown.",
                    "advice": "No advice found.",
                }
            )

    print(f"✅ Found {len(results)} suggestion(s)")
    return jsonify({"suggestions": results})


def normalize_qtext(q: str, symptom: str) -> str:
    if not q:
        return ""
    # แทนชื่ออาการด้วย placeholder เพื่อให้คำถามที่เหมือนกัน across symptoms นับเป็นอันเดียว
    q = q.replace(symptom or "", "{symptom}")
    q = re.sub(r"\s+", " ", q.strip().lower())
    return q