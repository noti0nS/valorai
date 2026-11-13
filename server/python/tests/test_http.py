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


def test_rf008_password_recovery_demo_flow_and_session_revocation(world):
    from test_account import registration
    api = world["api"]
    created = post(api, "/api/register", registration())
    owner = cookie_of(created)
    inbox = api.handle("GET", "http://127.0.0.1:8787/api/demo-inbox", {"cookie": owner}, b"")
    confirmed = post(api, "/api/confirm", {"code": inbox.body["code"]}, owner)
    session1 = cookie_of(confirmed)

    # Uniform response for unknown and known emails
    unknown = post(api, "/api/recovery/request", {"email": "naoexiste@example.com"})
    known = post(api, "/api/recovery/request", {"email": "fixture@example.com"})
    assert unknown.status == 200 and known.status == 200
    assert unknown.body["message"] == known.body["message"]

    # Demo inbox reveals recovery code for known email only
    assert post(api, "/api/recovery/demo-inbox", {"email": "naoexiste@example.com"}).status == 404
    rec_inbox = post(api, "/api/recovery/demo-inbox", {"email": "fixture@example.com"})
    assert rec_inbox.status == 200
    code = rec_inbox.body["code"]
    assert len(code) == 6

    # Wrong code is rejected; correct code resets password and revokes active sessions
    assert post(api, "/api/recovery/reset", {
        "email": "fixture@example.com", "code": "000000", "newPassword": "NewPassword9", "confirmPassword": "NewPassword9",
    }).status == 400
    reset = post(api, "/api/recovery/reset", {
        "email": "fixture@example.com", "code": code, "newPassword": "NewPassword9", "confirmPassword": "NewPassword9",
    })
    assert reset.status == 200
    assert api.handle("GET", "http://127.0.0.1:8787/api/session", {"cookie": session1}, b"").status == 401
    assert post(api, "/api/login", {"identifier": "fixture@example.com", "password": "TestingOnly8"}).status == 401
    assert post(api, "/api/login", {"identifier": "fixture@example.com", "password": "NewPassword9"}).status == 200


def test_rf009_authenticated_password_change_revokes_other_sessions(world, monkeypatch):
    from test_account import registration
    api = world["api"]
    tokens = iter([f"{i:064x}" for i in range(1, 10)])
    monkeypatch.setattr(api.session, "tokens", lambda: next(tokens))
    created = post(api, "/api/register", registration())
    owner = cookie_of(created)
    inbox = api.handle("GET", "http://127.0.0.1:8787/api/demo-inbox", {"cookie": owner}, b"")
    confirmed = post(api, "/api/confirm", {"code": inbox.body["code"]}, owner)
    session_a = cookie_of(confirmed)
    login_b = post(api, "/api/login", {"identifier": "fixture@example.com", "password": "TestingOnly8"})
    session_b = cookie_of(login_b)

    wrong = post(api, "/api/password", {
        "currentPassword": "WrongPassword1", "newPassword": "UpdatedPass9", "confirmPassword": "UpdatedPass9",
    }, session_a)
    assert wrong.status == 422

    changed = post(api, "/api/password", {
        "currentPassword": "TestingOnly8", "newPassword": "UpdatedPass9", "confirmPassword": "UpdatedPass9",
    }, session_a)
    assert changed.status == 200
    new_session_a = cookie_of(changed)
    assert api.handle("GET", "http://127.0.0.1:8787/api/session", {"cookie": session_b}, b"").status == 401
    assert api.handle("GET", "http://127.0.0.1:8787/api/session", {"cookie": new_session_a}, b"").status == 200


def test_resend_mailer_sends_confirmation_and_recovery_codes(world):
    from test_account import registration
    from valorai.mailer import ResendMailer

    sent = []

    def fake_post(url, headers, body, timeout_s):
        sent.append((url, headers, json.loads(body)))
        return 200, '{"id":"email_123"}'

    api = world["api"]
    api.email_mode = "resend"
    api.mailer = ResendMailer("re_test_key", "ValorAI <noreply@mail.noti0ns.dev>", http_post=fake_post)

    created = post(api, "/api/register", registration())
    assert created.status == 201
    assert len(sent) == 1
    assert sent[0][0] == "https://api.resend.com/emails"
    assert sent[0][2]["to"] == ["fixture@example.com"]
    assert "confirmação" in sent[0][2]["subject"].lower()
    # Demo inbox must be disabled when email_mode == 'resend'
    assert api.handle("GET", "http://127.0.0.1:8787/api/demo-inbox", {"cookie": cookie_of(created)}, b"").status == 404

    req = post(api, "/api/recovery/request", {"email": "fixture@example.com"})
    assert req.status == 200
    assert len(sent) == 2
    assert "recuperação" in sent[1][2]["subject"].lower()
    assert post(api, "/api/recovery/demo-inbox", {"email": "fixture@example.com"}).status == 404
