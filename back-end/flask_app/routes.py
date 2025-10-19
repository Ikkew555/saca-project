from flask import Blueprint, request, jsonify, current_app
from app.i18n_kriol_panlex import en_to_kriol, kriol_to_english, pre_normalize_asr
from app.cli_match import run_cli_match
from app.kriol_stt_predict import transcribe
from app.utils import preprocess_text, MISHEAR_MAP
from werkzeug.utils import secure_filename
from app.utils import to_wav_16k_mono
import os

# Use the new chat endpoint implementation
from app.chat.routes import chat as chat_handler

# Severity helper
from app.severity_infer import predict_severity_for_match

routes_blueprint = Blueprint("routes_blueprint", __name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def make_human_message(result):
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
    diseases = [p.get("disease", "") for p in predictions if p.get("disease")]
    disease_list = ", ".join(diseases[:-1]) + (
        f", and {diseases[-1]}" if len(diseases) > 1 else diseases[0]
    )
    if len(symptoms) == 1:
        symptom_text = symptoms[0]
    elif len(symptoms) == 2:
        symptom_text = f"{symptoms[0]} and {symptoms[1]}"
    else:
        symptom_text = ", ".join(symptoms[:-1]) + f", and {symptoms[-1]}"
    return (
        f"It sounds like you might be experiencing {symptom_text}. "
        f"These symptoms could be related to <b>{disease_list}</b>. "
        "If you have more symptoms, please mention them to help me refine the match."
    )


# 🧠 /api/match — text input
@routes_blueprint.route("/api/match", methods=["POST"])
def match_symptom():
    try:
        data = request.get_json() or {}
        user_input_raw = data.get("text") or ""
        user_input = preprocess_text(user_input_raw, MISHEAR_MAP).strip()
        if not user_input:
            return jsonify({"error": "Empty text input"}), 400

        print(f"[INFO] Received text input: {user_input}")

        # Your RF symptom matcher
        result = run_cli_match(user_input)

        result["input_raw"] = user_input_raw
        result["input"] = user_input

        # 🔒 Only compute severity when explicitly allowed
        if bool(data.get("allow_severity")):
            try:
                severity = predict_severity_for_match(result, data)
                result["severity"] = severity
            except Exception as e:
                current_app.logger.exception("severity prediction failed: %s", e)

        result["message"] = make_human_message(result)
        print(f"[INFO] Response prepared for input: {user_input}")
        return jsonify(result)

    except Exception as e:
        print(f"[ERROR /api/match] {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# 🎤 /api/voice — voice input (forwards to /api/chat)
@routes_blueprint.route("/api/voice", methods=["POST"])
def handle_voice():
    try:
        file = request.files.get("file")
        user_id = request.form.get("user", "frontend-user")
        lang = request.form.get("lang", "english")

        if not file:
            return jsonify({"error": "No voice file received"}), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        try:
            wav_path = to_wav_16k_mono(file_path)
        except Exception:
            wav_path = file_path

        text_from_audio_raw = transcribe(wav_path)
        text_clean = preprocess_text(text_from_audio_raw, MISHEAR_MAP)

        print(f"[🎙️ Raw transcription]: {text_from_audio_raw}")
        print(f"[🧹 Cleaned text]: {text_clean}")

        from flask import current_app

        with current_app.test_request_context(
            "/api/chat",
            method="POST",
            json={"user": user_id, "text": text_clean, "lang": lang},
        ):
            response = chat_handler()
            chat_data = response.get_json()

        chat_data["transcribed_text"] = text_from_audio_raw
        chat_data["processed_text"] = text_clean
        chat_data["input_type"] = "voice"

        print("✅ Voice processed and sent to /api/chat successfully.")
        return jsonify(chat_data)

    except Exception as e:
        print(f"[❌ ERROR /api/voice] {e}")
        return jsonify({"error": f"Voice processing failed: {str(e)}"}), 500


# 🩺 Health check
@routes_blueprint.route("/", methods=["GET"])
def root():
    return jsonify({"ok": True, "service": "SACA backend running ✅"})


# 🌐 i18n helper (EN↔Kriol)
@routes_blueprint.route("/api/i18n/translate", methods=["POST"])
def i18n_translate():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    direction = (data.get("direction") or "en2kriol").lower()
    use_asr_norm = bool(data.get("asr"))

    if direction == "kriol2en":
        if use_asr_norm:
            text = pre_normalize_asr(text)
        out = kriol_to_english(text)
    else:
        out = en_to_kriol(text)

    return jsonify({"input": text, "direction": direction, "output": out})
