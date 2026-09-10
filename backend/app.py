import os

from flask import Flask, Response, abort, send_from_directory
from flask_cors import CORS

from db import close_db, init_db
from events import subscribe
from extensions import limiter
from routes.products import products_bp
from routes.shopping_list import shopping_list_bp

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "shopping.db"))
STATIC_DIR = os.environ.get("STATIC_DIR", os.path.join(os.path.dirname(__file__), "static"))


def create_app():
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
    app.config["DATABASE_PATH"] = DB_PATH

    # Any origin, not just a configured one: the app is reachable from
    # wherever a user points Settings > Server URL (the native app's local
    # origin, a browser on another device, etc. - see plan.md SS6). No
    # cookie/session auth exists yet in v1, so wildcard CORS isn't giving up
    # meaningful protection; this gets revisited once v2 profile sessions
    # exist (issue #8).
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # No default/global limit: reads (product/list listing) stay unlimited,
    # individual write routes opt in to their own limit via @limiter.limit(...).
    limiter.init_app(app)

    init_db(DB_PATH)
    app.teardown_appcontext(close_db)

    app.register_blueprint(products_bp)
    app.register_blueprint(shopping_list_bp)

    @app.get("/api/events")
    def events():
        """Server-Sent Events stream: pushes a small message whenever the
        shopping list changes, so other connected clients know to refetch it
        instead of waiting for a manual refresh."""
        return Response(subscribe(), mimetype="text/event-stream")

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
    # Only used for local development (gunicorn runs the app in production -
    # see docker-compose.yml). Off by default so an accidental production
    # invocation of this entrypoint doesn't expose the Werkzeug debugger.
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
