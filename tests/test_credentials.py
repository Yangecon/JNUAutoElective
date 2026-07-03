import json

import pytest

from jnu_auto_elective.credentials import CredentialError, Credentials, get_header


def test_get_header_case_insensitive():
    headers = {"Cookie": "a=1", "TOKEN": "tok"}
    assert get_header(headers, "cookie") == "a=1"
    assert get_header(headers, "token") == "tok"
    assert get_header(headers, "missing") is None


def test_credentials_from_capture_success():
    captured = {
        "request_headers": {
            "Cookie": "JSESSIONID=abc",
            "Token": "token-1",
            "User-Agent": "Chrome",
        },
        "request_payload": "xh=20240001&xklcdm=BATCH01",
    }

    credentials = Credentials.from_capture(captured)

    assert credentials.cookie == "JSESSIONID=abc"
    assert credentials.token == "token-1"
    assert credentials.student_code == "20240001"
    assert credentials.elective_batch_code == "BATCH01"
    assert credentials.headers["User-Agent"] == "Chrome"


def test_credentials_from_capture_requires_headers():
    captured = {"request_headers": {"cookie": "a=1"}, "request_payload": "xh=1&xklcdm=B"}
    with pytest.raises(CredentialError, match="token"):
        Credentials.from_capture(captured)


def test_credentials_from_capture_requires_payload_fields():
    captured = {"request_headers": {"cookie": "a=1", "token": "tok"}, "request_payload": "x=1"}
    with pytest.raises(CredentialError, match="xh"):
        Credentials.from_capture(captured)


def test_credentials_round_trip(tmp_path):
    path = tmp_path / "credentials.json"
    credentials = Credentials(
        cookie="a=1",
        token="tok",
        student_code="20240001",
        elective_batch_code="BATCH01",
    )

    credentials.save(path)

    assert json.loads(path.read_text(encoding="utf-8"))["student_code"] == "20240001"
    assert Credentials.load(path) == credentials
