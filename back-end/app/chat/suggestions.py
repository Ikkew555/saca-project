# back-end/app/chat/suggestions.py
from flask import Blueprint, request, jsonify
from .data import df_details

suggestion_bp = Blueprint("suggestion_bp", __name__)


@suggestion_bp.route("/api/suggestions", methods=["POST"])
def get_suggestions():
    data = request.get_json() or {}
    symptoms = [str(s).lower().strip() for s in data.get("symptoms", [])]
    lang = (data.get("lang") or "english").lower()

    results = []
    for s in symptoms:
        match = df_details[df_details["symptom"].str.lower() == s]
        if not match.empty:
            row = match.iloc[0]
            if lang == "kriol":
                results.append(
                    {
                        "symptom": row.get("symptom_kriol", ""),
                        "description": row.get("description_kriol", ""),
                        "common_causes": row.get("common_causes_kriol", ""),
                        "advice": row.get("advice_kriol", ""),
                    }
                )
            else:
                results.append(
                    {
                        "symptom": row.get("symptom", ""),
                        "description": row.get("description_en", ""),
                        "common_causes": row.get("common_causes_en", ""),
                        "advice": row.get("advice_en", ""),
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
    return jsonify({"suggestions": results})
