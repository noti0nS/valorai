import sqlite3
import uuid
from dataclasses import dataclass, replace
from pathlib import Path

from valorai.records import Account


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


class MemoryLessons:
    def __init__(self, lessons: list[dict] | None = None):
        self.lessons = lessons or []

    def list(self) -> list[dict]:
        return sorted(self.lessons, key=lambda item: item["id"])


def connect_schema(path: Path | None = None) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    schema = path or Path(__file__).resolve().parents[2] / "migrations" / "0001_initial.sql"
    connection.executescript(schema.read_text(encoding="utf-8"))
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
    def __init__(self, db: SqliteDb):
        self.db = db

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
)


class DjangoDb:
    def query(self, sql: str, params: tuple = (), columns: tuple[str, ...] | None = None) -> list[dict]:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            description = getattr(cursor, "description", None)
            if description:
                names = tuple(column[0] for column in description)
                return [as_dict(row, names) for row in rows]
        return [as_dict(row, columns or ()) for row in rows]

    def execute(self, sql: str, params: tuple = ()) -> int:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
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
