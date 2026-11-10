import math
from decimal import Decimal, ROUND_HALF_UP

from valorai.errors import ApiError

GOALS = {"budget", "debt", "reserve", "invest"}
MAX_REAIS = 100_000_000


def to_cents(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or isinstance(value, float) and not math.isfinite(value):
        return None
    if value < 0 or value > MAX_REAIS:
        return None
    cents = (Decimal(value) if isinstance(value, int) else Decimal(str(value))).scaleb(2)
    return int(cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def to_reais(cents: int) -> int | float:
    if cents % 100 == 0:
        return cents // 100
    return cents / 100


class FinanceModule:
    def __init__(self, accounts, clock, audit):
        self.accounts = accounts
        self.clock = clock
        self.audit = audit

    def update(self, account, body: dict, ip_hash: str):
        errors: dict[str, str] = {}
        income = to_cents(body.get("income")) if isinstance(body, dict) else None
        expenses = to_cents(body.get("fixedExpenses")) if isinstance(body, dict) else None
        goal = body.get("goal") if isinstance(body, dict) else None
        if income is None:
            errors["income"] = "Informe um valor entre 0 e 100000000."
        if expenses is None:
            errors["fixedExpenses"] = "Informe um valor entre 0 e 100000000."
        if goal not in GOALS:
            errors["goal"] = "Selecione um objetivo."
        if errors:
            raise ApiError(422, "Confira os valores e selecione um objetivo.", errors)
        updated = self.accounts.update_finance(account.id, income, expenses, goal, self.clock.now())
        self.audit.record(account.id, "financial_profile_updated", ip_hash, self.clock.now())
        return updated

    def present(self, account) -> dict | None:
        if account.income is None:
            return None
        return {"income": to_reais(account.income), "fixedExpenses": to_reais(account.fixed_expenses or 0), "goal": account.goal}
