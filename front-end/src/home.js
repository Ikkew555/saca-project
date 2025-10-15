import "./home.css";
import Logo from "./assets/logo_ngukurr.png";
import img1 from "./assets/img1.png";
import img2 from "./assets/img2.png";
import htw1 from "./assets/htw1.png";
import htw2 from "./assets/htw2.png";
import htw3 from "./assets/htw3.png";
import speak from "./assets/speech.png";
import translate from "./assets/technical-support.png";
import healthcare from "./assets/healthcare.png";
import { useState } from "react";
import LanguageSelector from "./languageSelector.jsx"; // ✅ import your flag selector
import { translations } from "./translations.js";
import { useNavigate } from "react-router-dom";

const HomePage = () => {
  const [language, setLanguage] = useState("en");
  const t = translations[language];
  const navigate = useNavigate();

  // ✨ Smooth scroll helper
  const scrollToSection = (id) => {
    const section = document.getElementById(id);
    if (section) {
      section.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <div>
      {/* 🧭 Navigation Bar */}
      <nav className="nav-bar">
        <div id="logo">
          <img src={Logo} alt="logo" />
        </div>
        <div id="nav-bar-menu-left">
          <button onClick={() => scrollToSection("introduce")}>
            {t.about}
          </button>
          <button onClick={() => scrollToSection("how-it-works")}>
            {t.howItWorks}
          </button>
          <button onClick={() => scrollToSection("township-news")}>
            {t.townshipNews}
          </button>
        </div>
        <div id="nav-bar-menu-right">
          <LanguageSelector language={language} onChange={setLanguage} />
        </div>
      </nav>

      {/* 🏠 Hero Section */}
      <section className="top-info">
        <h2>{t.title}</h2>
        <p>{t.subtitle}</p>
        <div className="button-list">
          <button onClick={() => navigate("/chatbot")}>{t.trySaca}</button>
        </div>
      </section>

      {/* ℹ️ About Section */}
      <section id="introduce">
        <div className="introduce-top">
          <div className="introduce-col-left">
            <div className="image-grid">
              <img src={img1} alt="Example 1" />
              <img src={img2} alt="Example 2" />
            </div>
          </div>
          <div className="introduce-col-right">
            <h2 id="title">{t.title_desc}</h2>
            <p>{t.desc}</p>
            <div className="button-list">
              <button id="visit-web" onClick={() => navigate("/chatbot")}>
                {t.visitWebsite}
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* 🌟 Benefits Section */}
      <section className="benefits">
        <h2>{t.benefitsTitle}</h2>
        <p className="subtitle">{t.benefitsSubtitle}</p>

        <div className="benefit-grid">
          <div className="benefit-box">
            <div className="icon">
              <img src={speak} alt="speak" />
            </div>
            <h2>{t.speakTitle}</h2>
            <p>{t.speakDesc}</p>
          </div>

          <div className="benefit-box">
            <div className="icon">
              <img src={translate} alt="translate" />
            </div>
            <h2>{t.translateTitle}</h2>
            <p>{t.translateDesc}</p>
          </div>

          <div className="benefit-box">
            <div className="icon">
              <img src={healthcare} alt="healthcare" />
            </div>
            <h2>{t.accessTitle}</h2>
            <p>{t.accessDesc}</p>
          </div>
        </div>
      </section>

      {/* ⚙️ How It Works */}
      <section id="how-it-works">
        <h2>{t.hiwTitle}</h2>
        <p className="intro-text">{t.hiwSubtitle}</p>
        <div className="steps">
          <div className="step">
            <img src={htw1} alt="Speak" />
            <h3>{t.step1}</h3>
            <p>{t.step1Desc}</p>
          </div>
          <div className="step">
            <img src={htw2} alt="Translate" />
            <h3>{t.step2}</h3>
            <p>{t.step2Desc}</p>
          </div>
          <div className="step">
            <img src={htw3} alt="Understand" />
            <h3>{t.step3}</h3>
            <p>{t.step3Desc}</p>
          </div>
        </div>
      </section>

      {/* 📰 Township News */}
      <section id="township-news">
        <h2>{t.townshipNews}</h2>
        <p>Another text or image here.</p>
      </section>
    </div>
  );
};

export default HomePage;
