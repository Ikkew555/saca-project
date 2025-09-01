# 🧠 SACA — Smart Adaptive Clinical Assistant

**SACA** is a web-based application designed to support clinical decision-making through Machine Learning (ML) and Natural Language Processing (NLP). It aims to provide real-time, culturally safe health support for communities in need, especially those in remote or underserved areas.

## 📁 Project Structure

SACA-PROJECT/
├── backend/ # Flask (Python) backend for ML/NLP processing
│ ├── flask_app/ # Python modules for routes, ML models, NLP logic
│ ├── run.py # Flask server entry point
│ └── requirements.txt
├── frontend/ # React app built with Vite
│ ├── public/
│ ├── src/
│ ├── package.json
│ └── vite.config.js
└── README.md # Project documentation

## 🚀 Features

- 🔍 ML model integration for predictive analysis
- 🧠 NLP-powered text summarization or classification
- ⚛️ React frontend for fast and interactive UI
- 🌐 REST API built with Flask (CORS-enabled)
- 🧩 Easy to extend or deploy

## 🛠️ How to Run the Project

### 🔹 Frontend (React)

```bash
cd frontend
npm install
npm run dev
Visit: http://localhost:5173
```

### 🔹 Backend (Flask)

```bash
cd backend
pip install -r requirements.txt
python run.py
```