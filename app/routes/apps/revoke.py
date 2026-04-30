from flask import abort, redirect

from app import app
from app.db import UserAppLink
from app.types import request
from app.utilities.users import require_user


@app.route("/app/<string:clientid>/revoke", methods=["POST"])
@require_user
def revoke_app(clientid):
    link = UserAppLink.query.filter_by(
        app_id=clientid, 
        user_id=request.user.id
    ).first()
    if not link:
        return abort(404)
    link.revoke()
    return redirect("/dashboard")
