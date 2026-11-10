import json
from pathlib import Path

from valorai.coordinator.hasher import BcryptHasher
from valorai.http import admit


def post(api, path, payload, cookie=None, url="http://127.0.0.1:8787"):
    headers = {"content-type": "application/json"}
    if cookie:
        headers["cookie"] = cookie
    return api.handle("POST", f"{url}{path}", headers, json.dumps(payload).encode())


def cookie_of(result) -> str:
    return result.headers["Set-Cookie"].split(";", 1)[0]


def test_registration_slice_matches_the_current_contract(world):
    from test_account import registration
    api = world["api"]
    created = post(api, "/api/register", registration())
    assert created.status == 201
    assert created.body["account"]["emailVerified"] is False
    assert created.body["account"]["demoConfirmed"] is False
    assert "HttpOnly" in created.headers["Set-Cookie"]
    assert created.headers["Cache-Control"] == "no-store"
    owner = cookie_of(created)
    assert post(api, "/api/finance", {"income": 2000, "fixedExpenses": 1000, "goal": "reserve"}, owner).status == 403
    inbox = api.handle("GET", "http://127.0.0.1:8787/api/demo-inbox", {"cookie": owner}, b"")
    assert inbox.status == 200
    assert api.handle("GET", "http://127.0.0.1:8787/api/demo-inbox", {}, b"").status == 401
    confirmed = post(api, "/api/confirm", {"code": inbox.body["code"]}, owner)
    assert confirmed.status == 200
    assert confirmed.body["account"]["emailVerified"] is False
    assert confirmed.body["account"]["demoConfirmed"] is True
    owner = cookie_of(confirmed)
    assert post(api, "/api/confirm", {"code": inbox.body["code"]}, owner).status == 409
    saved = post(api, "/api/finance", {"income": 2000, "fixedExpenses": 1000, "goal": "reserve"}, owner)
    assert saved.status == 200
    assert saved.body["account"]["finance"] == {"income": 2000, "fixedExpenses": 1000, "goal": "reserve"}
    assert post(api, "/api/register", registration()).status == 409
    assert post(api, "/api/deactivate", {"password": "TestingOnly8"}, owner).status == 200
    assert api.handle("GET", "http://127.0.0.1:8787/api/session", {"cookie": owner}, b"").status == 401
    assert post(api, "/api/login", {"identifier": "fixture@example.com", "password": "TestingOnly8"}).status == 401


def test_origin_and_method_guards():
    denied = admit("POST", "/api/login", "https://invalid.example", "http://127.0.0.1:8787")
    assert denied is not None and denied.status == 403
    assert admit("PUT", "/api/login", "http://127.0.0.1:8787", "http://127.0.0.1:8787").status == 405
    assert admit("GET", "/assets/app.js", None, "http://127.0.0.1:8787") is None


def test_bcrypt_cost_stays_ten():
    stored = BcryptHasher().hash("TestingOnly8")
    assert stored.startswith("$2b$10$") or stored.startswith("$2a$10$")
    assert BcryptHasher().verify("TestingOnly8", stored) is True


def test_confirmation_storage_prefix_is_private():
    root = Path(__file__).resolve().parents[1] / "valorai"
    offenders = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if '"code:"' in path.read_text(encoding="utf-8") and not path.as_posix().endswith("confirmation/module.py")
    ]
    assert offenders == []
    assert "bcrypt" not in (root / "account" / "module.py").read_text(encoding="utf-8")
