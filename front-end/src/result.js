import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { translations } from "./translations";
import "./result.css";

function ResultPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    symptoms = [],
    predictions = [],
    symptom_details = [],
  } = location.state || {};

  // 🌐 Language setup
  const [language, setLanguage] = useState(
    () => localStorage.getItem("lang") || "en"
  );
  const langText = translations[language] || translations.en;
  const [showPopup, setShowPopup] = useState(true);
  const handleSelect = (lang) => {
    setLanguage(lang);
    localStorage.setItem("lang", lang);
    sessionStorage.setItem("seenLangPopup", "true");
    setShowPopup(false);
  };

  useEffect(() => {
    console.log("🩺 Full backend response ↓");
    console.dir({ symptoms, predictions, symptom_details }, { depth: null });
    const langLabel =
      language === "en"
        ? "🇬🇧 English"
        : language === "kriol"
        ? "🇦🇺 Kriol"
        : language;
    console.log(
      `%c🌐 Current language: ${langLabel}`,
      "color: #4CAF50; font-weight: bold; font-size: 14px;"
    );
  }, [symptoms, predictions, symptom_details, language]);

  return (
    <div className="result-container">
      {/* HEADER */}
      <div className="suggestion-header">
        <h1>{langText.summaryTitle}</h1>
        <button onClick={() => setShowPopup(true)} className="lang-btn">
          {language === "en"
            ? "🇬🇧 " + langText.english
            : "🇦🇺 " + langText.kriol}
        </button>
      </div>

      {/* 🌐 LANGUAGE POPUP */}
      {showPopup && (
        <div className="popup-overlay" onClick={() => setShowPopup(false)}>
          <div className="popup-content" onClick={(e) => e.stopPropagation()}>
            <h3 className="popup-title">{langText.chooseLanguage}</h3>
            <div className="popup-options">
              <button
                className={`popup-option ${
                  language === "en" ? "selected" : ""
                }`}
                onClick={() => handleSelect("en")}
              >
                🇬🇧 {translations.en.english}
              </button>
              <button
                className={`popup-option ${
                  language === "kriol" ? "selected" : ""
                }`}
                onClick={() => handleSelect("kriol")}
              >
                🇦🇺 {translations.kriol.kriol}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 🩺 Header */}
      {/* 🌿 Dynamic, more natural summary paragraph */}
      <p className="summary-text">
        {symptom_details.length > 0 ? (
          <>
            {language === "kriol" ? (
              <>
                Wi bin faind yu bin tokbaut{" "}
                <b>
                  {symptom_details
                    .slice(0, 3)
                    .map((item) => item.symptom_kriol || item.symptom)
                    .join(", ")}
                </b>
                . Diswan luk{" "}
                {predictions.length > 0
                  ? predictions[0].score > 0.7
                    ? "laek strong sik we yu shud go klinik or si doktor kwiktaem."
                    : predictions[0].score > 0.4
                    ? "laek midl sik. Yu ken kip rest, dring plenti watta, an luk afta yu bodi."
                    : "laek laet sik nomo. Yu ken rest gud, dring watta, an kip yu bodi warm."
                  : "main nomo sik, yu luk orait nomo."}{" "}
                Imin gud yu bin chus blong yus dis app blong luk afta yu hilti.
                SACA save help yu andaestan yu sik mo isi, an gib yu tok blong
                wat yu ken du nau an we yu ken go if yu sik no beta.
              </>
            ) : (
              <>
                From what you’ve reported —{" "}
                <b>
                  {symptom_details
                    .slice(0, 3)
                    .map((item) => item.symptom)
                    .join(", ")}
                </b>{" "}
                — our system has identified that you may be showing signs of a{" "}
                {predictions.length > 0
                  ? predictions[0].score > 0.7
                    ? "serious condition. It’s strongly recommended that you visit a local clinic or consult a healthcare professional as soon as possible."
                    : predictions[0].score > 0.4
                    ? "moderate condition. You should rest, drink plenty of water, and monitor your symptoms closely for any changes."
                    : "mild condition. You may continue resting, maintaining hydration, and ensuring proper nutrition to recover faster."
                  : "stable condition with no major health risks at the moment."}{" "}
                It’s great that you used this tool to check your health — SACA
                helps make medical understanding clearer and connects you to
                safer care if your symptoms change or worsen.
              </>
            )}
          </>
        ) : (
          langText.summaryText
        )}
      </p>

      {/* 🧠 Detected Symptoms */}
      <div className="result-section">
        <h3>{langText.detectedSymptoms}</h3>
        {symptom_details.length > 0 ? (
          symptom_details.map((item, i) => {
            const content = language === "kriol" ? item.kriol : item.en;
            return (
              <div key={i} className="symptom-card">
                <h4>
                  {language === "kriol" ? item.symptom_kriol : item.symptom}
                </h4>
                <p>
                  <b>{langText.description}:</b> {content.description || "—"}
                </p>
                <p>
                  <b>{langText.causes}:</b> {content.common_causes || "—"}
                </p>
                {/* <p>
                  <b>{langText.advice}:</b> {content.advice || "—"}
                </p> */}
              </div>
            );
          })
        ) : (
          <p>
            {language === "kriol"
              ? "Nating sik faind yet."
              : "No symptoms detected."}
          </p>
        )}
      </div>

      {/* 💊 Possible Conditions */}
      <div className="result-section">
        <h3>{langText.possibleConditions}</h3>
        {predictions.length > 0 ? (
          predictions.map((p, i) => {
            const confidence = Math.round(p.score * 100);
            const level =
              confidence < 40 ? "low" : confidence < 70 ? "medium" : "high";

            return (
              <div key={i} className="prediction-card">
                <p>
                  <b>{p.disease}</b> — {langText.confidence}: {confidence}%
                </p>
                <div className="confidence-bar">
                  <div
                    className={`confidence-fill ${level}`}
                    style={{ width: `${confidence}%` }}
                  ></div>
                </div>
              </div>
            );
          })
        ) : (
          <p>
            {language === "kriol"
              ? "No risalt yet."
              : "No predictions available."}
          </p>
        )}
      </div>

      {/* 🔙 Buttons */}
      <div className="result-button-section">
        <button onClick={() => navigate("/")} className="btn-back">
          {langText.back}
        </button>
        <button
          onClick={() =>
            navigate("/suggestions", {
              state: { predictions, symptoms },
            })
          }
          className="btn-back"
        >
          {langText.suggestion}
        </button>
      </div>
    </div>
  );
}

export default ResultPage;
