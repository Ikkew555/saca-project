import React from "react";

export default function Sidebar({ sessions = [], currentId, onNew, onSelect }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-head">
        <h3>💬 Chats</h3>
        <button className="btn-new" onClick={onNew}>+ New</button>
      </div>
      <ul className="session-list">
        {sessions.map(s => (
          <li
            key={s.id}
            className={`session-item ${s.id === currentId ? "active" : ""}`}
            onClick={() => onSelect(s.id)}
            title={s.title}
          >
            {s.title || "New chat"}
          </li>
        ))}
      </ul>
    </aside>
  );
}
