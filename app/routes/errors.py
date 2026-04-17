from flask import render_template, request
from flask_limiter.errors import RateLimitExceeded
from app import app, logger

@app.errorhandler(401)
def unauthorized(e):
    return render_template("templates/error.html", status_code=401, error_message="Unauthorized"), 401

@app.errorhandler(403)
def forbidden(e):
    return render_template("templates/error.html", status_code=403, error_message="Forbidden"), 403

@app.errorhandler(404)
def error_not_found(e):
    return render_template("templates/error.html", status_code=404, error_message="Not found"), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return render_template("templates/error.html", status_code=405, error_message="Method not allowed"), 405

@app.errorhandler(RateLimitExceeded)
def ratelimited(e):   
    return render_template("templates/error.html", status_code=429, error_message="Too many requests"), 429

@app.errorhandler(500)
@app.errorhandler(Exception)
def internal_server_error(e):
    logger.error("In request for %s: %s", request.path, str(e), exc_info=e)
    return render_template("templates/error.html", status_code=500, error_message="Internal server error"), 500