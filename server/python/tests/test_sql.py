from valorai.account.module import AccountModule
from valorai.coordinator.hasher import BcryptHasher
from valorai.finance.module import FinanceModule
from valorai.kv import MemoryKv
from valorai.ledger.module import LedgerModule
from valorai.storage import SqlAccounts, SqlAudit, SqlLedger, SqlLessons, SqlSessions, SqliteDb, connect_schema
from valorai.clock import FixedClock

from test_account import registration
from conftest import NOW


def test_sql_store_uses_the_existing_schema_and_keeps_finance_after_deactivation():
    db = SqliteDb(connect_schema())
    clock = FixedClock(NOW)
    accounts = SqlAccounts(db, ids=lambda: "sql-account")
    audit = SqlAudit(db)
    account = AccountModule(accounts, MemoryKv(), BcryptHasher(), clock, audit)
    from valorai.account.validation import registration_from
    created = account.create(registration_from(registration(email="sql@example.com"), clock.today()), "ip")
    finance = FinanceModule(accounts, clock, audit)
    updated_acc = finance.update(created, {"income": 10.2, "fixedExpenses": 0, "goal": "debt"}, "ip")
    lessons = SqlLessons(db)
    ledger = LedgerModule(SqlLedger(db), accounts, lessons, clock, audit)
    ledger.handle_transaction(
        updated_acc,
        {"action": "create", "title": "Supermercado", "amount": 150.0, "kind": "variable_expense", "category": "Alimentação & Mercado"},
        "ip",
    )
    ledger.handle_limit(
        updated_acc,
        {"action": "upsert", "scope": "category", "category": "Alimentação & Mercado", "limit": 500.0},
        "ip",
    )
    ledger.handle_lesson_progress(updated_acc, {"lessonId": "first-budget", "progressPercent": 100}, "ip")
    account.update_profile(
        updated_acc,
        {
            "name": "Cliente Atualizado",
            "birthDate": "1995-06-15",
            "phone": "(82) 99999-1111",
            "postalCode": "57020-000",
            "state": "AL",
            "city": "Maceió",
        },
        "ip",
    )

    sessions = SqlSessions(db)
    sessions.insert("hash", created.id, NOW, NOW, NOW + 10)
    account.deactivate(accounts.find_by_id(created.id), "TestingOnly8", sessions, _Codes(), "ip")
    stored = accounts.find_by_id(created.id)
    assert stored.status == "inactive"
    assert stored.income == 1020
    assert stored.name == "Cliente Atualizado"
    assert sessions.find("hash") is None
    # Logical deletion preserves transactions, limits, and profile history (RF005 / RNF03)
    dash = ledger.present_dashboard(stored)
    assert len(dash["transactions"]) == 1
    assert len(dash["limits"]) == 1
    assert len(accounts.list_profile_changes(created.id)) == 1
    titles = [row["id"] for row in lessons.list()]
    assert titles == ["due-dates", "emergency-fund", "first-budget"]


class _Codes:
    def discard(self, account_id: str) -> None:
        self.discarded = account_id
