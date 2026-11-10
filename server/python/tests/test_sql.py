from valorai.account.module import AccountModule
from valorai.coordinator.hasher import BcryptHasher
from valorai.finance.module import FinanceModule
from valorai.kv import MemoryKv
from valorai.storage import SqlAccounts, SqlAudit, SqlLessons, SqlSessions, SqliteDb, connect_schema
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
    finance.update(created, {"income": 10.2, "fixedExpenses": 0, "goal": "debt"}, "ip")
    sessions = SqlSessions(db)
    sessions.insert("hash", created.id, NOW, NOW, NOW + 10)
    account.deactivate(accounts.find_by_id(created.id), "TestingOnly8", sessions, _Codes(), "ip")
    stored = accounts.find_by_id(created.id)
    assert stored.status == "inactive"
    assert stored.income == 1020
    assert sessions.find("hash") is None
    titles = [row["id"] for row in SqlLessons(db).list()]
    assert titles == ["due-dates", "emergency-fund", "first-budget"]


class _Codes:
    def discard(self, account_id: str) -> None:
        self.discarded = account_id
