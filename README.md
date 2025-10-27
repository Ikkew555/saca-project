# 🧠 SACA — Smart Adaptive Clinical Assistant

**SACA** is a web-based application designed to support clinical decision-making through Machine Learning (ML) and Natural Language Processing (NLP). It aims to provide real-time, culturally safe health support for communities in need, especially those in remote or underserved areas.

## 📁 Project Structure

```
SACA-PROJECT/
├── backend/ # Flask (Python) backend for ML/NLP logic
│ ├── app/ # Core logic, data, and utility modules
│ │ ├── cli_match.py # Symptom → Disease logic
│ │ ├── api_match.py # REST API for ML/NLP
│ │ ├── utils.py # Helper functions for CSV data
│ │ └── data/ # Dataset (.csv) for symptom/disease mapping
│ ├── flask_app/ # Flask routing layer
│ │ └── routes.py
│ ├── run.py # Flask server entry point
│ └── requirements.txt # Backend dependencies
│
├── frontend/ # React web app (user interface)
│ ├── public/
│ ├── src/
│ │ └── Chatbot.js # Chat interface for text/voice input
│ ├── package.json
│ └── vite.config.js # For Vite build system
│
└── README.md # Project documentation
```

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
npm start
Visit: http://localhost:3000
```

### 🔹 Backend (Python)

```bash
cd backend
pip install -r requirements.txt
python3 run.py
```

```
pip install pandas scikit-learn joblib (only for first-time)
```
