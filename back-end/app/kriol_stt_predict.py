import argparse, whisper
from app.utils import (
    load_kriol_lexicon,
    load_symptom_disease_map,
    extract_symptoms,
    score_diseases,
)


def transcribe(audio_path, model_name="base"):
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path)
    return result.get("text", "").strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", help="path to audio file (.wav/.mp3)")
    p.add_argument("--text", help="Kriol text input (bypass STT)")
    p.add_argument("--kriol_lexicon", default="../data/lexicon_kriol_to_symptom.csv")
    p.add_argument("--symptom_map", default="../data/symptom_to_disease.csv")
    p.add_argument("--whisper_model", default="base")
    p.add_argument("--topk", type=int, default=3)
    args = p.parse_args()

    # 1) เลือก input
    if args.text:
        kriol_text = args.text.strip()
    elif args.audio:
        kriol_text = transcribe(args.audio, args.whisper_model)
    else:
        print("⚠️ Please provide either --text '<kriol sentence>' or --audio <file>")
        return

    print(f"\n[Transcribed/Provided Kriol] {kriol_text}")

    # 2) โหลด CSV
    lex_df = load_kriol_lexicon(args.kriol_lexicon)
    sym_df = load_symptom_disease_map(args.symptom_map)

    # 3) ดึงอาการ
    symptoms = extract_symptoms(kriol_text, lex_df)
    print(f"[Extracted symptoms] {symptoms if symptoms else 'None'}")

    # 4) ทำนายโรค
    ranked = score_diseases(symptoms, sym_df)
    if ranked.empty:
        print("\n[Prediction] No clear disease risk detected.")
    else:
        print("\n[Prediction: Possible diseases & scores]")
        for _, r in ranked.head(args.topk).iterrows():
            print(f"- {r['disease']}: {r['score']:.2f}")


if __name__ == "__main__":
    main()
