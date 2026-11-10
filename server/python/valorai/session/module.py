import re

from valorai.crypto import sha256_hex
from valorai.errors import ApiError

SESSION_SECONDS = 12 * 60 * 60
IDLE_SECONDS = 1800
COOKIE = re.compile(r"(?:^|;\s*)valorai_session=([a-f0-9]{64})(?:;|$)")


def session_cookie(token: str, max_age: int, secure: bool) -> str:
    cookie = f"valorai_session={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age}"
    return cookie + "; Secure" if secure else cookie


class SessionModule:
    def __init__(self, sessions, accounts, clock, tokens):
        self.sessions = sessions
        self.accounts = accounts
        self.clock = clock
        self.tokens = tokens

    def read(self, cookie_header: str | None, *, confirmed: bool = False):
        match = COOKIE.search(cookie_header or "")
        if not match:
            raise ApiError(401, "Entre na sua conta para continuar.")
        token_hash = sha256_hex(match.group(1))
        now = self.clock.now()
        session = self.sessions.find(token_hash)
        if session is None or session.expires_at <= now or session.last_seen <= now - IDLE_SECONDS:
            if session is not None:
                self.sessions.delete(token_hash)
            raise ApiError(401, "Sua sessão expirou. Entre novamente para continuar.")
        account = self.accounts.find_by_id(session.account_id)
        if account is None or account.status == "inactive":
            raise ApiError(401, "Entre na sua conta para continuar.")
        if confirmed and account.status != "demo_confirmed":
            raise ApiError(403, "Conclua a confirmação de demonstração primeiro.")
        self.sessions.touch(token_hash, now)
        return account, token_hash

    def start(self, account_id: str, *, secure: bool) -> str:
        token = self.tokens()
        now = self.clock.now()
        self.sessions.insert(sha256_hex(token), account_id, now, now, now + SESSION_SECONDS)
        return session_cookie(token, SESSION_SECONDS, secure)

    def clear(self, token_hash: str) -> None:
        self.sessions.delete(token_hash)

    def revoke_all(self, account_id: str) -> None:
        self.sessions.revoke_all(account_id)

    def delete_expired(self, now: int) -> None:
        self.sessions.delete_expired(now)

    def cookie_header(self, request_is_secure: bool) -> str:
        return session_cookie("", 0, request_is_secure)
