# poly_app/__init__.py
import os
from flask import Flask
from flask_cors import CORS

from poly_app.routes.auth import auth_bp
from poly_app.routes.profile import profile_bp
from poly_app.routes.books import books_bp
from poly_app.routes.cart import cart_bp
from poly_app.routes.purchases import purchases_bp
from poly_app.routes.reading import reading_bp
from poly_app.routes.ratings import ratings_bp
from poly_app.routes.comments import comments_bp
from poly_app.routes.recommendations import recommend_bp
from poly_app.routes.admin import admin_bp
from poly_app.routes.ui import ui_bp


def create_app():
    app = Flask(__name__)

    # Basic config
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    app.config["JWT_SECRET"] = os.getenv("JWT_SECRET", "supersecretkey")

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Blueprints - API
    app.register_blueprint(auth_bp,        url_prefix="/api/auth")
    app.register_blueprint(profile_bp,     url_prefix="/api/profile")
    app.register_blueprint(books_bp,       url_prefix="/api/books")
    app.register_blueprint(cart_bp,        url_prefix="/api/cart")
    app.register_blueprint(purchases_bp,   url_prefix="/api/purchases")
    app.register_blueprint(reading_bp,     url_prefix="/api/read")
    app.register_blueprint(ratings_bp,     url_prefix="/api/rate")
    app.register_blueprint(comments_bp,    url_prefix="/api/comments")
    app.register_blueprint(recommend_bp,   url_prefix="/api/recommendations")
    app.register_blueprint(admin_bp,       url_prefix="/api/admin")

    # UI blueprint
    app.register_blueprint(ui_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    return app
