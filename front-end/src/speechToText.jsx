import React, { useState, useEffect } from "react";

function SpeechToText() {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [recognition, setRecognition] = useState(null);

  useEffect(() => {
    // Check browser support
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Your browser does not support speech recognition.");
      return;
    }

    const recognizer = new SpeechRecognition();

    // 🎤 Settings
    recognizer.lang = "en";
    recognizer.interimResults = true; // capture partial results live
    recognizer.continuous = true;     // keep listening until stopped

    // 📋 Handle results
    recognizer.onresult = (event) => {
      let currentTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        currentTranscript += event.results[i][0].transcript + " ";
      }
      setTranscript(currentTranscript.trim());
    };

    // ❌ Handle errors
    recognizer.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        alert("⚠️ Please allow microphone access in your browser settings.");
      }
      setIsListening(false);
    };

    recognizer.onstart = () => {
      console.log("🎤 Microphone is listening...");
    };

    recognizer.onend = () => {
      console.log("🛑 Microphone stopped.");
      setIsListening(false);
    };

    setRecognition(recognizer);
  }, []);

  const handleStart = () => {
    if (recognition && !isListening) {
      setTranscript("");
      setIsListening(true);
      recognition.start();
    }
  };

  const handleStop = () => {
    if (recognition && isListening) {
      recognition.stop();
      setIsListening(false);
    }
  };

  return (
    <div style={{ padding: "20px", textAlign: "center" }}>
      <h2>🎙️ Talk to SACA</h2>
      <button onClick={handleStart} disabled={isListening}>
        Start Talking
      </button>
      <button
        onClick={handleStop}
        disabled={!isListening}
        style={{ marginLeft: "10px" }}
      >
        Stop
      </button>

      <div style={{ marginTop: "20px" }}>
        <p>
          <strong>📝 You said:</strong>
        </p>
        <div
          style={{
            padding: "10px",
            border: "1px solid #ccc",
            minHeight: "40px",
          }}
        >
          {transcript || "(waiting for input...)"}
        </div>
      </div>
    </div>
  );
}

export default SpeechToText;
