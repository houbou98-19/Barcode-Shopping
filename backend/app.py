import os

from flask import Flask, abort, send_from_directory

from db import close_db, init_db
from routes.products import products_bp
from routes.shopping_list import shopping_list_bp

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "shopping.db"))
STATIC_DIR = os.environ.get("STATIC_DIR", os.path.join(os.path.dirname(__file__), "static"))


def create_app():
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
    app.config["DATABASE_PATH"] = DB_PATH

    init_db(DB_PATH)
    app.teardown_appcontext(close_db)

    app.register_blueprint(products_bp)
    app.register_blueprint(shopping_list_bp)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        """Serves the built frontend (production only - the Vite dev server
        handles this during local development). Falls back to index.html
        for any unknown path so client-side routing works."""
        if path.startswith("api/"):
            abort(404)
        full_path = os.path.join(app.static_folder, path)
        if path and os.path.isfile(full_path):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
