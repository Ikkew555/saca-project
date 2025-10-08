# run.py
from flask import Flask
from flask_cors import CORS
from flask_app.routes import routes_blueprint

app = Flask(__name__)
CORS(app)
app.register_blueprint(routes_blueprint)


@app.route("/")
def index():
    return {"message": "Flask backend is running!"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
