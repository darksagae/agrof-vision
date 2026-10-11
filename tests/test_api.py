import base64
import json

import pytest
from fastapi.testclient import TestClient

from agrof_vision.api import app
from agrof_vision.lambda_handler import handler


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["opencv_version"].startswith("5.")


def test_analyze_upload(client, healthy_jpeg):
    response = client.post("/api/analyze", files={"image": ("leaf.jpg", healthy_jpeg, "image/jpeg")})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["leaf"]["detected"]


def test_analyze_errors(client):
    assert client.post("/api/analyze").status_code == 422
    bad = client.post("/api/analyze", files={"image": ("x.txt", b"hello", "text/plain")})
    assert bad.status_code == 422 and "JPEG" in bad.json()["error"]
    big = client.post(
        "/api/analyze", files={"image": ("x.jpg", b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024), "image/jpeg")}
    )
    assert big.status_code == 413


def test_security_headers(client):
    headers = client.get("/api/health").headers
    assert headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]


def test_lambda_raw_and_json_bodies(healthy_jpeg):
    encoded = base64.b64encode(healthy_jpeg).decode()
    raw = handler({"body": encoded, "isBase64Encoded": True, "headers": {"Content-Type": "image/jpeg"}}, None)
    assert raw["statusCode"] == 200 and json.loads(raw["body"])["leaf"]["detected"]
    as_json = handler(
        {"body": json.dumps({"image": encoded}), "headers": {"content-type": "application/json"}}, None
    )
    assert as_json["statusCode"] == 200


def test_lambda_errors():
    assert handler({"requestContext": {"http": {"method": "GET"}}}, None)["statusCode"] == 405
    assert handler({"body": "{}"}, None)["statusCode"] == 422
    assert handler({"body": "%%%", "isBase64Encoded": True}, None)["statusCode"] == 422
