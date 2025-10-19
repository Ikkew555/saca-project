# back-end/run.py
from flask import Flask
from flask_cors import CORS

# Optional: legacy routes (e.g., /api/voice, /api/match, i18n)
try:
    from flask_app.routes import routes_blueprint

    HAVE_FLASK_APP_ROUTES = True
except Exception:
    routes_blueprint = None
    HAVE_FLASK_APP_ROUTES = False

# New chat package blueprints
try:
    # Preferred: blueprints defined in chat/
    from app.chat.routes import chat_bp
    from app.chat.suggestions import suggestion_bp
except Exception as e:
    # Last resort: if someone still keeps api_chat.py around
    chat_bp = None
    suggestion_bp = None
    try:
        from app.api_chat import api_chat as chat_bp, suggestion_bp as _suggestion_bp

        suggestion_bp = _suggestion_bp
    except Exception:
        # Neither chat/ nor api_chat.py could be imported
        raise RuntimeError(
            "No chat API found. Ensure you have app/chat/ with routes.py & suggestions.py, "
            "or restore app/api_chat.py."
        ) from e


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Register blueprints
    if HAVE_FLASK_APP_ROUTES:
        app.register_blueprint(routes_blueprint)  # e.g., /api/voice, /api/match

    if chat_bp is not None:
        app.register_blueprint(chat_bp)  # /api/chat
    if suggestion_bp is not None:
        app.register_blueprint(suggestion_bp)  # /api/suggestions

    @app.get("/")
    def index():
        return {"message": "Flask backend is running!"}

    return app


if __name__ == "__main__":
    app = create_app()
    # Match your React proxy (http://localhost:5001)
    app.run(host="0.0.0.0", port=5001, debug=True)
