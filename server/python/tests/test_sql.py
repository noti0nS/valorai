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
    rows = lessons.list()
    titles = [row["id"] for row in rows]
    assert titles == [
        "annual-expenses",
        "credit-card-control",
        "credit-score-negotiation",
        "debt-exit",
        "due-dates",
        "emergency-fund",
        "family-budget",
        "first-budget",
        "first-investments",
        "fixed-vs-variable-concepts",
        "inflation-purchasing-power",
        "invisible-spending",
        "irregular-income",
        "smart-goals",
        "thirteenth-and-extras",
    ]
    assert all("## " in row["body"] and row["category"] for row in rows)


class _Codes:
    def discard(self, account_id: str) -> None:
        self.discarded = account_id


def _sql_world():
    db = SqliteDb(connect_schema())
    clock = FixedClock(NOW)
    accounts = SqlAccounts(db, ids=lambda: "audit-account")
    audit = SqlAudit(db)
    account = AccountModule(accounts, MemoryKv(), BcryptHasher(), clock, audit)
    from valorai.account.validation import registration_from
    created = account.create(registration_from(registration(email="audit@example.com"), clock.today()), "ip")
    ledger = LedgerModule(SqlLedger(db, ids=iter(f"id-{n}" for n in range(100)).__next__), accounts, SqlLessons(db), clock, audit)
    return db, audit, account, ledger, created


def _events(db):
    return [row["event"] for row in db.query("SELECT event FROM audit_events ORDER BY id", (), ("event",))]


def test_triggers_record_data_changes_with_the_bound_request_context():
    db, audit, _account, ledger, created = _sql_world()
    audit.bind("hash-1", NOW + 5)
    payload = {"action": "create", "title": "Mercado", "amount": 10.0, "kind": "variable_expense", "category": "Alimentação & Mercado"}
    ledger.handle_transaction(created, payload, "hash-1")
    tx_id = ledger.ledger.list_transactions(created.id)[0].id
    ledger.handle_transaction(created, {"action": "toggle_status", "id": tx_id}, "hash-1")
    ledger.handle_transaction(created, {"action": "validate", "id": tx_id}, "hash-1")
    ledger.handle_transaction(created, {**payload, "action": "update", "id": tx_id, "title": "Mercado 2"}, "hash-1")
    ledger.handle_transaction(created, {"action": "delete", "id": tx_id}, "hash-1")
    ledger.handle_limit(created, {"scope": "category", "category": "Transporte", "limit": 50.0}, "hash-1")
    ledger.handle_limit(created, {"scope": "category", "category": "Transporte", "limit": 80.0}, "hash-1")
    limit_id = ledger.ledger.list_limits(created.id)[0].id
    ledger.handle_limit(created, {"action": "delete", "id": limit_id}, "hash-1")
    assert _events(db) == [
        "registration_created", "transaction_created", "transaction_status_toggled", "transaction_updated",
        "transaction_updated", "transaction_deleted", "budget_limit_updated", "budget_limit_updated", "budget_limit_deleted",
    ]
    rows = db.query("SELECT ip_hash, created_at FROM audit_events WHERE event = 'transaction_created'", (), ("ip_hash", "created_at"))
    assert (rows[0]["ip_hash"], rows[0]["created_at"]) == ("hash-1", NOW + 5)


def test_audit_and_profile_history_are_append_only():
    import sqlite3
    import pytest
    db, _audit, account, _ledger, created = _sql_world()
    account.update_profile(created, {
        "name": "Outro Nome", "birthDate": "1995-06-15", "phone": "(82) 99999-1111",
        "postalCode": "57020-000", "state": "AL", "city": "Maceió",
    }, "ip")
    assert "profile_updated" in _events(db)
    for sql in (
        "UPDATE audit_events SET event = 'x'", "DELETE FROM audit_events",
        "UPDATE profile_changes SET changed_fields = '[]'", "DELETE FROM profile_changes",
    ):
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            db.execute(sql)


def test_deactivation_event_comes_from_the_status_trigger_once():
    db, _audit, account, _ledger, created = _sql_world()
    sessions = SqlSessions(db)
    account.deactivate(created, "TestingOnly8", sessions, _Codes(), "ip")
    assert _events(db).count("account_deactivated") == 1


