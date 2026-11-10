from dataclasses import dataclass

from valorai.crypto import sha256_hex
from valorai.errors import ApiError
from valorai.kv import PrefixKv
from valorai.records import Account, Registration


@dataclass
class Attempt:
    count: int
    window: int
    blocked_until: int

    def as_dict(self) -> dict:
        return {"count": self.count, "window": self.window, "blockedUntil": self.blocked_until}

    @classmethod
    def from_dict(cls, value: dict) -> "Attempt":
        return cls(int(value["count"]), int(value["window"]), int(value["blockedUntil"]))


class AccountModule:
    """Identity, password check, status, and deactivation. Hashing stays on the injected hasher."""

    def __init__(self, accounts, kv, hasher, clock, audit):
        self.accounts = accounts
        self.attempts = PrefixKv(kv, "login:")
        self.hasher = hasher
        self.clock = clock
        self.audit = audit

    def create(self, data: Registration, ip_hash: str) -> Account:
        if self.accounts.find_by_identity(data.email, data.cpf):
            raise ApiError(409, "Não foi possível criar uma nova conta com esses dados. Tente entrar na conta existente.")
        now = self.clock.now()
        account = Account(
            id=self.accounts.next_id(), name=data.name, email=data.email, cpf=data.cpf,
            password_hash=self.hasher.hash(data.password), status="pending", city=data.city, state=data.state,
            birth_date=data.birth_date, phone=data.phone, postal_code=data.postal_code, created_at=now,
        )
        try:
            self.accounts.insert(account)
        except LookupError:
            raise ApiError(409, "Não foi possível criar uma nova conta com esses dados. Tente entrar na conta existente.") from None
        self.audit.record(account.id, "registration_created", ip_hash, now)
        return account

    def authenticate(self, identifier: object, password: object, ip_hash: str) -> Account:
        text = identifier.strip().lower()[:200] if isinstance(identifier, str) else ""
        secret = password if isinstance(password, str) else ""
        if len(secret) > 32 or len(secret.encode()) > 72:
            raise ApiError(401, "Identificador ou senha inválidos.")
        account = self.accounts.find_for_login(text, "".join(character for character in text if character.isdigit()))
        key = account.id if account else sha256_hex(text)
        failure = self._attempt(key)
        now = self.clock.now()
        if failure and failure.blocked_until > now:
            raise ApiError(401, "Identificador ou senha inválidos. Se houve várias tentativas, aguarde cinco minutos.")
        if account:
            matches = self.hasher.verify(secret, account.password_hash)
        else:
            self.hasher.hash(secret or "invalid")
            matches = False
        if not account or not matches or account.status == "inactive":
            expired = failure is None or (failure.blocked_until > 0 and failure.blocked_until <= now) or failure.window + 900 <= now
            count = 1 if expired else failure.count + 1
            self.attempts.put(key, Attempt(count, now if expired else failure.window, now + 300 if count >= 5 else 0).as_dict())
            self.audit.record(account.id if account else None, "login_failed", ip_hash, now)
            raise ApiError(401, "Identificador ou senha inválidos.")
        self.attempts.delete(key)
        self.audit.record(account.id, "login_succeeded", ip_hash, now)
        return account

    def mark_demo_confirmed(self, account: Account, ip_hash: str) -> Account:
        updated = self.accounts.mark_demo_confirmed(account.id)
        if updated is None:
            raise ApiError(409, "Essa etapa já foi concluída.")
        self.audit.record(account.id, "demo_confirmation_completed", ip_hash, self.clock.now())
        return updated

    def deactivate(self, account: Account, password: object, sessions, confirmation, ip_hash: str) -> None:
        """Status, then sessions, then the confirmation code, then the audit event.

        These writes cannot roll back: the D1 backend treats atomic blocks as no-ops.
        """
        secret = password if isinstance(password, str) else ""
        if len(secret) > 32 or not self.hasher.verify(secret, account.password_hash):
            raise ApiError(400, "Confira sua senha para confirmar a desativação.")
        self.accounts.deactivate(account.id)
        sessions.revoke_all(account.id)
        confirmation.discard(account.id)
        self.audit.record(account.id, "account_deactivated", ip_hash, self.clock.now())

    def prune(self, now: int) -> None:
        self.attempts.prune(lambda value: value["window"] + 900 <= now and value["blockedUntil"] <= now)

    def _attempt(self, key: str) -> Attempt | None:
        value = self.attempts.get(key)
        return None if value is None else Attempt.from_dict(value)
