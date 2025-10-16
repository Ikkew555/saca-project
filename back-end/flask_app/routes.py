from flask import Blueprint, request, jsonify
from app.cli_match import run_cli_match  # main logic for text
from app.kriol_stt_predict import transcribe  # voice-to-text
from app.utils import preprocess_text, MISHEAR_MAP
from werkzeug.utils import secure_filename
from app.utils import to_wav_16k_mono
import os

# ---------------------------------------------------------------------
# Blueprint setup
# ---------------------------------------------------------------------
routes_blueprint = Blueprint("routes_blueprint", __name__)

# Create upload folder if missing
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------------------------------------------------
# Helper — build friendly response text
# ---------------------------------------------------------------------
def make_human_message(result):
    """
    Generates a conversational response mentioning multiple symptoms
    and possible related diseases.
    """
    symptoms = result.get("symptoms", [])
    predictions = result.get("predictions", [])

    if not symptoms:
        return (
            "Hmm, I couldn’t detect any clear symptoms yet. "
            "Could you describe how you feel again, maybe with more details?"
        )

    if not predictions:
        return (
            f"I found some symptoms like {', '.join(symptoms)}, "
            "but couldn’t confidently match them to a condition yet."
        )

    # Format disease list nicely
    diseases = [p.get("disease", "") for p in predictions if p.get("disease")]
    disease_list = ", ".join(diseases[:-1]) + (
        f", and {diseases[-1]}" if len(diseases) > 1 else diseases[0]
    )

    # Handle multiple symptoms in natural phrasing
    if len(symptoms) == 1:
        symptom_text = symptoms[0]
    elif len(symptoms) == 2:
        symptom_text = f"{symptoms[0]} and {symptoms[1]}"
    else:
        symptom_text = ", ".join(symptoms[:-1]) + f", and {symptoms[-1]}"

    # Compose full message
    return (
        f"It sounds like you might be experiencing {symptom_text}. "
        f"These symptoms could be related to <b>{disease_list}</b>. "
        "If you have more symptoms, please mention them to help me refine the match."
    )


# ---------------------------------------------------------------------
# 🧠 /api/match — text input
# ---------------------------------------------------------------------
@routes_blueprint.route("/api/match", methods=["POST"])
def match_symptom():
    """
    Receive text input from frontend, process via CLI logic,
    and return JSON results with friendly response.
    """
    try:
        data = request.get_json()
        user_input = (data.get("text") or "").strip()
        user_input = preprocess_text(user_input_raw, MISHEAR_MAP)

        if not user_input:
            return jsonify({"error": "Empty text input"}), 400

        print(f"[INFO] Received text input: {user_input}")

        # Run CLI matcher logic
        result = run_cli_match(user_input)
        result["input_raw"] = user_input_raw
        result["input"] = user_input
        # Add human-style message
        result["message"] = make_human_message(result)
        result["input"] = user_input

        print(f"[INFO] Response prepared for input: {user_input}")
        return jsonify(result)

    except Exception as e:
        print(f"[ERROR /api/match] {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# ---------------------------------------------------------------------
# 🎤 /api/voice — voice input
# ---------------------------------------------------------------------
@routes_blueprint.route("/api/voice", methods=["POST"])
def handle_voice():
    """
    Receive voice file from React, convert to text, run matcher,
    and return results with human-readable response.
    """
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No voice file received"}), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        try:
                wav_path = to_wav_16k_mono(file_path)   # ✅ ถ้ามีใน utils.py
                stt_input_path = wav_path
        except Exception:
                stt_input_path = file_path  # ถ้า ffmpeg ไม่มี ให้ใช้ไฟล์เดิมต่อไปก่อน

        text_from_audio_raw = transcribe(stt_input_path)
        print(f"[INFO] Transcribed text (raw): {text_from_audio_raw}")

        # Convert voice → text
        text_from_audio = preprocess_text(text_from_audio_raw, MISHEAR_MAP)
        print(f"[INFO] Transcribed text (pre): {text_from_audio}")

        # Run symptom-disease matching
        result = run_cli_match(text_from_audio)
        result["input_raw"] = text_from_audio_raw
        result["input"] = text_from_audio
        result["message"] = make_human_message(result)

        print("[INFO] Voice analysis complete.")
        return jsonify(result)

    except Exception as e:
        print(f"[ERROR /api/voice] {e}")
        return jsonify({"error": f"Voice processing failed: {str(e)}"}), 500


# ---------------------------------------------------------------------
# 🩺 Health check route (optional)
# ---------------------------------------------------------------------
@routes_blueprint.route("/", methods=["GET"])
def root():
    return jsonify({"ok": True, "service": "SACA backend running ✅"})
