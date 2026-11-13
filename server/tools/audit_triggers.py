"""Render migration 0009 (generic audit triggers).

D1 migrations are plain SQL and SQLite has no table wildcard in CREATE TRIGGER, so the one trigger shape is
repeated per table by this script. The committed `server/migrations/0009_generic_audit.sql` must equal the output;
`server/python/tests/test_audit_sql.py` fails when they drift.

    python server/tools/audit_triggers.py > server/migrations/0009_generic_audit.sql
"""

# table -> (column holding the owning account id, column holding the row id, optional WHEN for the insert trigger)
AUDITED = {
    "transactions": ("account_id", "id", "NEW.external_ref IS NULL OR NEW.external_ref NOT LIKE 'seed-%'"),
    "budget_limits": ("account_id", "id", None),
    "accounts": ("id", "id", None),
}

# Columns of accounts whose change counts as a profile or finance edit. goal_current_cents and status are left out:
# the goal balance is moved by transaction triggers (already audited as a transaction), and status has its own trigger.
ACCOUNT_EDIT_COLUMNS = (
    "name", "birth_date", "phone", "postal_code", "state", "city", "avatar_data",
    "income", "fixed_expenses", "goal", "completed_at", "goal_target_cents", "goal_monthly_cents",
)

# Triggers created by migrations 0003 and 0005, replaced by this migration.
SUPERSEDED = (
    "transactions_audit_insert", "transactions_audit_update", "transactions_audit_delete",
    "budget_limits_audit_insert", "budget_limits_audit_update", "budget_limits_audit_delete",
    "profile_changes_audit_insert",
    "accounts_audit_registered", "accounts_audit_confirmed", "accounts_audit_deactivated", "accounts_audit_finance",
)


def _trigger(table: str, op: str, when: str | None, account: str, entity: str, row: str, suffix: str, of: str = "") -> str:
    where = f"\nWHEN {when}" if when else ""
    return (
        f"CREATE TRIGGER {table}_audit_{suffix} AFTER {op.upper()}{of} ON {table}{where}\n"
        "BEGIN\n"
        "  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)\n"
        f"  SELECT {row}.{account}, '{table}.{op}', {row}.{entity}, ip_hash, at FROM audit_context WHERE id = 1;\n"
        "END;\n"
    )


def render() -> str:
    parts = [
        "-- Generic audit triggers, rendered by server/tools/audit_triggers.py. Do not edit by hand.\n"
        "-- One trigger shape per table and operation replaces the per-event triggers of 0003 and 0005.\n"
        "-- event is '<table>.<insert|update|delete>'; entity_id is the id of the changed row.\n",
        "ALTER TABLE audit_events ADD COLUMN entity_id TEXT;\n",
        "\n".join(f"DROP TRIGGER IF EXISTS {name};" for name in SUPERSEDED) + "\n",
    ]
    for table, (account, entity, insert_when) in AUDITED.items():
        parts.append(_trigger(table, "insert", insert_when, account, entity, "NEW", "i"))
        edit_of = f" OF {', '.join(ACCOUNT_EDIT_COLUMNS)}" if table == "accounts" else ""
        parts.append(_trigger(table, "update", None, account, entity, "NEW", "u", edit_of))
        if table != "accounts":
            parts.append(_trigger(table, "delete", None, account, entity, "OLD", "d"))
    parts.append(
        "-- Account status changes keep a readable event for RF002 and RF005: accounts.status.demo_confirmed, .inactive.\n"
        "CREATE TRIGGER accounts_audit_status AFTER UPDATE OF status ON accounts\n"
        "WHEN NEW.status <> OLD.status\n"
        "BEGIN\n"
        "  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)\n"
        "  SELECT NEW.id, 'accounts.status.' || NEW.status, NEW.id, ip_hash, at FROM audit_context WHERE id = 1;\n"
        "END;\n"
    )
    return "\n".join(parts)


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stdout.write(render())
