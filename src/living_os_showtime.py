from flask import Flask, Response, jsonify, request
import os, json, time

from src.kernel.mini_os import MiniOS
from src.kernel.fcp_protocol import fcp_pack, fcp_parse
from src.api.routes import init_routes

# ⚡️ Вказуємо шлях до static/
app = Flask(__name__, static_folder="../static", static_url_path="")

kernel = MiniOS()

# Ініціалізація API
init_routes(app, kernel)

@app.route("/")
def index():
    # Віддає index.html зі статичної папки
    return app.send_static_file("index.html")

if __name__ == "__main__":
    print("[LivingOS Showtime] running → http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
