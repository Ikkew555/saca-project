import React, { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import "./App.css";
import "./sidebar.css";

export default function Layout() {
  const [sessions, setSessions] = useState([]);
  const [currentId, setCurrentId] = useState(() => Date.now().toString());

  // โหลดจาก localStorage
  useEffect(() => {
    const saved = localStorage.getItem("saca_chat_sessions");
    if (saved) {
      const parsed = JSON.parse(saved);
      setSessions(parsed);
      if (parsed.length) setCurrentId(parsed[parsed.length - 1].id);
    } else {
      // มีแชทเปล่าสักอัน
      const first = { id: currentId, title: "New chat", messages: [] };
      setSessions([first]);
    }
  }, []);

  // บันทึกทุกครั้งที่ sessions เปลี่ยน
  useEffect(() => {
    localStorage.setItem("saca_chat_sessions", JSON.stringify(sessions));
  }, [sessions]);

  const current = sessions.find(s => s.id === currentId) || { id: currentId, title: "New chat", messages: [] };

  // ให้ Chatbot เรียกเวลามีการเปลี่ยนข้อความ
  const updateCurrentMessages = (newMessages) => {
    setSessions(prev => {
      const others = prev.filter(s => s.id !== currentId);
      const firstUser =
        newMessages.find(m => m.sender === "user" || m.role === "user");
      const title =
        (firstUser?.text || firstUser?.content || "New chat").slice(0, 40);
      return [...others, { id: currentId, title, messages: newMessages }];
    });
  };

  const handleNew = () => {
    const id = Date.now().toString();
    const fresh = { id, title: "New chat", messages: [] };
    setSessions(prev => [...prev, fresh]);
    setCurrentId(id);
  };

  const handleSelect = (id) => setCurrentId(id);

  return (
    <div className="app-shell">
      <Sidebar
        sessions={sessions}
        currentId={currentId}
        onNew={() => {
          const id = Date.now().toString();
          setSessions((p) => [...p, { id, title: "New chat", messages: [] }]);
          setCurrentId(id);
        }}
        onSelect={(id) => setCurrentId(id)}
      />
      <main className="app-main">
        <Outlet
          key={currentId}  // ✅ บังคับ remount เมื่อสลับห้อง/กด New
          context={{
            externalMessages: current.messages,
            onExternalMessagesChange: updateCurrentMessages,
            currentChatId: currentId,    // ✅ ส่ง id ไปให้ chat.js รู้ว่ามีการสลับห้อง
          }}
        />
      </main>
    </div>
  );
}
