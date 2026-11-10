from urllib.parse import urlparse

from valorai.crypto import header, sha256_hex
from valorai.errors import ApiError
from valorai.finance.module import FinanceModule
from valorai.ledger.module import LedgerModule
from valorai.storage import MemoryLedger

LARGE_BODY_PATHS = {"/api/profile", "/api/transactions/import", "/api/transactions/receipt"}


def admit(method: str, path: str, origin: str | None, target_origin: str):
    if not path.startswith("/api/"):
        return None
    if method == "POST" and origin != target_origin:
        return _fail(ApiError(403, "Origem não autorizada."))
    if method not in {"GET", "POST"}:
        return _fail(ApiError(405, "Método não permitido."))
    return None


class Result:
    def __init__(self, status: int, body: dict, headers: dict[str, str]):
        self.status = status
        self.body = body
        self.headers = headers


def _headers(set_cookie: str | None = None) -> dict[str, str]:
    headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    if set_cookie is not None:
        headers["Set-Cookie"] = set_cookie
    return headers


def _ok(body: dict, status: int = 200, set_cookie: str | None = None) -> Result:
    return Result(status, body, _headers(set_cookie))


def _fail(error: ApiError) -> Result:
    body: dict = {"error": str(error)}
    if error.fields is not None:
        body["fields"] = error.fields
    return Result(error.status, body, _headers())


def public_account(account, finance: FinanceModule) -> dict:
    return {
        "id": account.id, "name": account.name, "email": account.email, "city": account.city, "state": account.state,
        "status": account.status, "finance": finance.present(account), "completed": bool(account.completed_at),
        "emailVerified": False, "demoConfirmed": account.status == "demo_confirmed",
        "avatar": account.avatar_data,
    }


