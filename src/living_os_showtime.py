# src/living_os_showtime.py
from flask import Flask, send_from_directory
from src.api.routes import bp as api_bp

app = Flask(__name__, static_folder="../static", template_folder="../static")
app.register_blueprint(api_bp)

# Serve static frontend
@app.route("/")
def index():
    return send_from_directory("../static", "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory("../static", path)

if __name__ == "__main__":
    print("[LivingOS Showtime] running at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
