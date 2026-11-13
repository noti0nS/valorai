from dataclasses import dataclass
from enum import StrEnum


class AccountStatus(StrEnum):
    PENDING = "pending"
    DEMO_CONFIRMED = "demo_confirmed"
    INACTIVE = "inactive"


class FinancialGoal(StrEnum):
    BUDGET = "budget"
    DEBT = "debt"
    RESERVE = "reserve"
    INVEST = "invest"


class TransactionKind(StrEnum):
    INCOME = "income"
    FIXED_EXPENSE = "fixed_expense"
    VARIABLE_EXPENSE = "variable_expense"


class TransactionChannel(StrEnum):
    MANUAL = "manual"
    IMPORT = "import"
    PHOTO = "photo"


class TransactionStatus(StrEnum):
    PAID = "paid"
    PENDING = "pending"


class PaymentMethod(StrEnum):
    PIX = "pix"
    CREDIT = "credit"
    DEBIT = "debit"
    CASH = "cash"
    BOLETO = "boleto"
    TRANSFER = "transfer"


class LimitScope(StrEnum):
    CATEGORY = "category"
    DAILY = "daily"
    WEEKLY = "weekly"
    CARD_SHARE = "card_share"


@dataclass
class Account:
    id: str
    name: str
    email: str
    cpf: str
    password_hash: str
    status: AccountStatus
    city: str
    state: str
    birth_date: str
    phone: str
    postal_code: str
    created_at: int
    income: int | None = None
    fixed_expenses: int | None = None
    goal: FinancialGoal | None = None
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
    kind: TransactionKind
    category: str
    channel: TransactionChannel
    occurred_on: str
    status: TransactionStatus = TransactionStatus.PAID
    payment_method: PaymentMethod = PaymentMethod.DEBIT
    merchant_doc: str | None = None
    confidence: int | None = None
    validated: bool = True
    external_ref: str | None = None
    notes: str | None = None
    created_at: int = 0
    goal_contribution: bool = False


@dataclass
class BudgetLimit:
    id: str
    account_id: str
    scope: LimitScope
    category: str
    limit_cents: int
    warn_percent: int = 80
    created_at: int = 0
