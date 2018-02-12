"""
Defines the blueprint for the web API
Integrates with the provided DOA to retrieve and create notes.
"""

from sanic import Blueprint
from sanic.request import Request
from sanic.response import json as resp_json

from .db import BaseNoteDOA
from .exceptions import NoteExpired, NoteNotFound

__all__ = ["bp"]


# splattable dicts to be used when creating erroneous or successful responses
_err = dict(success=False)
_suc = dict(success=True)

bp = Blueprint("api", url_prefix="/api")


class ResponseErrors:
    invalid_json = resp_json(dict(**_err, message="Invalid JSON"), status=415)
    invalid_params = resp_json(dict(**_err, message="Missing Parameters"), status=422)
    invalid_note = resp_json(dict(**_err, message="The note does not exist or has expired."), status=404)


@bp.route("/get", methods=["POST"])
async def api_get(request: Request):
    """
    Web API handler for retrieving notes. Should always return JSON data.

    :param request: request provided by Sanic
    :return:
    """
    if request.json is None:
        return ResponseErrors.invalid_json

    uid = request.json.get("uid", None)
    if not isinstance(uid, str):
        return ResponseErrors.invalid_params

    doa = request.app.config.doa
    assert isinstance(doa, BaseNoteDOA)

    try:
        note = await doa.get_by_uid(uid)
    except (NoteExpired, NoteNotFound):
        return ResponseErrors.invalid_note
    else:
        return resp_json(dict(**_suc, message="Successful", title=note["title"], note=note["note"]), status=200)


@bp.route("/create", methods=["POST"])
async def api_create(request: Request):
    """
    Web API handler for creating notes. Should always return JSON data.

    :param request: request provided by Sanic
    :return:
    """
    if request.json is None:
        return ResponseErrors.invalid_json

    n, t, e = map(request.json.get, ("note", "title", "expiration"))
    t = t or "Untitled"
    e = e or 0

    if not n:
        return ResponseErrors.invalid_params

    doa = request.app.config.doa
    assert isinstance(doa, BaseNoteDOA)

    uid = await doa.create_note(t, n, e)

    return resp_json(dict(**_suc, message="Successful", uid=uid), status=201)
