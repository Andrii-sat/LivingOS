"""
LivingOS Showtime — Flask entrypoint
"""
import os
from flask import Flask, send_from_directory
from src.api.routes import bp as api_bp

app = Flask(__name__, static_folder="../static", static_url_path="")
app.register_blueprint(api_bp)

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/app.js")
def app_js():
    return send_from_directory(app.static_folder, "app.js")

@app.route("/style.css")
def style_css():
    return send_from_directory(app.static_folder, "style.css")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
