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
        "accounts.insert", "transactions.insert", "transactions.update", "transactions.update",
        "transactions.update", "transactions.delete", "budget_limits.insert", "budget_limits.update", "budget_limits.delete",
    ]
    rows = db.query("SELECT ip_hash, created_at, entity_id FROM audit_events WHERE event = 'transactions.insert'", (), ("ip_hash", "created_at", "entity_id"))
    assert (rows[0]["ip_hash"], rows[0]["created_at"]) == ("hash-1", NOW + 5)
    # Every data event names the row it touched, including a delete.
    deleted = db.query("SELECT entity_id FROM audit_events WHERE event = 'transactions.delete'", (), ("entity_id",))
    assert deleted[0]["entity_id"] == tx_id == rows[0]["entity_id"]


def test_context_is_reset_after_a_request_so_stray_writes_are_visibly_unbound():
    db, audit, _account, _ledger, created = _sql_world()
    audit.bind("hash-1", NOW + 5)
    audit.unbind()
    SqlAccounts(db).update_finance(created.id, 100000, 50000, "reserve", NOW)
    row = db.query("SELECT ip_hash, created_at FROM audit_events WHERE event = 'accounts.update'", (), ("ip_hash", "created_at"))[0]
    assert (row["ip_hash"], row["created_at"]) == ("unbound", 0)


def test_generated_migration_matches_the_generator():
    import importlib.util
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("audit_triggers", root / "tools" / "audit_triggers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    migration = (root / "migrations" / "0009_generic_audit.sql").read_text(encoding="utf-8")
    assert migration == module.render()


def test_audit_and_profile_history_are_append_only():
    import sqlite3
    import pytest
    db, _audit, account, _ledger, created = _sql_world()
    account.update_profile(created, {
        "name": "Outro Nome", "birthDate": "1995-06-15", "phone": "(82) 99999-1111",
        "postalCode": "57020-000", "state": "AL", "city": "Maceió",
    }, "ip")
    assert "accounts.update" in _events(db)
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
    assert _events(db).count("accounts.status.inactive") == 1


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
    # Only the goal screen's own save logged an account edit; the trigger-driven balance moves did not.
    assert _events(db).count("accounts.update") == 1
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
    assert _events(db) == ["accounts.insert", "accounts.status.demo_confirmed", "accounts.update"]
    row = db.query("SELECT ip_hash, created_at FROM audit_events WHERE event = 'accounts.update'", (), ("ip_hash", "created_at"))[0]
    assert (row["ip_hash"], row["created_at"]) == ("h", NOW + 1)


def test_views_aggregate_financial_summary_and_monthly_category_spending():
    db, audit, _account, ledger, created = _sql_world()
    audit.bind("h", NOW + 1)
    ledger.handle_transaction(created, {
        "action": "create", "title": "Salário", "amount": 3000.0, "kind": "income",
        "category": "Renda", "occurredOn": "2026-10-05", "status": "paid",
    }, "h")
    ledger.handle_transaction(created, {
        "action": "create", "title": "Mercado", "amount": 250.0, "kind": "variable_expense",
        "category": "Alimentação & Mercado", "occurredOn": "2026-10-10", "status": "paid",
    }, "h")
    ledger.handle_transaction(created, {
        "action": "create", "title": "Feira", "amount": 50.0, "kind": "variable_expense",
        "category": "Alimentação & Mercado", "occurredOn": "2026-10-15", "status": "pending",
    }, "h")
    ledger.handle_limit(created, {
        "action": "upsert", "scope": "category", "category": "Alimentação & Mercado", "limit": 600.0,
    }, "h")

    summary = db.query(
        "SELECT account_id, transaction_count, total_income_cents, total_expense_cents, pending_expense_cents "
        "FROM v_account_financial_summary WHERE account_id = ?",
        (created.id,),
    )[0]
    assert summary == {
        "account_id": created.id,
        "transaction_count": 3,
        "total_income_cents": 300000,
        "total_expense_cents": 30000,
        "pending_expense_cents": 5000,
    }

    spending = db.query(
        "SELECT year_month, category, expense_count, spent_cents, limit_cents, limit_usage_percent "
        "FROM v_monthly_category_spending WHERE account_id = ?",
        (created.id,),
    )[0]
    assert spending == {
        "year_month": "2026-10",
        "category": "Alimentação & Mercado",
        "expense_count": 2,
        "spent_cents": 30000,
        "limit_cents": 60000,
        "limit_usage_percent": 50.0,
    }