class RegistrationApi:
    def __init__(self, account, session, confirmation, finance, throttle, lessons, bot, clock, site_key: str, email_mode: str, log=None, ledger=None):
        self.account = account
        self.session = session
        self.confirmation = confirmation
        self.finance = finance
        self.throttle = throttle
        self.lessons = lessons
        self.bot = bot
        self.clock = clock
        self.site_key = site_key
        self.email_mode = email_mode
        self.log = log or (lambda: None)
        self.ledger = ledger or LedgerModule(MemoryLedger(), account.accounts, lessons, clock, account.audit)

    def handle(self, method: str, url: str, headers: dict[str, str], body: bytes) -> Result:
        try:
            return self._handle(method, url, headers, body)
        except ApiError as error:
            return _fail(error)
        except Exception:
            self.log()
            return _fail(ApiError(500, "Não foi possível concluir agora. Tente novamente em instantes."))

    def _handle(self, method: str, url: str, headers: dict[str, str], body: bytes) -> Result:
        parsed = urlparse(url)
        path = parsed.path
        secure = parsed.scheme == "https"
        ip_hash = sha256_hex(header(headers, "cf-connecting-ip") or "local")
        if method == "GET" and path == "/api/config":
            return _ok({"emailMode": "demo", "siteKey": self.site_key, "confirmation": self.confirmation.limits(), "prototype": True})
        if method == "GET" and path == "/api/session":
            account, _hash = self.session.read(header(headers, "cookie"))
            return _ok({"account": public_account(account, self.finance)})
        if method == "GET" and path == "/api/lessons":
            self.session.read(header(headers, "cookie"), confirmed=True)
            return _ok({"lessons": self.lessons.list()})
        if method == "GET" and path == "/api/dashboard":
            account, _hash = self.session.read(header(headers, "cookie"), confirmed=True)
            return _ok({
                "account": public_account(account, self.finance),
                "profile": self.account.present_profile(account),
                "dashboard": self.ledger.present_dashboard(account),
            })
        if method == "GET" and path == "/api/demo-inbox":
            if self.email_mode != "demo":
                raise ApiError(404, "Indisponível.")
            account, _hash = self.session.read(header(headers, "cookie"))
            return _ok(self.confirmation.reveal(account))
        if method != "POST":
            raise ApiError(404, "Página não encontrada.")
        self.throttle.hit(ip_hash)
        max_bytes = 3_145_728 if path in LARGE_BODY_PATHS else 16384
        payload = _read_body(header(headers, "content-type"), body, max_bytes=max_bytes)
        if path == "/api/register":
            from valorai.account.validation import registration_from
            data = registration_from(payload, self.clock.today())
            self.bot.check(payload, parsed.hostname, header(headers, "cf-connecting-ip") or "")
            created = self.account.create(data, ip_hash)
            timing = self.confirmation.issue(created.id)
            cookie = self.session.start(created.id, secure=secure)
            return _ok({"account": public_account(created, self.finance), **timing}, 201, cookie)
        if path == "/api/login":
            self.bot.check(payload, parsed.hostname, header(headers, "cf-connecting-ip") or "")
            account = self.account.authenticate(payload.get("identifier"), payload.get("password"), ip_hash)
            return _ok({"account": public_account(account, self.finance)}, 200, self.session.start(account.id, secure=secure))
        account, token_hash = self.session.read(header(headers, "cookie"))
        if path == "/api/logout":
            self.session.clear(token_hash)
            return _ok({"ok": True}, 200, self.session.cookie_header(secure))
        if path == "/api/resend":
            if account.status != "pending":
                raise ApiError(409, "Essa etapa já foi concluída.")
            return _ok(self.confirmation.issue(account.id))
        if path == "/api/confirm":
            self.confirmation.check(account, payload.get("code"))
            confirmed = self.account.mark_demo_confirmed(account, ip_hash)
            self.confirmation.discard(account.id)
            self.session.revoke_all(account.id)
            return _ok({"account": public_account(confirmed, self.finance)}, 200, self.session.start(account.id, secure=secure))
        if account.status != "demo_confirmed":
            raise ApiError(403, "Conclua a confirmação de demonstração primeiro.")
        if path == "/api/finance":
            updated = self.finance.update(account, payload, ip_hash)
            return _ok({"account": public_account(updated, self.finance), "dashboard": self.ledger.present_dashboard(updated)})
        if path == "/api/profile":
            updated = self.account.update_profile(account, payload, ip_hash)
            return _ok({
                "account": public_account(updated, self.finance),
                "profile": self.account.present_profile(updated),
            })
        if path == "/api/transactions":
            return _ok({"dashboard": self.ledger.handle_transaction(account, payload, ip_hash)})
        if path == "/api/transactions/import":
            result = self.ledger.handle_import(account, payload, ip_hash)
            if result.get("preview"):
                return _ok(result)
            return _ok({"dashboard": result, "importResult": result.get("importResult")})
        if path == "/api/transactions/receipt":
            result = self.ledger.handle_receipt(account, payload, ip_hash)
            if "extracted" in result:
                return _ok(result)
            return _ok({"dashboard": result})
        if path == "/api/limits":
            return _ok({"dashboard": self.ledger.handle_limit(account, payload, ip_hash)})
        if path == "/api/goal":
            updated, dashboard = self.ledger.handle_goal(account, payload, ip_hash)
            return _ok({"account": public_account(updated, self.finance), "dashboard": dashboard})
        if path == "/api/lessons/progress":
            return _ok({"dashboard": self.ledger.handle_lesson_progress(account, payload, ip_hash)})
        if path == "/api/deactivate":
            self.account.deactivate(account, payload.get("password"), self.session, self.confirmation, ip_hash)
            return _ok({"ok": True}, 200, self.session.cookie_header(secure))
        raise ApiError(404, "Operação não encontrada.")


def _read_body(content_type: str | None, body: bytes, max_bytes: int = 16384) -> dict:
    if content_type is None or "application/json" not in content_type:
        raise ApiError(415, "Envie dados em JSON.")
    if not body:
        raise ApiError(400, "Dados ausentes.")
    if len(body) > max_bytes:
        raise ApiError(413, "O formulário excedeu o tamanho permitido.")
    import json
    try:
        value = json.loads(body)
    except json.JSONDecodeError:
        raise ApiError(400, "Não foi possível ler o formulário.") from None
    if not isinstance(value, dict):
        raise ApiError(400, "Não foi possível ler o formulário.")
    return value
