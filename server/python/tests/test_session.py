from valorai.crypto import sha256_hex
from valorai.errors import ApiError

from test_account import pytest_raises


def test_session_cookie_is_hashed_and_idle_expires(world):
    from valorai.account.validation import registration_from
    from test_account import registration
    created = world["account"].create(registration_from(registration(), world["clock"].today()), "ip")
    cookie = world["session"].start(created.id, secure=True)
    assert "HttpOnly" in cookie and cookie.endswith("; Secure")
    token = cookie.split("valorai_session=")[1].split(";")[0]
    assert token not in world["sessions"].rows
    assert sha256_hex(token) in world["sessions"].rows
    account, token_hash = world["session"].read(cookie)
    assert account.id == created.id
    assert world["sessions"].rows[token_hash].last_seen == world["clock"].now()
    world["clock"].advance(1800)
    with pytest_raises(ApiError) as expired:
        world["session"].read(cookie)
    assert expired.value.status == 401
    assert token_hash not in world["sessions"].rows


def test_pending_session_cannot_read_confirmed_routes(world):
    from valorai.account.validation import registration_from
    from test_account import registration
    created = world["account"].create(registration_from(registration(), world["clock"].today()), "ip")
    cookie = world["session"].start(created.id, secure=False)
    with pytest_raises(ApiError) as blocked:
        world["session"].read(cookie, confirmed=True)
    assert blocked.value.status == 403


def test_absolute_cap_expires_without_waiting_for_idle(world):
    from valorai.account.validation import registration_from
    from test_account import registration
    created = world["account"].create(registration_from(registration(), world["clock"].today()), "ip")
    cookie = world["session"].start(created.id, secure=False)
    world["clock"].advance(12 * 60 * 60)
    with pytest_raises(ApiError):
        world["session"].read(cookie)
