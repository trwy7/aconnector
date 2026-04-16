from flask import redirect, abort, request
from app import app
from app.db import App, db
from app.utilities.users import require_user

@app.route("/app/<string:clientid>/revoke", methods=['POST'])
@require_user
def revoke_app(clientid):
    ca = App.query.get(clientid)
    if not ca:
        return abort(404)
    try:
        ca.user_auths.remove(request.user)
        db.session.commit()
    except ValueError:
        pass
    return redirect("/dashboard")