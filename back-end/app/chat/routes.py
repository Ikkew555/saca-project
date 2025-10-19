# back-end/app/chat/routes.py
from __future__ import annotations

from flask import Blueprint, request, jsonify
from typing import Dict, List, Optional

# --- Local modules (import modules, not names, to avoid F823 shadowing) ---
from . import followup as fu  # get_next_question / normalize_qtext / format_question
from . import symptom_extraction as sx  # extract_symptoms
from . import screening as scr  # screening helpers (buddy questions)
from . import triage_slots as ts  # required_done / ask_next / parse_answer / PROMPTS
from . import predict as pdx  # disease prediction (ML or rule-based)

# Optional: symptom details (if present)
try:
    from .data import (
        df_details,
    )  # expected columns: symptom, symptom_kriol, description_en/_kriol, etc.
except Exception:  # pragma: no cover
    df_details = None

# Severity (LightGBM or fallback is implemented inside app/severity_infer.py)
from app.severity_infer import predict_severity

chat_bp = Blueprint("chat_bp", __name__)

# In-memory session store (simple; replace with Redis/db if needed)
_SESSIONS: Dict[str, Dict] = {}

YES_WORDS = {"yes", "y", "yeah", "yep", "true", "correct", "i do", "i have"}
NO_WORDS = {"no", "n", "nope", "nah", "false"}


def _get_session(user_id: str) -> Dict:
    s = _SESSIONS.setdefault(user_id, {})
    s.setdefault("symptoms", [])
    s.setdefault("queue", [])
    s.setdefault("current_symptom", None)
    s.setdefault("step", 0)
    s.setdefault("asked_questions", {})  # {symptom: [q1, q2, ...]}
    s.setdefault(
        "asked_global", set()
    )  # set of normalized questions (to avoid repeats)
    s.setdefault("asked_screen_for", set())
    s.setdefault("last_question", None)
    s.setdefault("last_question_kind", None)  # "screen" | "followup" | "slot" | None
    s.setdefault("last_screening_cands", [])  # remember options we just screened
    s.setdefault("slots", {})  # global triage slots
    s.setdefault("pending_slot", None)  # which slot we're currently waiting for
    return s


def _enqueue_symptoms(s: Dict, new_syms: List[str]) -> None:
    for f in new_syms:
        if f not in s["symptoms"]:
            s["symptoms"].append(f)
        if f not in s["queue"] and f not in s.get("done", set()):
            s["queue"].append(f)


def _pick_next_symptom(s: Dict) -> Optional[str]:
    if s["queue"]:
        s["current_symptom"] = s["queue"].pop(0)
        s["step"] = 0
        return s["current_symptom"]
    s["current_symptom"] = None
    s["step"] = 0
    return None


