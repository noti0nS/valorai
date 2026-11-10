from dataclasses import dataclass


@dataclass
class Account:
    id: str
    name: str
    email: str
    cpf: str
    password_hash: str
    status: str
    city: str
    state: str
    birth_date: str
    phone: str
    postal_code: str
    created_at: int
    income: int | None = None
    fixed_expenses: int | None = None
    goal: str | None = None
    completed_at: int | None = None
    goal_target_cents: int = 500_000
    goal_current_cents: int = 0
    goal_monthly_cents: int = 75_000
    avatar_data: str | None = None


@dataclass(frozen=True)
class Registration:
    name: str
    cpf: str
    birth_date: str
    phone: str
    postal_code: str
    state: str
    city: str
    email: str
    password: str


@dataclass(frozen=True)
class ProfileUpdate:
    name: str
    birth_date: str
    phone: str
    postal_code: str
    state: str
    city: str
    avatar_data: str | None = None
    keep_avatar: bool = True


@dataclass
class Transaction:
    id: str
    account_id: str
    title: str
    amount_cents: int
    kind: str
    category: str
    channel: str
    occurred_on: str
    status: str = "paid"
    payment_method: str = "debit"
    merchant_doc: str | None = None
    confidence: int | None = None
    validated: bool = True
    external_ref: str | None = None
    notes: str | None = None
    created_at: int = 0


@dataclass
class BudgetLimit:
    id: str
    account_id: str
    scope: str
    category: str
    limit_cents: int
    warn_percent: int = 80
    created_at: int = 0
