# back-end/app/routes/i18n.py
from flask import Blueprint, request, jsonify
from app.i18n_kriol_panlex import en_to_kriol, kriol_to_english, pre_normalize_asr

bp = Blueprint("i18n", __name__, url_prefix="/api/i18n")


@bp.post("/translate")
def translate():
    data = request.get_json(force=True) or {}
    text = data.get("text", "")
    direction = (data.get("direction") or "en2kriol").lower()

    if direction == "kriol2en":
        if data.get("asr"):
            text = pre_normalize_asr(text)  # helpful if input came from speech
        out = kriol_to_english(text)
    else:
        out = en_to_kriol(text)

    return jsonify({"input": text, "direction": direction, "output": out})
