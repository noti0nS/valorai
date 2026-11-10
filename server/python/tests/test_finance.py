from valorai.errors import ApiError
from valorai.finance.module import to_cents, to_reais

from test_account import pytest_raises, registration


def test_cents_conversion_and_goal_rules(world):
    from valorai.account.validation import registration_from
    account = world["account"].create(registration_from(registration(), world["clock"].today()), "ip")
    assert to_cents(10.2) == 1020
    assert to_cents(-1) is None
    assert to_cents(float("inf")) is None
    assert to_reais(180050) == 1800.5
    updated = world["finance"].update(account, {"income": 3500, "fixedExpenses": 1800, "goal": "reserve"}, "ip")
    assert updated.income == 350000
    assert updated.fixed_expenses == 180000
    assert world["finance"].present(updated) == {"income": 3500, "fixedExpenses": 1800, "goal": "reserve"}
    with pytest_raises(ApiError) as rejected:
        world["finance"].update(account, {"income": 0, "fixedExpenses": 0, "goal": "invest-now"}, "ip")
    assert rejected.value.status == 422
    zero = world["finance"].update(account, {"income": 0, "fixedExpenses": 50, "goal": "budget"}, "ip")
    assert zero.income == 0