def _get_symptom_details(symptom_list: List[str]) -> List[Dict]:
    out = []
    for sym in symptom_list:
        if df_details is not None:
            try:
                row = df_details[df_details["symptom"].str.lower() == sym.lower()]
                if not row.empty:
                    r = row.iloc[0]
                    out.append(
                        {
                            "symptom": sym,
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
                    )
                    continue
            except Exception:
                pass
        # fallback
        out.append(
            {
                "symptom": sym,
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
        )
    return out


def _detect_language(text: str) -> str:
    kriol_keywords = {"bin", "la", "yu", "im", "sik", "plenti", "moa", "wan", "bai"}
    words = set((text or "").lower().split())
    return "kriol" if words & kriol_keywords else "english"


@chat_bp.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    user_id = str(data.get("user") or "default")
    text_raw = data.get("text") or ""
    text = text_raw.strip()
    lang = (data.get("lang") or _detect_language(text)).lower()
    if lang not in ("english", "kriol"):
        lang = "english"

    s = _get_session(user_id)

    # 0) If we are collecting a global slot, parse & store
    if s.get("pending_slot"):
        key = s["pending_slot"]
        val = ts.parse_answer(key, text)
        s["slots"][key] = val
        s["pending_slot"] = None
        s["last_question"] = None
        s["last_question_kind"] = None
        # Fall through to continue flow

    # 1) Handle "yes" to a recent screening question (add suggested buddies)
    if s.get("last_question_kind") == "screen":
        txt_low = text.lower()
        if any(w in txt_low for w in YES_WORDS):
            cands = s.get("last_screening_cands", [])
            if cands:
                _enqueue_symptoms(s, cands)
                s["last_screening_cands"] = []
                # Move immediately to the last candidate to ask follow-ups
                s["current_symptom"] = cands[-1]
                s["step"] = 0

    # 2) Extract any newly mentioned symptoms from free text
    try:
        found = sx.extract_symptoms(text)
    except Exception:
        # if the module isn't present or errors, don't crash the flow
        found = []
    if found:
        _enqueue_symptoms(s, found)
        s["current_symptom"] = found[-1]  # focus on the latest mentioned
        s["step"] = 0

    # 3) If we have an active symptom, try screening first, then follow-up
    if s["current_symptom"]:
        # 3a) Screening (buddy) question once per symptom
        if s["current_symptom"] not in s["asked_screen_for"]:
            try:
                # retrieve candidates so we can add if user says "yes"
                cands = scr.get_screening_candidates(s["current_symptom"], s, topk=2)
                if cands:
                    # Build a readable list (language-aware)
                    if lang == "kriol":
                        # Simple Kriol formatting
                        lst = ", ".join(cands[:-1]) + (
                            " o " + cands[-1] if len(cands) > 1 else cands[0]
                        )
                        qtext = f"Yu gat {lst} tu?"
                    else:
                        # English
                        if len(cands) == 1:
                            lst = cands[0]
                        elif len(cands) == 2:
                            lst = f"{cands[0]} or {cands[1]}"
                        else:
                            lst = ", ".join(cands[:-1]) + f", or {cands[-1]}"
                        qtext = f"Do you also have {lst}?"
                    s["asked_screen_for"].add(s["current_symptom"])
                    s["last_question"] = qtext
                    s["last_question_kind"] = "screen"
                    s["last_screening_cands"] = cands
                    return jsonify({"message": qtext, "lang": lang})
            except Exception:
                # If screening module isn't available, skip
                pass

        # 3b) Follow-up questions for the current symptom
        q, done_flag = fu.get_next_question(
            s["current_symptom"],
            s["step"],
            lang,
            asked=s["asked_questions"].get(s["current_symptom"], []),
            asked_global=s["asked_global"],
        )
        if q:
            s["asked_questions"].setdefault(s["current_symptom"], []).append(q)
            s["asked_global"].add(fu.normalize_qtext(q, s["current_symptom"]))
            q_fmt = fu.format_question(q, s["current_symptom"])
            s["last_question"] = q_fmt
            s["last_question_kind"] = "followup"
            return jsonify({"message": q_fmt, "lang": lang})

        # No more follow-ups for this symptom; mark as done and move on
        s.setdefault("done", set()).add(s["current_symptom"])
        s["current_symptom"] = None
        s["step"] = 0

    # 4) If there are more symptoms in the queue, switch to next and ask its first follow-up
    if _pick_next_symptom(s):
        q0, _ = fu.get_next_question(
            s["current_symptom"],
            0,
            lang,
            asked=s["asked_questions"].get(s["current_symptom"], []),
            asked_global=s["asked_global"],
        )
        if q0:
            s["asked_questions"].setdefault(s["current_symptom"], []).append(q0)
            s["asked_global"].add(fu.normalize_qtext(q0, s["current_symptom"]))
            q0_fmt = fu.format_question(q0, s["current_symptom"])
        else:
            # graceful fallback if no follow-ups defined
            if lang == "kriol":
                q0_fmt = f"Orait, yumi tokbaut {s['current_symptom']}. Yu save talem mi moa long hao yu feelim?"
            else:
                q0_fmt = f"Okay, let's talk about {s['current_symptom']}. Can you tell me more about how it feels?"

        s["last_question"] = q0_fmt
        s["last_question_kind"] = "followup"
        return jsonify({"message": q0_fmt, "lang": lang})

    # 5) Ask global triage slots until the required set is complete
    if not ts.required_done(s["slots"]):
        prompt, key = ts.ask_next(s["slots"], lang)
        if prompt and key:
            s["pending_slot"] = key
            s["last_question"] = prompt
            s["last_question_kind"] = "slot"
            return jsonify({"message": prompt, "lang": lang})

    # 6) Finalize: predict diseases + severity, and return result
    try:
        # Prefer ML if available in predict.py; otherwise fallback
        _predict = getattr(pdx, "predict_disease_ml", None) or getattr(
            pdx, "predict_disease", None
        )
        results = _predict(s["symptoms"]) if _predict else {}
    except Exception:
        results = {}

    # turn predictions into list of dicts
    preds_list = []
    if isinstance(results, dict):
        # assume {disease: score}
        items = sorted(results.items(), key=lambda kv: kv[1], reverse=True)
        preds_list = [{"disease": k, "score": float(v)} for k, v in items]
    elif isinstance(results, list):
        # already list
        preds_list = results

    details = _get_symptom_details(s["symptoms"])
    severity = predict_severity(s["symptoms"], s.get("slots", {}))

    if lang == "kriol":
        if s["symptoms"]:
            msg = f"From yu sik ({', '.join(s['symptoms'])}), bai im laik {', '.join([p['disease'] for p in preds_list[:2]])}."
        else:
            msg = "Mi no save faindim eni sik yet."
    else:
        if s["symptoms"]:
            top2 = ", ".join([p["disease"] for p in preds_list[:2]])
            msg = f"Based on your symptoms ({', '.join(s['symptoms'])}), it might be {top2}."
        else:
            msg = "I couldn't detect clear symptoms yet."

    response = {
        "message": msg,
        "symptoms": s["symptoms"],
        "symptom_details": details,
        "predictions": preds_list,
        "lang": lang,
        "done": True,
        "triage_status": "ready",
        "severity": severity,
    }

    # Reset session for next conversation
    _SESSIONS[user_id] = {
        "symptoms": [],
        "queue": [],
        "done": set(),
        "step": 0,
        "current_symptom": None,
        "last_question": None,
        "last_question_kind": None,
        "asked_questions": {},
        "asked_global": set(),
        "asked_screen_for": set(),
        "last_screening_cands": [],
        "slots": {},
        "pending_slot": None,
    }

    return jsonify(response)
