import React, { useState, useEffect, useRef, useCallback } from "react";
import { useOutletContext } from "react-router-dom";
import "./chat.css";
import fever from "./assets/symptom/fever.png";
import cough from "./assets/symptom/cough.png";
import backPain from "./assets/symptom/backPain.png";
import drizziness from "./assets/symptom/drizziness.png";
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
    currentChatId,     // ✅ รับ id ห้องแชทปัจจุบัน
  } = useOutletContext();

  const getGreeting = (lang) =>
  lang === "kriol"
    ? "👋 Helo! Mi SACA. Yu save tokbaut yu sik o tap wan pichu we luk semsem long yu sik blo stat."
    : "👋 Hi there! I’m your Smart Clinical Assistant. You can describe your symptoms below or tap an image that looks similar to your symptom to get started.";


  const [text, setText] = useState("");
  // เริ่มต้นเป็น [] ก่อน แล้วค่อยซิงก์ตาม context ภายหลัง
  const [messages, setMessages] = useState(() =>
    Array.isArray(externalMessages) ? externalMessages : []
  );
  // const [text, setText] = useState("");
  // const [chat, setChat] = useState([]);
  // const [messages, setMessages] = useState(externalMessages);
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const [isFinalLoading, setIsFinalLoading] = useState(false);
  const [showLangPopup, setShowLangPopup] = useState(true);
  // const { externalMessages = [], onExternalMessagesChange = () => {} } = useOutletContext() || {};
  const chatEndRef = useRef(null);
  const navigate = useNavigate();
  // const greetedOnce = useRef(false);


  // helper: อัปเดตทั้ง state ภายใน + แจ้ง Layout ให้บันทึกเป็นประวัติ
  const pushAndSync = useCallback((next) => {
    setMessages(next);
    onExternalMessagesChange(next);
  }, [onExternalMessagesChange]);

  const appendAndSync = useCallback((...items) => {
    setMessages((prev) => {
      const next = [...prev, ...items];
      onExternalMessagesChange(next);
      return next;
    });
  }, [onExternalMessagesChange]);


  // 🌐 Language setup
  const [language, setLanguage] = useState(
    () => localStorage.getItem("lang") || "en"
  );
  const t = translations[language] || translations.en;

  // 👋 Greeting message on load
  // ✅ ยิง greeting ทุกครั้งเมื่อเปิด "ห้องใหม่" (id เปลี่ยน) และห้องนั้นยังว่าง
  useEffect(() => {
    const isEmptyRoom = (externalMessages?.length ?? 0) === 0;
    if (isEmptyRoom) {
      const greet = { sender: "bot", text: getGreeting(language), meta: { greeting: true } };
      pushAndSync([greet]);
    } else {
      setMessages(externalMessages);
    }
  }, [currentChatId, language, externalMessages, pushAndSync]);

  useEffect(() => {
    const emptyRoom = messages.length === 0;
    const onlyGreeting =
      messages.length === 1 &&
      messages[0].sender === "bot" &&
      messages[0].meta?.greeting;

    // ถ้าห้องยังว่าง หรือมีแต่ greeting อยู่ → อัปเดตข้อความให้ตรงภาษา
    if (emptyRoom || onlyGreeting) {
      pushAndSync([{ sender: "bot", text: getGreeting(language), meta: { greeting: true } }]);
    }
    // ไม่ใส่ messages ใน dependency เพื่อกันลูป
  }, [language, currentChatId, pushAndSync]);

  // Auto-scroll
  useEffect(() => {
    if (chatEndRef.current)
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const symptomImages = [
    { name: "fever", file: fever },
    { name: "cough", file: cough },
    { name: "fatigue", file: fatigue },
    { name: "dizziness", file: drizziness },
    { name: "chest pain", file: chestPain },
    { name: "back pain", file: backPain },
  ];

  // ✉️ Send message to backend
  const handleSend = async (inputText, imageFile = null) => {
    const userInput = inputText || text;
    if (!userInput.trim()) return;

    // If clicked image
    if (imageFile) {
      appendAndSync({ sender: "user", text: userInput, type: "image", file: imageFile });
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

      // 🧠 If backend done
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
            },
          });
        }, 2000);
        return;
      }

      // 💬 Normal response
      let fullHTML = data.message;
      if (data.predictions?.length) {
        fullHTML += `<br/><br/><b>Possible Diseases:</b><br/>${data.predictions
          .map((p) => `${p.disease} — score: ${p.score}`)
          .join("<br/>")}`;
      }

      setTimeout(() => {
        setIsTyping(false);
        appendAndSync({ sender: "bot", text: "" });

        // typing effect: อัปเดตบับเบิลล่าสุดทีละตัวอักษรและซิงก์กับ Layout
        let i = 0;
        const interval = setInterval(() => {
          i++;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              text: fullHTML.slice(0, i),
            };
            onExternalMessagesChange(updated); // sync ไป Layout ทุก tick
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

  // 🎙️ Start Recording (with popup)
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      // 🧩 Collect voice data
      recorder.ondataavailable = (e) => chunks.push(e.data);

      // 🎯 Handle when user stops recording
      recorder.onstop = async () => {
        setRecording(false); // close popup

        const blob = new Blob(chunks, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("file", blob, "voice.webm");

        // 👤 Show user message in chat
        appendAndSync({ sender: "user", text: "🎤 Voice message sent." });

        // 🕐 Show analyzing loader
        setIsTyping(true);
        appendAndSync({ sender: "bot", text: "🎧 Analyzing your voice input..." });

        try {
          const res = await fetch("/api/voice", {
            method: "POST",
            body: formData,
          });
          const data = await res.json();

          setTimeout(() => {
            setIsTyping(false);

            const botMsg = {
              sender: "bot",
              text:
                data.message ||
                (language === "kriol"
                  ? "Mi bin lisin long yu. Mi save faindim infomesen."
                  : "I’ve listened to your voice and analyzed the information."),
            };

            // setChat((prev) => [...prev, botMsg]);
            pushAndSync([
              ...messages,
              { sender: "user", text: "🎤 Voice message sent." },
              botMsg,
            ]);
          }, 1500);
        } catch (err) {
          console.error("Voice processing error:", err);
          // setChat((prev) => [
          //   ...prev,
          //   {
          //     sender: "bot",
          //     text:
          //       language === "kriol"
          //         ? "Sori, mi no bin save lisin propali. Trai gen."
          //         : "Sorry, I couldn’t process your voice. Please try again.",
          //   },
          // ]);
          pushAndSync([
            ...messages,
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

      // 🚀 Begin recording
      recorder.start();
      setMediaRecorder(recorder);
      setRecording(true); // show popup
    } catch (err) {
      console.error("Microphone error:", err);
      alert("Microphone not available or permission denied.");
    }
  };

  // ⏹ Stop Recording (triggered from popup)
  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setRecording(false); // close popup
    }
  };

  // 🌐 Language selection popup
  const handleLangSelect = (langCode) => {
    setLanguage(langCode);
    localStorage.setItem("lang", langCode);
    setShowLangPopup(false);
  };

  return (
    <div className="chatbot-container">
      {/* 💬 Header */}
      <div className="chatbot-header">
        <h2 className="chatbot-title">{t.assistantTitle}</h2>
        <button onClick={() => setShowLangPopup(true)} className="lang-btn">
          {language === "en" ? "🇬🇧 English" : "🇦🇺 Kriol"}
        </button>
      </div>

      {/* 🌍 Language Popup */}
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

      {/* 💬 Chat Area */}
      <div className="chat-box">
        {messages.length <= 1 && (
          <div className="symptom-gallery">
            <div className="gallery-grid">
              {symptomImages.map((sym, i) => (
                <div
                  key={i}
                  className="symptom-card"
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

      {/* 🗣️ Input Section */}
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
        {/* 🎙️ Mic Button */}
        <button onClick={startRecording} className="btn-mic">
          <img src={micIcon} alt="Start recording" className="mic-img" />
        </button>
      </div>
      {/* 🎧 Voice Recording Popup */}
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
