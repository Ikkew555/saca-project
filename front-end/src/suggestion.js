import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./suggestion.css";
import { translations } from "./translations";

export default function SuggestionPage() {
  const location = useLocation();
  const navigate = useNavigate();

  // ✅ Use the same key names as in translations.js
  const [lang, setLang] = useState(() => localStorage.getItem("lang") || "en");
  const [showLangPopup, setShowLangPopup] = useState(true);
  const [suggestions, setSuggestions] = useState([]);

  const { predictions = [], symptoms = [] } = location.state || {};

  // ✅ Safe fallback for missing translations
  const t = translations?.[lang] || translations.en;

  // 🧠 Fetch suggestions when symptoms or lang change
  useEffect(() => {
    if (symptoms.length > 0) {
      fetch("/api/suggestions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symptoms, lang }),
      })
        .then((res) => res.json())
        .then((data) => setSuggestions(data.suggestions || []))
        .catch(() => setSuggestions([]));
    }
  }, [symptoms, lang]);

  // 🌐 Change language
  const handleLangSelect = (selectedLang) => {
    setLang(selectedLang);
    localStorage.setItem("lang", selectedLang);
    setShowLangPopup(false);
  };

  return (
    <div className="suggestion-page">
      <div className="suggestion-container">
        {/* HEADER */}
        <div className="suggestion-header">
          <h1>💡 {t.healthSuggestions}</h1>
          <button onClick={() => setShowLangPopup(true)} className="lang-btn">
            {lang === "en" ? "🇬🇧 " + t.english : "🇦🇺 " + t.kriol}
          </button>
        </div>

        {/* 🌐 LANGUAGE POPUP */}
        {showLangPopup && (
          <div
            className="popup-overlay"
            onClick={() => setShowLangPopup(false)}
          >
            <div className="popup-content" onClick={(e) => e.stopPropagation()}>
              <h3 className="popup-title"> {t.chooseLanguage}</h3>
              <div className="popup-options">
                <button
                  className={`popup-option ${lang === "en" ? "selected" : ""}`}
                  onClick={() => handleLangSelect("en")}
                >
                  🇬🇧 {translations.en.english}
                </button>
                <button
                  className={`popup-option ${
                    lang === "kriol" ? "selected" : ""
                  }`}
                  onClick={() => handleLangSelect("kriol")}
                >
                  🇦🇺 {translations.kriol.kriol}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ✅ Possible Conditions */}
        <section>
          <h2 className="section-title">❤️ {t.possibleConditions}</h2>
          {predictions.length > 0 ? (
            <ul className="condition-list">
              {predictions.map((p, i) => (
                <li key={i}>
                  {p.disease} – {t.confidence}: {(p.score * 100).toFixed(0)}%
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${p.score * 100}%` }}
                    ></div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p>{lang === "en" ? "No conditions found." : "Nating sik yet."}</p>
          )}
        </section>

        <br />

        {/* 🌿 What You Can Do */}
        <section>
          <h2 className="section-title">🌿 {t.whatYouCanDoNow}</h2>
          {suggestions.length > 0 ? (
            suggestions.map((item, i) => (
              <div key={i} className="suggestion-card">
                <p className="font-bold text-lg capitalize">{item.symptom}</p>
                <p>
                  <strong>{t.advice}:</strong> {item.advice}
                </p>
              </div>
            ))
          ) : (
            <p>
              {lang === "en"
                ? "Stay hydrated and monitor your symptoms."
                : "Drink plenti watta an rest smol."}
            </p>
          )}
        </section>

        {/* FOOTER */}
        <div className="footer-buttons no-print">
          <button onClick={() => navigate(-1)} className="btn-primary">
            {t.backToResult}
          </button>
          <button onClick={() => navigate("/")} className="btn-primary">
            {t.backToChat}
          </button>
        </div>
      </div>
    </div>
  );
}
