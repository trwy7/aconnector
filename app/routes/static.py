from app import app

@app.route("/")
def robots():
    return "User-agent: *\nDisallow: /" # Thou shal not index my site!