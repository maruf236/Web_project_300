import logging, time
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .config import Config
from .errors import register_error_handlers
from .db import fetch_one

limiter = Limiter(key_func=get_remote_address, default_limits=["300 per minute"], storage_uri="memory://")

def create_app():
    logging.basicConfig(level=logging.INFO, format='{"t":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}')
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, origins=[Config.CORS_ORIGIN])
    limiter.init_app(app)
    register_error_handlers(app)

    @app.before_request
    def _t0():
        g.t0 = time.time()

    @app.after_request
    def _log(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        resp.headers["Cache-Control"] = "no-store"
        logging.getLogger("ridevai").info("%s %s %s %dms", request.method, request.path,
                                          resp.status_code, (time.time() - g.get("t0", time.time())) * 1000)
        return resp

    @app.get("/health")
    def health():
        try:
            fetch_one("SELECT 1")
            return jsonify(ok=True)
        except Exception:
            return jsonify(ok=False), 503

    from .routes.auth import bp as auth_bp
    from .routes.offers import bp as offers_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(offers_bp, url_prefix="/api/offers")
    # Passenger search/booking (Week 4-5): @require_auth + @require_category("student") + @require_verified_identity
    return app
