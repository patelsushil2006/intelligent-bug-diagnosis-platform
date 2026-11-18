import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from flask import Flask, jsonify
from config.config import Config
from config.logging_config import setup_logging
from database.db import init_db
from backend.routes.bug_routes import bug_bp
from backend.routes.health_routes import health_bp
from backend.routes.web_routes import web_bp
from knowledge_base.ingestion import DefectIngestionPipeline


def create_app(config_class=Config) -> Flask:
    """Application factory for Intelligent Bug Diagnosis Platform."""
    setup_logging()

    app = Flask(
        __name__,
        template_folder="frontend/templates",
        static_folder="frontend/static"
    )
    app.config.from_object(config_class)

    # Initialize relational database tables
    init_db()

    # Seed initial defect knowledge base if empty
    try:
        pipeline = DefectIngestionPipeline()
        pipeline.seed_initial_knowledge_base()
    except Exception as e:
        app.logger.warning(f"Initial knowledge base seeding deferred: {e}")

    # Register blueprints
    app.register_blueprint(web_bp)
    app.register_blueprint(bug_bp)
    app.register_blueprint(health_bp)

    # Global Error Handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "details": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({
            "error": "File size exceeds the allowed maximum limit of 16 MB."
        }), 413

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error occurred."}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5001)),
        debug=Config.DEBUG
    )
