import json
import sqlite3
import uuid
from dataclasses import dataclass, replace
from pathlib import Path

from valorai.records import Account, BudgetLimit, ProfileUpdate, Transaction


@dataclass
class SessionRow:
    token_hash: str
    account_id: str
    created_at: int
    last_seen: int
    expires_at: int


class MemoryAccounts:
    def __init__(self, ids=None):
        self.rows: dict[str, Account] = {}
        self.changes: dict[str, list[dict]] = {}
        self.ids = ids or (lambda: str(uuid.uuid4()))

    def next_id(self) -> str:
        return self.ids()

    def insert(self, account: Account) -> None:
        if any(row.cpf == account.cpf or row.email == account.email for row in self.rows.values()):
            raise LookupError(account.id)
        self.rows[account.id] = account

    def find_by_identity(self, email: str, cpf: str) -> Account | None:
        return next((row for row in self.rows.values() if row.email == email or row.cpf == cpf), None)

    def find_for_login(self, email: str, cpf: str) -> Account | None:
        return self.find_by_identity(email, cpf)

    def find_by_id(self, account_id: str) -> Account | None:
        return self.rows.get(account_id)

    def mark_demo_confirmed(self, account_id: str) -> Account | None:
        account = self.rows.get(account_id)
        if account is None or account.status != "pending":
            return None
        updated = replace(account, status="demo_confirmed")
        self.rows[account_id] = updated
        return updated

    def update_finance(self, account_id: str, income: int, expenses: int, goal: str, completed_at: int) -> Account:
        updated = replace(self.rows[account_id], income=income, fixed_expenses=expenses, goal=goal, completed_at=completed_at)
        self.rows[account_id] = updated
        return updated

    def update_goal_progress(self, account_id: str, target_cents: int, current_cents: int, monthly_cents: int) -> Account:
        updated = replace(
            self.rows[account_id],
            goal_target_cents=target_cents,
            goal_current_cents=current_cents,
            goal_monthly_cents=monthly_cents,
        )
        self.rows[account_id] = updated
        return updated

    def update_profile(self, account_id: str, update: ProfileUpdate, changed_fields: list[str], changed_at: int) -> Account:
        current = self.rows[account_id]
        avatar = current.avatar_data if update.keep_avatar else update.avatar_data
        updated = replace(
            current,
            name=update.name,
            birth_date=update.birth_date,
            phone=update.phone,
            postal_code=update.postal_code,
            state=update.state,
            city=update.city,
            avatar_data=avatar,
        )
        self.rows[account_id] = updated
        if changed_fields:
            bucket = self.changes.setdefault(account_id, [])
            bucket.insert(0, {"id": len(bucket) + 1, "changedFields": changed_fields, "createdAt": changed_at})
        return updated

    def list_profile_changes(self, account_id: str) -> list[dict]:
        return list(self.changes.get(account_id, []))[:10]

    def deactivate(self, account_id: str) -> None:
        self.rows[account_id] = replace(self.rows[account_id], status="inactive")


class MemorySessions:
    def __init__(self):
        self.rows: dict[str, SessionRow] = {}

    def insert(self, token_hash: str, account_id: str, created_at: int, last_seen: int, expires_at: int) -> None:
        self.rows[token_hash] = SessionRow(token_hash, account_id, created_at, last_seen, expires_at)

    def find(self, token_hash: str) -> SessionRow | None:
        return self.rows.get(token_hash)

    def touch(self, token_hash: str, last_seen: int) -> None:
        row = self.rows[token_hash]
        self.rows[token_hash] = replace(row, last_seen=last_seen)

    def delete(self, token_hash: str) -> None:
        self.rows.pop(token_hash, None)

    def revoke_all(self, account_id: str) -> None:
        self.rows = {key: row for key, row in self.rows.items() if row.account_id != account_id}

    def delete_expired(self, now: int) -> None:
        self.rows = {key: row for key, row in self.rows.items() if row.expires_at > now}


