from flask import Flask
from flask_cors import CORS
from flask_app.routes import routes_blueprint
from app.api_chat import api_chat, suggestion_bp  # ✅ Add this import

app = Flask(__name__)
CORS(app)

# Register both Blueprints
app.register_blueprint(routes_blueprint)
app.register_blueprint(api_chat)  # ✅ Add this
app.register_blueprint(suggestion_bp)  # ✅ Add this


@app.route("/")
def index():
    return {"message": "Flask backend is running!"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
