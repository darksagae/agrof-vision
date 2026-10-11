"""AWS Lambda adapter (Function URL or API Gateway HTTP API).

Accepts either a raw image body (Content-Type image/jpeg, image/png or
image/webp) or JSON {"image": "<base64>"}. Configure IAM auth or an
authorizer before exposing it; do not deploy an open public endpoint.
"""

from __future__ import annotations

import base64
import binascii
import json

from .pipeline import MAX_BYTES, ImageError, analyze

HEADERS = {
    "Content-Type": "application/json",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
}


def _reply(status: int, body: dict) -> dict:
    return {"statusCode": status, "headers": HEADERS, "body": json.dumps(body)}


def _image_bytes(event: dict) -> bytes:
    body = event.get("body") or ""
    if len(body) > MAX_BYTES * 4 // 3 + 1024:
        raise ImageError("Images must be 10 MB or smaller.")
    try:
        raw = base64.b64decode(body, validate=True) if event.get("isBase64Encoded") else body.encode()
    except binascii.Error as error:
        raise ImageError("The request body is not valid base64.") from error
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    if headers.get("content-type", "").split(";")[0].strip().startswith("image/"):
        return raw
    try:
        payload = json.loads(raw)
        return base64.b64decode(payload["image"], validate=True)
    except (ValueError, KeyError, TypeError, binascii.Error) as error:
        raise ImageError('Send an image body or JSON {"image": "<base64>"}.') from error


def handler(event: dict, _context: object) -> dict:
    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
    if method != "POST":
        return _reply(405, {"error": "Use POST."})
    try:
        return _reply(200, analyze(_image_bytes(event)))
    except ImageError as error:
        return _reply(422, {"error": str(error)})