class MemoryAudit:
    def __init__(self):
        self.events: list[tuple] = []

    def record(self, account_id: str | None, event: str, ip_hash: str, created_at: int) -> None:
        self.events.append((account_id, event, ip_hash, created_at))

    def bind(self, ip_hash: str, now: int) -> None:
        """Memory stores have no triggers, so there is no request context to bind."""


class MemoryLessons:
    def __init__(self, lessons: list[dict] | None = None):
        self.lessons = lessons or []
        self.progress: dict[tuple[str, str], dict] = {}

    def list(self) -> list[dict]:
        return sorted(self.lessons, key=lambda item: item["id"])

    def list_progress(self, account_id: str) -> dict[str, int]:
        return {
            lesson_id: entry["progressPercent"]
            for (acc_id, lesson_id), entry in self.progress.items()
            if acc_id == account_id
        }

    def set_progress(self, account_id: str, lesson_id: str, progress_percent: int, updated_at: int) -> None:
        self.progress[(account_id, lesson_id)] = {
            "lessonId": lesson_id,
            "progressPercent": progress_percent,
            "updatedAt": updated_at,
        }


class MemoryLedger:
    def __init__(self, ids=None):
        self.transactions: dict[str, Transaction] = {}
        self.limits: dict[str, BudgetLimit] = {}
        self.ids = ids or (lambda: str(uuid.uuid4()))

    def next_id(self) -> str:
        return self.ids()

    def list_transactions(self, account_id: str) -> list[Transaction]:
        rows = [tx for tx in self.transactions.values() if tx.account_id == account_id]
        return sorted(rows, key=lambda tx: (tx.occurred_on, tx.created_at, tx.id), reverse=True)

    def find_transaction(self, account_id: str, tx_id: str) -> Transaction | None:
        tx = self.transactions.get(tx_id)
        if tx is None or tx.account_id != account_id:
            return None
        return tx

    def has_external_ref(self, account_id: str, external_ref: str) -> bool:
        return any(
            tx.account_id == account_id and tx.external_ref == external_ref
            for tx in self.transactions.values()
        )

    def insert_transaction(self, tx: Transaction) -> Transaction:
        self.transactions[tx.id] = tx
        return tx

    def update_transaction(self, tx: Transaction) -> Transaction:
        self.transactions[tx.id] = tx
        return tx

    def delete_transaction(self, account_id: str, tx_id: str) -> bool:
        tx = self.transactions.get(tx_id)
        if tx is None or tx.account_id != account_id:
            return False
        del self.transactions[tx_id]
        return True

    def list_limits(self, account_id: str) -> list[BudgetLimit]:
        rows = [lim for lim in self.limits.values() if lim.account_id == account_id]
        return sorted(rows, key=lambda lim: (lim.scope, lim.category))

    def upsert_limit(self, limit: BudgetLimit) -> BudgetLimit:
        existing = next(
            (
                lim for lim in self.limits.values()
                if lim.account_id == limit.account_id and lim.scope == limit.scope and lim.category == limit.category
            ),
            None,
        )
        if existing is not None:
            updated = replace(existing, limit_cents=limit.limit_cents, warn_percent=limit.warn_percent)
            self.limits[existing.id] = updated
            return updated
        self.limits[limit.id] = limit
        return limit

    def delete_limit(self, account_id: str, limit_id: str) -> bool:
        lim = self.limits.get(limit_id)
        if lim is None or lim.account_id != account_id:
            return False
        del self.limits[limit_id]
        return True


def connect_schema(path: Path | None = None) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    if path is not None:
        connection.executescript(path.read_text(encoding="utf-8"))
    else:
        migrations_dir = Path(__file__).resolve().parents[2] / "migrations"
        for migration in sorted(migrations_dir.glob("*.sql")):
            connection.executescript(migration.read_text(encoding="utf-8"))
    return connection


class SqliteDb:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def query(self, sql: str, params: tuple = (), columns: tuple[str, ...] | None = None) -> list[dict]:
        cursor = self.connection.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def execute(self, sql: str, params: tuple = ()) -> int:
        cursor = self.connection.execute(sql, params)
        self.connection.commit()
        return cursor.rowcount


