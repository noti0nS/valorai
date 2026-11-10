from datetime import datetime, timezone

import pytest

from valorai.account.module import AccountModule
from valorai.account.validation import old_enough, registration_from, valid_cpf
from valorai.clock import FixedClock
from valorai.confirmation.module import ConfirmationModule
from valorai.coordinator.hasher import BcryptHasher
from valorai.crypto import sha256_hex
from valorai.errors import ApiError
from valorai.finance.module import FinanceModule, to_cents
from valorai.http import RegistrationApi, admit
from valorai.kv import MemoryKv
from valorai.ledger.module import LedgerModule
from valorai.session.module import SessionModule
from valorai.storage import MemoryAccounts, MemoryAudit, MemoryLedger, MemoryLessons, MemorySessions
from valorai.throttle import Throttle

NOW = int(datetime(2026, 10, 29, 12, tzinfo=timezone.utc).timestamp())


class FakeHasher:
    def __init__(self):
        self.hashed: list[str] = []
        self.checked: list[str] = []

    def hash(self, password: str) -> str:
        self.hashed.append(password)
        return f"hash:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        self.checked.append(password)
        return password_hash == f"hash:{password}"


class OpenBot:
    def __init__(self):
        self.calls = 0

    def check(self, body, hostname, remote_ip):
        self.calls += 1


def registration(**overrides):
    body = {
        "name": "Cliente de Teste", "cpf": "529.982.247-25", "birthDate": "1995-06-15",
        "phone": "(82) 99999-0000", "postalCode": "57020-000", "state": "AL", "city": "Maceió",
        "email": "fixture@example.com", "password": "TestingOnly8", "confirmPassword": "TestingOnly8",
        "demoConsent": True,
    }
    body.update(overrides)
    return body


@pytest.fixture
def clock():
    return FixedClock(NOW)


@pytest.fixture
def world(clock):
    kv = MemoryKv()
    accounts = MemoryAccounts(ids=lambda: "account-1")
    audit = MemoryAudit()
    hasher = FakeHasher()
    sessions = MemorySessions()
    account = AccountModule(accounts, kv, hasher, clock, audit)
    session = SessionModule(sessions, accounts, clock, lambda: "ab" * 32)
    confirmation = ConfirmationModule(kv, clock, lambda: 42)
    finance = FinanceModule(accounts, clock, audit)
    throttle = Throttle(kv, clock)
    lessons = MemoryLessons([
        {"id": "first-budget", "title": "Seu primeiro orçamento", "description": "Um plano", "body": "Liste sua renda", "minutes": 3},
        {"id": "emergency-fund", "title": "Uma reserva, um passo de cada vez", "description": "Tranquilidade", "body": "Comece por uma meta", "minutes": 4},
        {"id": "due-dates", "title": "Contas em dia, mente tranquila", "description": "Vencimentos", "body": "Liste as contas", "minutes": 3},
    ])
    ledger_store = MemoryLedger()
    ledger = LedgerModule(ledger_store, accounts, lessons, clock, audit)
    bot = OpenBot()
    api = RegistrationApi(account, session, confirmation, finance, throttle, lessons, bot, clock, "", "demo", ledger=ledger)
    return {
        "api": api, "account": account, "session": session, "confirmation": confirmation, "finance": finance,
        "ledger": ledger, "ledger_store": ledger_store, "lessons": lessons,
        "accounts": accounts, "audit": audit, "hasher": hasher, "sessions": sessions, "clock": clock, "bot": bot, "kv": kv,
    }
