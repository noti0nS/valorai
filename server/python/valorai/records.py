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
