import logging
from flask import jsonify
from pydantic import ValidationError
import psycopg2.errors as pgerr

log = logging.getLogger("ridevai")

class HttpError(Exception):
    def __init__(self, status, message, code=None):
        super().__init__(message)
        self.status, self.message, self.code = status, message, code

def register_error_handlers(app):
    @app.errorhandler(HttpError)
    def _http(e):
        return jsonify(error=e.message, code=e.code), e.status

    @app.errorhandler(ValidationError)
    def _val(e):
        details = [{"path": ".".join(map(str, i["loc"])), "message": i["msg"]} for i in e.errors()]
        return jsonify(error="Validation failed", details=details), 400

    @app.errorhandler(pgerr.UniqueViolation)
    def _dup(_e):
        return jsonify(error="Already exists"), 409

    @app.errorhandler(404)
    def _404(_e):
        return jsonify(error="Not found"), 404

    @app.errorhandler(429)
    def _429(_e):
        return jsonify(error="Too many requests"), 429

    @app.errorhandler(Exception)
    def _500(e):
        log.exception("unhandled: %s", e)
        return jsonify(error="Internal server error"), 500
