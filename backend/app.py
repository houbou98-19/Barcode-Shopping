import os

from flask import Flask

from db import close_db, init_db
from routes.products import products_bp
from routes.shopping_list import shopping_list_bp

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "shopping.db"))


def create_app():
    app = Flask(__name__)
    app.config["DATABASE_PATH"] = DB_PATH

    init_db(DB_PATH)
    app.teardown_appcontext(close_db)

    app.register_blueprint(products_bp)
    app.register_blueprint(shopping_list_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
