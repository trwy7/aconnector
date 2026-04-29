from app import app

@app.route("/")
def robots():
    return "User-agent: *\nDisallow: /" # Don't allow indexing