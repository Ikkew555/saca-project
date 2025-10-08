import React, { useState, useEffect, useRef } from "react";
import "./chat.css";
import LanguageSelector from "./languageSelector.jsx";
import fever from "./assets/symptom/fever.png";
import cough from "./assets/symptom/cough.png";
import backPain from "./assets/symptom/backPain.png";
import drizziness from "./assets/symptom/drizziness.png";
import fatigue from "./assets/symptom/fatigue.png";
import chestPain from "./assets/symptom/chestPain.png";
import { translations } from "./translations.js"; // import translations
import Logo from "./assets/logo_ngukurr.png";
import { useNavigate } from "react-router-dom";

function Chatbot() {
  const [text, setText] = useState("");
  const [chat, setChat] = useState([]);
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);
  const [language, setLanguage] = useState("en-US"); //default
  const t = translations[language]; // easy alias
  const navigate = useNavigate();

  // 👋 Greeting message on load
  useEffect(() => {
    setChat([
      {
        sender: "bot",
        text: "👋 Hi there! I’m your Smart Clinical Assistant. You can describe your symptoms below or tap one of the images to get started.",
      },
    ]);
  }, []);

  // Auto-scroll on new chat
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [chat]);

  const symptomImages = [
    { name: "Fever", file: fever },
    { name: "Cough", file: cough },
    { name: "Fatigue", file: fatigue },
    { name: "Dizziness", file: drizziness },
    { name: "Chest pain", file: chestPain },
    { name: "Back pain", file: backPain },
  ];

  // ✉️ Send message to backend
  const handleSend = async (inputText) => {
    const userInput = inputText || text;
    if (!userInput.trim()) return;

    setChat((prev) => [...prev, { sender: "user", text: userInput }]);
    setText("");
    setIsTyping(true);

    try {
      const res = await fetch("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: userInput }),
      });
      const data = await res.json();

      const predictions = (data.predictions || []).map((p) => ({
        ...p,
        possibility: p.score < 0.4 ? "Low" : p.score < 0.7 ? "Medium" : "High",
      }));

      // Build message content
      let fullHTML =
        data.message || "It sounds like you might be experiencing:<br/>";
      if (data.symptoms?.length)
        fullHTML += `<br/><b>Detected Symptoms:</b> ${data.symptoms.join(
          ", "
        )}`;
      if (predictions.length)
        fullHTML += `<br/><b>Possible Diseases:</b><br/>${predictions
          .map((p) => `- ${p.disease}<br/><b>Possibility:</b> ${p.possibility}`)
          .join("<br/>")}`;

      // Simulate “thinking” before reply
      setTimeout(() => {
        setIsTyping(false);
        const botMsg = { sender: "bot", text: "" };
        setChat((prev) => [...prev, botMsg]);

        let i = 0;
        const interval = setInterval(() => {
          i++;
          setChat((prev) => {
            const updated = [...prev];
            updated[updated.length - 1].text = fullHTML.slice(0, i);
            return updated;
          });
          if (i >= fullHTML.length) clearInterval(interval);
        }, 20);
      }, 2500 + Math.random() * 800);
    } catch (err) {
      console.error("Error:", err);
      setIsTyping(false);
    }
  };

  // 🎙️ Start recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        const formData = new FormData();
        formData.append("file", blob, "voice.webm");

        setChat((prev) => [
          ...prev,
          { sender: "user", text: "🎤 Voice input..." },
        ]);
        setIsTyping(true);

        const res = await fetch("/api/voice", {
          method: "POST",
          body: formData,
        });
        const data = await res.json();

        const predictions = (data.predictions || []).map((p) => ({
          ...p,
          possibility:
            p.score < 0.4 ? "Low" : p.score < 0.7 ? "Medium" : "High",
        }));

        let fullText =
          data.message || "Here’s what I found from your voice input:\n";
        if (data.symptoms?.length)
          fullText += `\nDetected Symptoms: ${data.symptoms.join(", ")}\n`;
        if (predictions.length)
          fullText += `\nPossible Diseases:\n${predictions
            .map(
              (p) =>
                `- ${p.disease} — score: ${p.score} | Possibility: ${p.possibility}`
            )
            .join("\n")}`;

        setTimeout(() => {
          setIsTyping(false);
          const botMsg = { sender: "bot", text: "" };
          setChat((prev) => [...prev, botMsg]);

          let i = 0;
          const interval = setInterval(() => {
            i++;
            setChat((prev) => {
              const updated = [...prev];
              updated[updated.length - 1].text = fullText.slice(0, i);
              return updated;
            });
            if (i >= fullText.length) clearInterval(interval);
          }, 25);
        }, 2000 + Math.random() * 500);
      };

      recorder.start();
      setMediaRecorder(recorder);
      setRecording(true);
    } catch (err) {
      console.error("Microphone error:", err);
      alert("Microphone not available or permission denied.");
    }
  };

  // ⏹ Stop recording
  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setRecording(false);
    }
  };

  return (
    <div>
      <nav className="nav-bar">
        <div id="logo">
          <img src={Logo} alt="logo" onClick={() => navigate("/home")} />
        </div>
        <div id="nav-bar-menu-left">
          <button onClick={() => navigate("/home")}>{t.about}</button>
          <button onClick={() => navigate("/home")}>{t.howItWorks}</button>
          <button onClick={() => navigate("/home")}>{t.townshipNews}</button>
        </div>
        <div id="nav-bar-menu-right">
          <LanguageSelector language={language} onChange={setLanguage} />
        </div>
      </nav>
      <div className="chatbot-container">
        <h2 className="chatbot-title">🩺 Smart Clinical Assistant</h2>

        <div className="chat-box">
          {/* 🖼️ Default Symptom Picker */}
          {chat.length <= 1 && (
            <div className="symptom-gallery">
              <div className="gallery-grid">
                {symptomImages.map((sym, i) => (
                  <div
                    key={i}
                    className="symptom-card"
                    onClick={() => handleSend(sym.name)}
                  >
                    <img
                      src={sym.file}
                      alt={sym.name}
                      className="symptom-img"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* 💬 Chat messages */}
          {chat.map((msg, idx) => (
            <div
              key={idx}
              className={`chat-message ${
                msg.sender === "user" ? "user" : "bot"
              }`}
            >
              <div
                className="message-bubble"
                dangerouslySetInnerHTML={{ __html: msg.text }}
              ></div>
            </div>
          ))}

          {isTyping && (
            <div className="typing-indicator">
              <span>Health agent is thinking</span>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* 🔴 Recording Indicator */}
        {recording && (
          <div className="recording-status">
            <span className="recording-dot"></span> Recording... Speak now
          </div>
        )}

        {/* Input Section */}
        <div className="input-section">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Describe your symptoms..."
            className="chat-input"
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
          />
          <button onClick={() => handleSend()} className="btn-send">
            Send
          </button>
          <button
            onClick={recording ? stopRecording : startRecording}
            className={`btn-mic ${recording ? "recording" : ""}`}
          >
            {recording ? "Stop" : "🎤 Mic"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default Chatbot;
