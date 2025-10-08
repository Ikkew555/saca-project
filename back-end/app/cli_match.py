# app/cli_match.py
import os, tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf
import whisper
import sys
import re
import threading
from pathlib import Path
from app.utils import (
    load_kriol_lexicon,
    load_symptom_disease_map,
    extract_symptoms,
    score_diseases,
)
import pandas as pd
from pathlib import Path


def run_cli_match(user_input):
    # ตัวอย่างเรียก CLI logic
    # TODO: ใส่ logic ของไฟล์คุณแทนได้เลย
    if not user_input:
        return "No input received."
    result = f"[CLI-MATCH] Matched for '{user_input}'"
    return result


# ---- Build an initial prompt from your lexicon (Kriol + symptom vocab) ----
def build_initial_prompt_from_lexicon(lex_df, limit=60):
    """
    Turn top-N Kriol phrases into a short biasing prompt for Whisper.
    Keep it short (<= ~300 tokens) to avoid harming decoding.
    """
    terms = []
    seen = set()
    for _, row in lex_df.head(limit).iterrows():
        term = str(row.get("term_raw") or row.get("kriol_phrase") or "").strip()
        if term and term.lower() not in seen:
            seen.add(term.lower())
            terms.append(term)
    # add common English clinical words to bias toward medical sense
    extras = [
        "cough",
        "headache",
        "shortness of breath",
        "chest pain",
        "fever",
        "dizziness",
        "fatigue",
        "diarrhea",
        "vomiting",
        "sore throat",
        "wheeze",
        "asthma",
        "diabetes",
        "kidney disease",
    ]
    for w in extras:
        if w not in seen:
            terms.append(w)
    # Make a compact prompt
    prompt = "Medical triage vocabulary (Kriol & English): " + ", ".join(terms[:limit])
    return prompt


# ---- Post-fix common mishears before matching ----
MISHEAR_FIX = {
    # cough
    "kof": "cough",
    "cof": "cough",
    "cauf": "cough",
    "caugh": "cough",
    # headache
    "h8": "headache",
    "head ake": "headache",
    "hed ache": "headache",
    "head ak": "headache",
    "hedak": "headache",
    # shortness of breath
    "short of breath": "shortness of breath",
    "hard to breath": "hard to breathe",
    # chest pain
    "pain in chest": "chest pain",
    "tight chest": "chest pain",
}


def apply_mishear_fixes(text: str) -> str:
    t = " " + text.lower() + " "
    for wrong, right in MISHEAR_FIX.items():
        # word boundary-ish replace (simple)
        t = re.sub(rf"(?<!\w){re.escape(wrong)}(?!\w)", right, t)
    return t.strip()


# === Load data ===
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

LEX_PATH = DATA_DIR / "lexicon_kriol_to_symptom.csv"
MAP_PATH = DATA_DIR / "symptom_to_disease.csv"

lex_df = load_kriol_lexicon(str(LEX_PATH))
sym_df = load_symptom_disease_map(str(MAP_PATH))

# === Config ===
SR = 16000


def record_audio():
    """
    Press ENTER to start, then ENTER again to stop.
    Uses a background thread to wait for ENTER (reliable on macOS).
    """
    print("🎙️ Press ENTER to start speaking, then ENTER again to stop.")
    try:
        input("Press ENTER to start...")
    except KeyboardInterrupt:
        print("\n[INFO] Cancelled.")
        return np.zeros((0, 1), dtype=np.float32)

    stop_event = threading.Event()

    # Background thread — waits for ENTER to stop
    def wait_for_enter():
        try:
            input()  # wait for ENTER again
        except KeyboardInterrupt:
            pass
        stop_event.set()

    t = threading.Thread(target=wait_for_enter, daemon=True)
    t.start()

    chunks = []
    frames_per_chunk = int(SR * 0.5)  # ✅ 0.5s per chunk (ถูก)
    try:
        with sd.InputStream(samplerate=SR, channels=1, dtype="float32") as stream:
            print("🎙️ Recording... (press ENTER to stop)")
            while not stop_event.is_set():
                data, _ = stream.read(frames_per_chunk)
                chunks.append(data.copy())
    except Exception as e:
        print("[AUDIO ERROR]", repr(e))
        return np.zeros((0, 1), dtype=np.float32)

    if not chunks:
        return np.zeros((0, 1), dtype=np.float32)

    audio = np.concatenate(chunks, axis=0)
    return audio


