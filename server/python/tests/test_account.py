from datetime import datetime, timezone

from valorai.account.validation import old_enough, password_message, registration_from, valid_cpf
from valorai.errors import ApiError

from conftest import NOW, registration


def test_cpf_and_age_rules():
    today = datetime.fromtimestamp(NOW, timezone.utc)
    assert valid_cpf("529.982.247-25") is True
    assert valid_cpf("529.982.247-24") is False
    assert valid_cpf("111.111.111-11") is False
    assert old_enough("2010-10-29", today) is True
    assert old_enough("2010-10-30", today) is False
    assert old_enough("2000-02-30", today) is False


def test_password_rules_keep_the_last_failing_check():
    assert password_message("a" * 8) == "Inclua um número."
    assert password_message("A1" + "x" * 31) == "Use no máximo 32 caracteres."
    assert password_message("A1" + "界" * 24) == "A senha excede o limite de 72 bytes."
    assert password_message("TestingOnly8") is None


def test_registration_rejects_a_mismatch_and_missing_consent(clock):
    with pytest_raises(ApiError) as mismatch:
        registration_from(registration(confirmPassword="Different8"), clock.today())
    assert mismatch.value.fields["confirmPassword"] == "As senhas precisam ser iguais."
    with pytest_raises(ApiError) as consent:
        registration_from(registration(demoConsent=False), clock.today())
    assert consent.value.status == 422


def test_duplicate_identity_and_login_lockout(world):
    data = registration_from(registration(), world["clock"].today())
    created = world["account"].create(data, "ip")
    with pytest_raises(ApiError) as duplicate:
        world["account"].create(data, "ip")
    assert duplicate.value.status == 409
    assert created.password_hash == "hash:TestingOnly8"
    with pytest_raises(ApiError):
        world["account"].authenticate("fixture@example.com", "WrongPass1", "ip")
    assert world["hasher"].checked == ["WrongPass1"]
    for _ in range(5):
        with pytest_raises(ApiError) as failed:
            world["account"].authenticate("missing@example.com", "WrongPass1", "ip")
        assert "cinco minutos" not in str(failed.value)
    assert world["hasher"].hashed[-1] == "WrongPass1"
    with pytest_raises(ApiError) as blocked:
        world["account"].authenticate("missing@example.com", "WrongPass1", "ip")
    assert blocked.value.status == 401
    assert "cinco minutos" in str(blocked.value)
    signed_in = world["account"].authenticate(created.email, "TestingOnly8", "ip")
    world["accounts"].deactivate(signed_in.id)
    with pytest_raises(ApiError):
        world["account"].authenticate(created.email, "TestingOnly8", "ip")


def test_deactivation_keeps_finance_and_drops_sessions(world):
    data = registration_from(registration(), world["clock"].today())
    created = world["account"].create(data, "ip")
    world["accounts"].update_finance(created.id, 350000, 180000, "reserve", NOW)
    world["session"].start(created.id, secure=False)
    world["confirmation"].issue(created.id)
    account = world["accounts"].find_by_id(created.id)
    world["account"].deactivate(account, "TestingOnly8", world["session"], world["confirmation"], "ip")
    stored = world["accounts"].find_by_id(created.id)
    assert stored.status == "inactive"
    assert stored.income == 350000
    assert world["sessions"].rows == {}
    assert world["confirmation"].codes.get(created.id) is None
    assert world["audit"].events[-1][1] == "account_deactivated"


def pytest_raises(error):
    import pytest
    return pytest.raises(error)
