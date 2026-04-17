from flask import render_template
from app import app

@app.errorhandler(404)
def error_not_found(e):
    return render_template("templates/error.html", status_code=404, error_message="Not found"), 404