def test_validation_flip_is_labelled_validated():
    db, audit, _account, ledger, created = _sql_world()
    audit.bind("h", NOW)
    ledger.handle_transaction(created, {"action": "create", "title": "Mercado", "amount": 10.0, "kind": "variable_expense", "category": "Alimentação & Mercado"}, "h")
    tx_id = ledger.ledger.list_transactions(created.id)[0].id
    db.execute("UPDATE transactions SET validated = 0 WHERE id = ?", (tx_id,))
    ledger.handle_transaction(created, {"action": "validate", "id": tx_id}, "h")
    assert _events(db)[-1] == "transaction_validated"


def test_goal_contribution_balance_is_kept_by_triggers():
    db, audit, _account, ledger, created = _sql_world()
    audit.bind("h", NOW)
    _updated, dashboard = ledger.handle_goal(created, {"target": 1000.0, "current": 100.0, "contribution": 50.0}, "h")
    assert dashboard["goal"]["current"] == 150.0
    tx = ledger.ledger.list_transactions(created.id)[0]
    assert tx.goal_contribution and tx.amount_cents == 5000
    # Editing the amount moves the balance by the difference.
    db.execute("UPDATE transactions SET amount_cents = 8000 WHERE id = ?", (tx.id,))
    assert _goal_cents(db, created.id) == 18000
    # Deleting the contribution takes it back out.
    ledger.handle_transaction(created, {"action": "delete", "id": tx.id}, "h")
    assert _goal_cents(db, created.id) == 10000
    # Without a recorded transaction the app still adds the contribution itself.
    fresh = SqlAccounts(db).find_by_id(created.id)
    ledger.handle_goal(fresh, {"contribution": 20.0, "recordTransaction": False}, "h")
    assert _goal_cents(db, created.id) == 12000
    assert ledger.ledger.list_transactions(created.id) == []


def test_typing_the_aporte_marker_does_not_touch_the_goal_and_flag_is_immutable():
    import sqlite3
    import pytest
    db, audit, _account, ledger, created = _sql_world()
    audit.bind("h", NOW)
    ledger.handle_transaction(created, {
        "action": "create", "title": "Manual", "amount": 40.0, "kind": "variable_expense",
        "category": "Reserva & Investimentos", "merchantDoc": "APORTE.META",
    }, "h")
    assert _goal_cents(db, created.id) == 0
    tx_id = ledger.ledger.list_transactions(created.id)[0].id
    with pytest.raises(sqlite3.DatabaseError, match="immutable"):
        db.execute("UPDATE transactions SET goal_contribution = 1 WHERE id = ?", (tx_id,))


def test_status_trigger_revokes_sessions_and_blocks_new_ones():
    import sqlite3
    import pytest
    db, _audit, _account, _ledger, created = _sql_world()
    sessions = SqlSessions(db)
    sessions.insert("a", created.id, NOW, NOW, NOW + 10)
    SqlAccounts(db).deactivate(created.id)
    assert sessions.find("a") is None
    with pytest.raises(sqlite3.DatabaseError, match="inactive"):
        sessions.insert("b", created.id, NOW, NOW, NOW + 10)


def _goal_cents(db, account_id):
    return db.query("SELECT goal_current_cents AS c FROM accounts WHERE id = ?", (account_id,), ("c",))[0]["c"]


def test_account_lifecycle_events_come_from_triggers():
    db, audit, _account, _ledger, created = _sql_world()
    audit.bind("h", NOW + 1)
    accounts = SqlAccounts(db)
    accounts.mark_demo_confirmed(created.id)
    accounts.update_finance(created.id, 100000, 50000, "reserve", NOW)
    assert _events(db) == ["registration_created", "demo_confirmation_completed", "financial_profile_updated"]
    row = db.query("SELECT ip_hash, created_at FROM audit_events WHERE event = 'financial_profile_updated'", (), ("ip_hash", "created_at"))[0]
    assert (row["ip_hash"], row["created_at"]) == ("h", NOW + 1)