def save_wav(audio, path):
    sf.write(path, audio, SR)


def transcribe_local(audio_path, lex_df=None):
    """
    Local Whisper transcription with vocabulary bias (initial prompt)
    and conservative decoding settings for better accuracy.
    """
    # pick model: env > default
    model_name = os.getenv("WHISPER_LOCAL_MODEL", "small.en")  # base/small/medium.en
    print(f"[INFO] Loading Whisper model: {model_name} (1st call may take a while)...")
    model = whisper.load_model(model_name)

    initial_prompt = None
    if lex_df is not None:
        initial_prompt = build_initial_prompt_from_lexicon(lex_df, limit=80)

    # decode options tuned for accuracy
    opts = dict(
        language="en",
        task="transcribe",
        temperature=[0.0, 0.2, 0.4],  # retry with slightly higher temps
        beam_size=5,
        best_of=5,
        condition_on_previous_text=False,
        compression_ratio_threshold=2.4,
        logprob_threshold=-1.0,
        no_speech_threshold=0.45,
    )
    if initial_prompt:
        opts["initial_prompt"] = initial_prompt

    result = model.transcribe(audio_path, **opts)
    text = (result.get("text") or "").strip()
    return text


def process_text(text: str, topk: int = 3):
    syms = extract_symptoms(text, lex_df)
    ranked = score_diseases(syms, sym_df).head(topk)
    print(f"\n[Transcript] {text}")
    print("[Symptoms]", syms)
    print("[Predictions]")
    for _, row in ranked.iterrows():
        print(f"- {row['disease']}: {row['score']:.2f}")


def main():
    mode = input("Choose input mode (voice/text): ").strip().lower()
    if mode == "text":
        text = input("Enter your text: ")
        text = apply_mishear_fixes(text)
        process_text(text)

    elif mode == "voice":
        audio = record_audio()
        if len(audio) == 0:
            print("No audio recorded.")
            return
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            save_wav(audio, tmp.name)
            # ✅ ส่ง lex_df เข้าไปเพื่อ bias + เกลาคำก่อนแมตช์
            transcript = transcribe_local(tmp.name, lex_df=lex_df)
        transcript = apply_mishear_fixes(transcript)
        process_text(transcript)

    else:
        print("Invalid mode. Choose 'voice' or 'text'.")


def run_cli_match(user_input: str, topk: int = 5):
    """
    Extract symptoms, match to diseases using CSV,
    and return structured results for React display.
    """
    try:
        text = apply_mishear_fixes(user_input)
        matched_symptoms = extract_symptoms(text, lex_df)

        if not matched_symptoms:
            return {
                "input": user_input,
                "symptoms": [],
                "predictions": [],
                "mapping": {},
                "message": "No known symptoms found in input.",
            }

        # Build symptom → disease mapping
        symptom_disease_map = {}
        for symptom in matched_symptoms:
            matched_rows = sym_df[sym_df["symptom"].str.lower() == symptom.lower()]
            symptom_disease_map[symptom] = matched_rows["disease"].unique().tolist()

        # Score diseases normally
        ranked = score_diseases(matched_symptoms, sym_df).head(topk)
        predictions = [
            {"disease": row["disease"], "score": round(float(row["score"]), 2)}
            for _, row in ranked.iterrows()
        ]

        return {
            "input": user_input,
            "symptoms": matched_symptoms,
            "predictions": predictions,
            "mapping": symptom_disease_map,
        }

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    main()
