"""
LivingOS Showtime Edition — Flask entrypoint
"""

from flask import Flask
from src.api.routes import init_routes

app = Flask(__name__, static_folder="../static", static_url_path="/static")

# реєстрація роутів
init_routes(app)

if __name__ == "__main__":
    print("[LivingOS WOW] running at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