def account_from(row) -> Account:
    row = as_dict(row, ACCOUNT_COLUMNS)
    return Account(
        id=row["id"], name=row["name"], email=row["email"], cpf=row["cpf"], password_hash=row["password_hash"],
        status=row["status"], city=row["city"], state=row["state"], birth_date=row["birth_date"], phone=row["phone"],
        postal_code=row["postal_code"], created_at=row["created_at"], income=row["income"],
        fixed_expenses=row["fixed_expenses"], goal=row["goal"], completed_at=row["completed_at"],
        goal_target_cents=int(row.get("goal_target_cents") if row.get("goal_target_cents") is not None else 500_000),
        goal_current_cents=int(row.get("goal_current_cents") if row.get("goal_current_cents") is not None else 0),
        goal_monthly_cents=int(row.get("goal_monthly_cents") if row.get("goal_monthly_cents") is not None else 75_000),
        avatar_data=row.get("avatar_data"),
    )


class SqlAccounts:
    def __init__(self, db: SqliteDb, ids=None):
        self.db = db
        self.ids = ids or (lambda: str(uuid.uuid4()))

    def next_id(self) -> str:
        return self.ids()

    def insert(self, account: Account) -> None:
        try:
            self.db.execute(
                """INSERT INTO accounts(id, name, cpf, email, birth_date, phone, postal_code, state, city, password_hash, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (account.id, account.name, account.cpf, account.email, account.birth_date, account.phone,
                 account.postal_code, account.state, account.city, account.password_hash, account.created_at),
            )
        except Exception as error:
            if error.__class__.__name__ != "IntegrityError":
                raise
            raise LookupError(account.id) from None

    def find_by_identity(self, email: str, cpf: str) -> Account | None:
        rows = self.db.query("SELECT * FROM accounts WHERE cpf = ? OR email = ?", (cpf, email), ACCOUNT_COLUMNS)
        return account_from(rows[0]) if rows else None

    def find_for_login(self, email: str, cpf: str) -> Account | None:
        rows = self.db.query("SELECT * FROM accounts WHERE email = ? OR cpf = ?", (email, cpf), ACCOUNT_COLUMNS)
        return account_from(rows[0]) if rows else None

    def find_by_id(self, account_id: str) -> Account | None:
        rows = self.db.query("SELECT * FROM accounts WHERE id = ?", (account_id,), ACCOUNT_COLUMNS)
        return account_from(rows[0]) if rows else None

    def mark_demo_confirmed(self, account_id: str) -> Account | None:
        changed = self.db.execute("UPDATE accounts SET status = 'demo_confirmed' WHERE id = ? AND status = 'pending'", (account_id,))
        if changed == 0:
            return None
        return self.find_by_id(account_id)

    def update_finance(self, account_id: str, income: int, expenses: int, goal: str, completed_at: int) -> Account:
        self.db.execute(
            "UPDATE accounts SET income = ?, fixed_expenses = ?, goal = ?, completed_at = ? WHERE id = ?",
            (income, expenses, goal, completed_at, account_id),
        )
        found = self.find_by_id(account_id)
        if found is None:
            raise LookupError(account_id)
        return found

    def update_goal_progress(self, account_id: str, target_cents: int, current_cents: int, monthly_cents: int) -> Account:
        self.db.execute(
            "UPDATE accounts SET goal_target_cents = ?, goal_current_cents = ?, goal_monthly_cents = ? WHERE id = ?",
            (target_cents, current_cents, monthly_cents, account_id),
        )
        found = self.find_by_id(account_id)
        if found is None:
            raise LookupError(account_id)
        return found

    def update_profile(self, account_id: str, update: ProfileUpdate, changed_fields: list[str], changed_at: int) -> Account:
        if update.keep_avatar:
            self.db.execute(
                "UPDATE accounts SET name = ?, birth_date = ?, phone = ?, postal_code = ?, state = ?, city = ? WHERE id = ?",
                (update.name, update.birth_date, update.phone, update.postal_code, update.state, update.city, account_id),
            )
        else:
            self.db.execute(
                "UPDATE accounts SET name = ?, birth_date = ?, phone = ?, postal_code = ?, state = ?, city = ?, avatar_data = ? WHERE id = ?",
                (update.name, update.birth_date, update.phone, update.postal_code, update.state, update.city, update.avatar_data, account_id),
            )
        if changed_fields:
            self.db.execute(
                "INSERT INTO profile_changes(account_id, changed_fields, created_at) VALUES (?, ?, ?)",
                (account_id, json.dumps(changed_fields, ensure_ascii=False), changed_at),
            )
        found = self.find_by_id(account_id)
        if found is None:
            raise LookupError(account_id)
        return found

    def list_profile_changes(self, account_id: str) -> list[dict]:
        rows = self.db.query(
            "SELECT id, changed_fields, created_at FROM profile_changes WHERE account_id = ? ORDER BY created_at DESC, id DESC LIMIT 10",
            (account_id,),
            ("id", "changed_fields", "created_at"),
        )
        result = []
        for row in rows:
            item = as_dict(row, ("id", "changed_fields", "created_at"))
            try:
                fields = json.loads(item["changed_fields"])
            except Exception:
                fields = []
            result.append({"id": item["id"], "changedFields": fields, "createdAt": item["created_at"]})
        return result

    def deactivate(self, account_id: str) -> None:
        self.db.execute("UPDATE accounts SET status = 'inactive' WHERE id = ?", (account_id,))


class SqlSessions:
    def __init__(self, db: SqliteDb):
        self.db = db

    def insert(self, token_hash: str, account_id: str, created_at: int, last_seen: int, expires_at: int) -> None:
        self.db.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
            (token_hash, account_id, created_at, last_seen, expires_at),
        )

    def find(self, token_hash: str) -> SessionRow | None:
        rows = self.db.query(
            "SELECT token_hash, account_id, created_at, last_seen, expires_at FROM sessions WHERE token_hash = ?",
            (token_hash,),
            ("token_hash", "account_id", "created_at", "last_seen", "expires_at"),
        )
        if not rows:
            return None
        row = as_dict(rows[0], ("token_hash", "account_id", "created_at", "last_seen", "expires_at"))
        return SessionRow(row["token_hash"], row["account_id"], row["created_at"], row["last_seen"], row["expires_at"])

    def touch(self, token_hash: str, last_seen: int) -> None:
        self.db.execute("UPDATE sessions SET last_seen = ? WHERE token_hash = ?", (last_seen, token_hash))

    def delete(self, token_hash: str) -> None:
        self.db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def revoke_all(self, account_id: str) -> None:
        self.db.execute("DELETE FROM sessions WHERE account_id = ?", (account_id,))

    def delete_expired(self, now: int) -> None:
        self.db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))


class SqlAudit:
    """Identity events are recorded here; data-change events come from triggers (migration 0003)."""

    def __init__(self, db: SqliteDb):
        self.db = db

    def bind(self, ip_hash: str, now: int) -> None:
        """Give the audit triggers the IP hash and clock of the current request."""
        self.db.execute("UPDATE audit_context SET ip_hash = ?, at = ? WHERE id = 1", (ip_hash, now))

    def record(self, account_id: str | None, event: str, ip_hash: str, created_at: int) -> None:
        self.db.execute(
            "INSERT INTO audit_events(account_id, event, ip_hash, created_at) VALUES (?, ?, ?, ?)",
            (account_id, event, ip_hash, created_at),
        )


def as_dict(row, columns: tuple[str, ...]) -> dict:
    if isinstance(row, dict):
        return row
    keys = getattr(row, "keys", None)
    if callable(keys):
        return {key: row[key] for key in keys()}
    return dict(zip(columns, row, strict=False))


ACCOUNT_COLUMNS = (
    "id", "name", "cpf", "email", "birth_date", "phone", "postal_code", "state", "city",
    "password_hash", "status", "created_at", "income", "fixed_expenses", "goal", "completed_at",
    "goal_target_cents", "goal_current_cents", "goal_monthly_cents", "avatar_data",
)

TRANSACTION_COLUMNS = (
    "id", "account_id", "title", "amount_cents", "kind", "category", "channel",
    "occurred_on", "status", "payment_method", "merchant_doc", "confidence",
    "validated", "external_ref", "notes", "created_at",
)

LIMIT_COLUMNS = (
    "id", "account_id", "scope", "category", "limit_cents", "warn_percent", "created_at",
)


def transaction_from(row) -> Transaction:
    data = as_dict(row, TRANSACTION_COLUMNS)
    return Transaction(
        id=data["id"],
        account_id=data["account_id"],
        title=data["title"],
        amount_cents=int(data["amount_cents"]),
        kind=data["kind"],
        category=data["category"],
        channel=data["channel"],
        occurred_on=data["occurred_on"],
        status=data["status"],
        payment_method=data["payment_method"],
        merchant_doc=data.get("merchant_doc"),
        confidence=int(data["confidence"]) if data.get("confidence") is not None else None,
        validated=bool(data.get("validated", 1)),
        external_ref=data.get("external_ref"),
        notes=data.get("notes"),
        created_at=int(data["created_at"]),
    )


def limit_from(row) -> BudgetLimit:
    data = as_dict(row, LIMIT_COLUMNS)
    return BudgetLimit(
        id=data["id"],
        account_id=data["account_id"],
        scope=data["scope"],
        category=data["category"],
        limit_cents=int(data["limit_cents"]),
        warn_percent=int(data["warn_percent"]),
        created_at=int(data["created_at"]),
    )


class DjangoDb:
    def query(self, sql: str, params: tuple = (), columns: tuple[str, ...] | None = None) -> list[dict]:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(sql.replace("?", "%s"), params)
            rows = cursor.fetchall()
            description = getattr(cursor, "description", None)
            if description:
                names = tuple(column[0] for column in description)
                return [as_dict(row, names) for row in rows]
        return [as_dict(row, columns or ()) for row in rows]

    def execute(self, sql: str, params: tuple = ()) -> int:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(sql.replace("?", "%s"), params)
            return cursor.rowcount


class SqlLessons:
    def __init__(self, db: SqliteDb):
        self.db = db

    def list(self) -> list[dict]:
        return self.db.query(
            "SELECT id, title, description, body, minutes FROM lessons ORDER BY id",
            (),
            ("id", "title", "description", "body", "minutes"),
        )

    def list_progress(self, account_id: str) -> dict[str, int]:
        rows = self.db.query(
            "SELECT lesson_id, progress_percent FROM lesson_progress WHERE account_id = ?",
            (account_id,),
            ("lesson_id", "progress_percent"),
        )
        result: dict[str, int] = {}
        for row in rows:
            item = as_dict(row, ("lesson_id", "progress_percent"))
            result[item["lesson_id"]] = int(item["progress_percent"])
        return result

    def set_progress(self, account_id: str, lesson_id: str, progress_percent: int, updated_at: int) -> None:
        self.db.execute(
            """INSERT INTO lesson_progress(account_id, lesson_id, progress_percent, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(account_id, lesson_id) DO UPDATE SET
               progress_percent = excluded.progress_percent, updated_at = excluded.updated_at""",
            (account_id, lesson_id, progress_percent, updated_at),
        )


class SqlLedger:
    def __init__(self, db: SqliteDb, ids=None):
        self.db = db
        self.ids = ids or (lambda: str(uuid.uuid4()))

    def next_id(self) -> str:
        return self.ids()

    def list_transactions(self, account_id: str) -> list[Transaction]:
        rows = self.db.query(
            """SELECT id, account_id, title, amount_cents, kind, category, channel, occurred_on,
                      status, payment_method, merchant_doc, confidence, validated, external_ref, notes, created_at
               FROM transactions
               WHERE account_id = ?
               ORDER BY occurred_on DESC, created_at DESC, id DESC""",
            (account_id,),
            TRANSACTION_COLUMNS,
        )
        return [transaction_from(row) for row in rows]

    def find_transaction(self, account_id: str, tx_id: str) -> Transaction | None:
        rows = self.db.query(
            """SELECT id, account_id, title, amount_cents, kind, category, channel, occurred_on,
                      status, payment_method, merchant_doc, confidence, validated, external_ref, notes, created_at
               FROM transactions
               WHERE account_id = ? AND id = ?""",
            (account_id, tx_id),
            TRANSACTION_COLUMNS,
        )
        return transaction_from(rows[0]) if rows else None

    def has_external_ref(self, account_id: str, external_ref: str) -> bool:
        rows = self.db.query(
            "SELECT id FROM transactions WHERE account_id = ? AND external_ref = ? LIMIT 1",
            (account_id, external_ref),
            ("id",),
        )
        return bool(rows)

    def insert_transaction(self, tx: Transaction) -> Transaction:
        self.db.execute(
            """INSERT INTO transactions(
                 id, account_id, title, amount_cents, kind, category, channel, occurred_on,
                 status, payment_method, merchant_doc, confidence, validated, external_ref, notes, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tx.id, tx.account_id, tx.title, tx.amount_cents, tx.kind, tx.category, tx.channel,
                tx.occurred_on, tx.status, tx.payment_method, tx.merchant_doc, tx.confidence,
                1 if tx.validated else 0, tx.external_ref, tx.notes, tx.created_at,
            ),
        )
        return tx

    def update_transaction(self, tx: Transaction) -> Transaction:
        self.db.execute(
            """UPDATE transactions
               SET title = ?, amount_cents = ?, kind = ?, category = ?, channel = ?, occurred_on = ?,
                   status = ?, payment_method = ?, merchant_doc = ?, confidence = ?, validated = ?, notes = ?
               WHERE account_id = ? AND id = ?""",
            (
                tx.title, tx.amount_cents, tx.kind, tx.category, tx.channel, tx.occurred_on,
                tx.status, tx.payment_method, tx.merchant_doc, tx.confidence, 1 if tx.validated else 0,
                tx.notes, tx.account_id, tx.id,
            ),
        )
        return tx

    def delete_transaction(self, account_id: str, tx_id: str) -> bool:
        changed = self.db.execute(
            "DELETE FROM transactions WHERE account_id = ? AND id = ?",
            (account_id, tx_id),
        )
        return changed > 0

    def list_limits(self, account_id: str) -> list[BudgetLimit]:
        rows = self.db.query(
            """SELECT id, account_id, scope, category, limit_cents, warn_percent, created_at
               FROM budget_limits
               WHERE account_id = ?
               ORDER BY scope ASC, category ASC""",
            (account_id,),
            LIMIT_COLUMNS,
        )
        return [limit_from(row) for row in rows]

    def upsert_limit(self, limit: BudgetLimit) -> BudgetLimit:
        self.db.execute(
            """INSERT INTO budget_limits(id, account_id, scope, category, limit_cents, warn_percent, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(account_id, scope, category) DO UPDATE SET
               limit_cents = excluded.limit_cents, warn_percent = excluded.warn_percent""",
            (limit.id, limit.account_id, limit.scope, limit.category, limit.limit_cents, limit.warn_percent, limit.created_at),
        )
        rows = self.db.query(
            """SELECT id, account_id, scope, category, limit_cents, warn_percent, created_at
               FROM budget_limits
               WHERE account_id = ? AND scope = ? AND category = ?""",
            (limit.account_id, limit.scope, limit.category),
            LIMIT_COLUMNS,
        )
        return limit_from(rows[0]) if rows else limit

    def delete_limit(self, account_id: str, limit_id: str) -> bool:
        changed = self.db.execute(
            "DELETE FROM budget_limits WHERE account_id = ? AND id = ?",
            (account_id, limit_id),
        )
        return changed > 0
