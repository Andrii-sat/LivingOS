"""
LivingOS Showtime Edition — Flask entrypoint
"""

from flask import Flask, send_from_directory
from src.api.routes import init_routes

# static лежить на рівень вище за src/
app = Flask(__name__, static_folder="../static", static_url_path="/static")

# реєструємо маршрути (API, state, import, index)
init_routes(app)

@app.route("/")
def index():
    # видаємо static/index.html
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    print("[LivingOS WOW] running at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
