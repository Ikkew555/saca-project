import React, { useState, useEffect, useRef, useCallback } from "react";
import { useOutletContext } from "react-router-dom";
import "./chat.css";
import fever from "./assets/symptom/fever.png";
import cough from "./assets/symptom/cough.png";
import backPain from "./assets/symptom/backPain.png";
import dizziness from "./assets/symptom/dizziness.png";
import fatigue from "./assets/symptom/fatigue.png";
import chestPain from "./assets/symptom/chestPain.png";
import { translations } from "./translations.js";
import { useNavigate } from "react-router-dom";
import micIcon from "./assets/icons/microphone-white-shape.png";
import stopIcon from "./assets/icons/microphone-white-shape.png";

function Chatbot() {
  const {
    externalMessages = [],
    onExternalMessagesChange = () => {},
    currentChatId,
  } = useOutletContext();

  const getGreeting = (lang) =>
    lang === "kriol"
      ? "👋 Helo! Mi SACA. Yu save tokbaut yu sik o tap wan pichu we luk semsem long yu sik blo stat."
      : "👋 Hi there! I’m your Smart Clinical Assistant. You can describe your symptoms below or tap an image that looks similar to your symptom to get started.";

  const [text, setText] = useState("");
  const [messages, setMessages] = useState(() =>
    Array.isArray(externalMessages) ? externalMessages : []
  );
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const [isFinalLoading, setIsFinalLoading] = useState(false);
  const [showLangPopup, setShowLangPopup] = useState(true);
  const chatEndRef = useRef(null);
  const navigate = useNavigate();

  // helper: sync messages with parent context
  const pushAndSync = useCallback(
    (next) => {
      setMessages(next);
      onExternalMessagesChange(next);
    },
    [onExternalMessagesChange]
  );

  const appendAndSync = useCallback(
    (...items) => {
      setMessages((prev) => {
        const next = [...prev, ...items];
        onExternalMessagesChange(next);
        return next;
      });
    },
    [onExternalMessagesChange]
  );

  // 🌐 Language setup
  const [language, setLanguage] = useState(
    () => localStorage.getItem("lang") || "en"
  );
  const t = translations[language] || translations.en;

  // 👋 Greeting message
  useEffect(() => {
    const isEmptyRoom = (externalMessages?.length ?? 0) === 0;
    if (isEmptyRoom) {
      const greet = {
        sender: "bot",
        text: getGreeting(language),
        meta: { greeting: true },
      };
      pushAndSync([greet]);
    } else {
      setMessages(externalMessages);
    }
  }, [currentChatId, language, externalMessages, pushAndSync]);

  // Auto-scroll
  useEffect(() => {
    if (chatEndRef.current)
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const symptomImages = [
    { name: "fever", file: fever },
    { name: "cough", file: cough },
    { name: "fatigue", file: fatigue },
    { name: "dizziness", file: dizziness },
    { name: "chest pain", file: chestPain },
    { name: "back pain", file: backPain },
  ];

  // ✉️ Send text message to backend
  const handleSend = async (inputText, imageFile = null) => {
    const userInput = inputText || text;
    if (!userInput.trim()) return;

    if (imageFile) {
      appendAndSync({
        sender: "user",
        text: userInput,
        type: "image",
        file: imageFile,
      });
    } else {
      appendAndSync({ sender: "user", text: userInput });
    }

    setText("");
    setIsTyping(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user: "frontend-user",
          text: userInput,
          lang: language === "en" ? "english" : "kriol",
        }),
      });
      const data = await res.json();

      if (data.done) {
        setIsTyping(false);
        setIsFinalLoading(true);
        setTimeout(() => {
          setIsFinalLoading(false);
          navigate("/result", {
            state: {
              symptoms: data.symptoms || [],
              predictions: data.predictions || [],
              lang: data.lang || "english",
              symptom_details: data.symptom_details,
              severity: data.severity || null,
              slots: data.slots || {},
            },
          });
        }, 2000);
        return;
      }

      // normal reply with typing effect
      let fullHTML = data.message;
      setTimeout(() => {
        setIsTyping(false);
        appendAndSync({ sender: "bot", text: "" });
        let i = 0;
        const interval = setInterval(() => {
          i++;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              text: fullHTML.slice(0, i),
            };
            onExternalMessagesChange(updated);
            return updated;
          });
          if (i >= fullHTML.length) clearInterval(interval);
        }, 20);
      }, 2000);
    } catch (err) {
      console.error("Error:", err);
      setIsTyping(false);
    }
  };

  // 🎙️ Start voice recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (e) => chunks.push(e.data);

      recorder.onstop = async () => {
        setRecording(false);

        const blob = new Blob(chunks, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("file", blob, "voice.webm");
        formData.append("user", "frontend-user");
        formData.append("lang", language === "en" ? "english" : "kriol");

        appendAndSync({ sender: "user", text: "🎤 Voice message sent." });
        setIsTyping(true);
        appendAndSync({
          sender: "bot",
          text: "🎧 Analyzing your voice input...",
        });

        try {
          const res = await fetch("/api/voice", {
            method: "POST",
            body: formData,
          });
          const data = await res.json();

          // show what the bot heard
          if (data.transcribed_text) {
            appendAndSync({
              sender: "user",
              text: `${data.transcribed_text}`,
              // text: `🗣 You said: <i>${data.transcribed_text}</i>`,
            });
          }

          if (data.done) {
            setIsTyping(false);
            setIsFinalLoading(true);
            setTimeout(() => {
              setIsFinalLoading(false);
              navigate("/result", {
                state: {
                  symptoms: data.symptoms || [],
                  predictions: data.predictions || [],
                  lang: data.lang || "english",
                  symptom_details: data.symptom_details,
                  severity: data.severity || null,
                  slots: data.slots || {},
                },
              });
            }, 2000);
            return;
          }

          // show bot message with typing effect
          setIsTyping(false);
          appendAndSync({ sender: "bot", text: "" });
          const fullText = data.message || "No response from bot.";
          let i = 0;
          const interval = setInterval(() => {
            i++;
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                text: fullText.slice(0, i),
              };
              onExternalMessagesChange(updated);
              return updated;
            });
            if (i >= fullText.length) clearInterval(interval);
          }, 20);
        } catch (err) {
          console.error("Voice processing error:", err);
          pushAndSync([
            {
              sender: "bot",
              text:
                language === "kriol"
                  ? "Sori, mi no bin save lisin propali. Trai gen."
                  : "Sorry, I couldn’t process your voice. Please try again.",
            },
          ]);
          setIsTyping(false);
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setRecording(true);
    } catch (err) {
      console.error("Microphone error:", err);
      alert("Microphone not available or permission denied.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setRecording(false);
    }
  };

  const handleLangSelect = (langCode) => {
    setLanguage(langCode);
    localStorage.setItem("lang", langCode);
    setShowLangPopup(false);
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <h2 className="chatbot-title">{t.assistantTitle}</h2>
        <button onClick={() => setShowLangPopup(true)} className="lang-btn">
          {language === "en" ? "🇬🇧 English" : "🇦🇺 Kriol"}
        </button>
      </div>

      {showLangPopup && (
        <div className="popup-overlay" onClick={() => setShowLangPopup(false)}>
          <div className="popup-content" onClick={(e) => e.stopPropagation()}>
            <h3 className="popup-title">{t.chooseLanguage}</h3>
            <p>{t.chooseLangText}</p>
            <br />
            <div className="popup-options">
              <button
                className={`popup-option ${
                  language === "en" ? "selected" : ""
                }`}
                onClick={() => handleLangSelect("en")}
              >
                🇬🇧 English
              </button>
              <button
                className={`popup-option ${
                  language === "kriol" ? "selected" : ""
                }`}
                onClick={() => handleLangSelect("kriol")}
              >
                🇦🇺 Kriol
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="chat-box">
        {messages.length <= 1 && (
          <div className="symptom-gallery">
            <div className="gallery-grid">
              {symptomImages.map((sym, i) => (
                <div
                  key={i}
                  className="symptom-card-images"
                  onClick={() => handleSend(sym.name, sym.file)}
                >
                  <img src={sym.file} alt={sym.name} className="symptom-img" />
                </div>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`chat-message ${msg.sender === "user" ? "user" : "bot"}`}
          >
            {msg.type === "image" ? (
              <div className="message-bubble image-bubble">
                <img
                  src={msg.file}
                  alt={msg.text}
                  className="chat-image"
                  title={msg.text}
                />
              </div>
            ) : (
              <div
                className="message-bubble"
                dangerouslySetInnerHTML={{ __html: msg.text }}
              ></div>
            )}
          </div>
        ))}

        {isTyping && !isFinalLoading && (
          <div className="typing-indicator">
            <span>Health agent is thinking...</span>
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
            <div className="typing-dot"></div>
          </div>
        )}
        {isFinalLoading && (
          <div className="loading-overlay">
            <span>🧠 Analyzing your symptoms...</span>
            <div className="loading-dot"></div>
            <div className="loading-dot"></div>
            <div className="loading-dot"></div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <div className="input-section">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            language === "kriol"
              ? "Tokbaut yu sik..."
              : "Describe your symptoms..."
          }
          className="chat-input"
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />
        <button onClick={() => handleSend()} className="btn-send">
          {language === "kriol" ? "Sendim" : "Send"}
        </button>
        <button onClick={startRecording} className="btn-mic">
          <img src={micIcon} alt="Start recording" className="mic-img" />
        </button>
      </div>

      {recording && (
        <div className="popup-overlay">
          <div className="popup-content">
            <h3>🎙️ {language === "kriol" ? "Lisin naw..." : "Listening..."}</h3>
            <p>
              {language === "kriol"
                ? "Tokbaut yu sik, tap Stop ta yu finis."
                : "Speak about your symptoms. Tap stop when finished."}
            </p>
            <div className="recording-visualizer">
              <div className="recording-dot"></div>
              <div className="recording-dot"></div>
              <div className="recording-dot"></div>
            </div>
            <button onClick={stopRecording} className="btn-stop-record">
              ⏹ {language === "kriol" ? "Stopim" : "Stop"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Chatbot;
