from valorai.errors import ApiError

from test_account import pytest_raises, registration


def _pending(world):
    from valorai.account.validation import registration_from
    return world["account"].create(registration_from(registration(), world["clock"].today()), "ip")


def test_confirmation_limits_and_inbox_belong_to_the_pending_session(world):
    account = _pending(world)
    issued = world["confirmation"].issue(account.id)
    revealed = world["confirmation"].reveal(account)
    assert revealed["code"] == "000042"
    assert revealed["to"] == account.email
    assert revealed["simulated"] is True
    world["clock"].advance(1)
    with pytest_raises(ApiError) as early:
        world["confirmation"].issue(account.id)
    assert early.value.status == 429
    world["clock"].advance(60)
    world["confirmation"].issue(account.id)
    world["clock"].advance(60)
    world["confirmation"].issue(account.id)
    world["clock"].advance(60)
    with pytest_raises(ApiError) as hourly:
        world["confirmation"].issue(account.id)
    assert "três envios" in str(hourly.value)
    assert issued["expiresAt"] > issued["resendAt"]


def test_five_wrong_codes_block_the_challenge(world):
    account = _pending(world)
    world["confirmation"].issue(account.id)
    for _ in range(4):
        with pytest_raises(ApiError) as wrong:
            world["confirmation"].check(account, "111111")
        assert wrong.value.status == 400
    with pytest_raises(ApiError) as blocked:
        world["confirmation"].check(account, "111111")
    assert "Limite de tentativas" in str(blocked.value)
    with pytest_raises(ApiError) as exhausted:
        world["confirmation"].reveal(account)
    assert exhausted.value.status == 410


def test_a_matching_code_is_accepted_and_discard_hides_it(world):
    account = _pending(world)
    world["confirmation"].issue(account.id)
    world["confirmation"].check(account, "000042")
    world["confirmation"].discard(account.id)
    assert world["confirmation"].codes.get(account.id) is None
