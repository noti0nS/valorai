"""Worker entrypoint. Auth requests still enter the accounts-v1 coordinator, which owns bcrypt.

The Python Workers CPU measurement is not written yet, so Account does not hash on its own.
"""

import os
import sys
import types
from pathlib import Path

# pywrangler treats this file's directory as the module root, so the package name is not on the path.
_package_root = str(Path(__file__).resolve().parent)
if _package_root not in sys.path:
    sys.path.insert(0, _package_root)
if "valorai" not in sys.modules:
    _package = types.ModuleType("valorai")
    _package.__path__ = [_package_root]
    _package.__package__ = "valorai"
    sys.modules["valorai"] = _package

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "valorai.django_settings")

from django.core.wsgi import get_wsgi_application
from workers import DurableObject, WorkerEntrypoint, wsgi

from valorai.account.module import AccountModule
from valorai.clock import SystemClock
from valorai.confirmation.module import ConfirmationModule
from valorai.coordinator.hasher import BcryptHasher
from valorai.finance.module import FinanceModule
from valorai.http import RegistrationApi, admit
from valorai.ledger.module import LedgerModule
from valorai.runtime import api_context
from valorai.session.module import SessionModule
from valorai.storage import DjangoDb, SqlAccounts, SqlAudit, SqlLedger, SqlLessons, SqlSessions
from valorai.throttle import Throttle
from valorai.turnstile import Turnstile

application = get_wsgi_application()


def json_result(result):
    import json
    from workers import Response
    return Response(json.dumps(result.body, ensure_ascii=False), status=result.status, headers=dict(result.headers))
HASHER = BcryptHasher()


def build_api(storage, env) -> RegistrationApi:
    db = DjangoDb()
    clock = SystemClock()
    kv = DurableKv(storage)
    bot = Turnstile(env.ENVIRONMENT, getattr(env, "TURNSTILE_SECRET_KEY", None), turnstile_verify)
    accounts = SqlAccounts(db)
    audit = SqlAudit(db)
    lessons = SqlLessons(db)
    return RegistrationApi(
        AccountModule(accounts, kv, HASHER, clock, audit),
        SessionModule(SqlSessions(db), accounts, clock, _tokens),
        ConfirmationModule(kv, clock, _code_number),
        FinanceModule(accounts, clock, audit),
        Throttle(kv, clock),
        lessons,
        bot,
        clock,
        getattr(env, "TURNSTILE_SITE_KEY", "") or "",
        getattr(env, "EMAIL_MODE", "demo"),
        log=lambda: print("authentication_request_failed"),
        ledger=LedgerModule(SqlLedger(db), accounts, lessons, clock, audit),
    )


class DurableKv:
    """Synchronous key store on the coordinator's SQLite. Django's WSGI path cannot await."""

    def __init__(self, storage):
        self.sql = storage.sql
        self.sql.exec("CREATE TABLE IF NOT EXISTS module_kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

    def get(self, key: str):
        import json
        rows = _sql_rows(self.sql.exec("SELECT value FROM module_kv WHERE key = ?", key))
        if not rows:
            return None
        raw = _cell(rows[0], "value")
        return json.loads(raw)

    def put(self, key: str, value: dict) -> None:
        import json
        self.sql.exec(
            "INSERT INTO module_kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            key,
            json.dumps(value),
        )

    def delete(self, key: str) -> None:
        self.sql.exec("DELETE FROM module_kv WHERE key = ?", key)

    def items(self):
        import json
        rows = _sql_rows(self.sql.exec("SELECT key, value FROM module_kv"))
        for row in rows:
            yield _cell(row, "key"), json.loads(_cell(row, "value"))


def _sql_rows(cursor):
    rows = cursor.toArray()
    if hasattr(rows, "to_py"):
        rows = rows.to_py()
    return list(rows)


def _cell(row, name: str):
    if isinstance(row, dict):
        return row[name]
    try:
        return row[name]
    except Exception:
        return getattr(row, name)


class AuthCoordinator(DurableObject):
    def __init__(self, ctx, env):
        super().__init__(ctx, env)
        self.hasher = HASHER

    async def fetch(self, request):
        import traceback
        token = api_context.set(build_api(self.ctx.storage, self.env))
        try:
            return await wsgi.fetch(application, request, self.env)
        except Exception:
            traceback.print_exc()
            raise
        finally:
            api_context.reset(token)

    async def alarm(self):
        api = build_api(self.ctx.storage, self.env)
        now = api.clock.now()
        api.confirmation.prune(now)
        api.account.prune(now)
        api.throttle.prune(now)
        api.session.delete_expired(now)


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = request.url if isinstance(request.url, str) else str(request.url)
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not parsed.path.startswith("/api/"):
            return await self.env.ASSETS.fetch(request)
        origin = request.headers.get("Origin") if hasattr(request.headers, "get") else None
        decision = admit(request.method, parsed.path, origin, f"{parsed.scheme}://{parsed.netloc}")
        if decision is not None:
            return json_result(decision)
        try:
            stub = self.env.AUTH.get(self.env.AUTH.idFromName("accounts-v1"))
            return await stub.fetch(request)
        except Exception:
            return json_result_error()


def json_result_error():
    from valorai.errors import ApiError
    from valorai.http import _fail
    return json_result(_fail(ApiError(503, "Serviço temporariamente indisponível. Tente novamente.")))


def _tokens() -> str:
    import uuid
    return uuid.uuid4().hex + uuid.uuid4().hex


def _code_number() -> int:
    import secrets
    return secrets.randbelow(1_000_000)


def turnstile_verify(secret: str, token: str, remote_ip: str) -> dict:
    import json
    from urllib.request import Request, urlopen
    payload = f"secret={secret}&response={token}&remoteip={remote_ip}".encode()
    request = Request("https://challenges.cloudflare.com/turnstile/v0/siteverify", data=payload, method="POST")
    with urlopen(request, timeout=10) as response:
        return json.load(response)
