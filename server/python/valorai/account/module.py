from dataclasses import dataclass

from valorai.account.validation import profile_update_from
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


def mask_cpf(cpf: str) -> str:
    if len(cpf) != 11:
        return cpf
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def mask_phone(phone: str) -> str:
    if len(phone) == 11:
        return f"({phone[:2]}) {phone[2:7]}-{phone[7:]}"
    return phone


def mask_postal(postal: str) -> str:
    if len(postal) == 8:
        return f"{postal[:5]}-{postal[5:]}"
    return postal


class AccountModule:
    """Identity, password check, status, profile maintenance, and deactivation. Hashing stays on the injected hasher."""

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
        return updated

    def update_profile(self, account: Account, payload: dict, ip_hash: str) -> Account:
        if not isinstance(payload, dict):
            raise ApiError(400, "Não foi possível ler o formulário.")
        update = profile_update_from(payload, self.clock.today(), account.cpf)
        changed: list[str] = []
        if update.name != account.name:
            changed.append("nome")
        if update.birth_date != account.birth_date:
            changed.append("data de nascimento")
        if update.phone != account.phone:
            changed.append("celular")
        if update.postal_code != account.postal_code:
            changed.append("CEP")
        if update.state != account.state:
            changed.append("UF")
        if update.city != account.city:
            changed.append("cidade")
        if not update.keep_avatar and update.avatar_data != account.avatar_data:
            changed.append("avatar")
        now = self.clock.now()
        updated = self.accounts.update_profile(account.id, update, changed, now)
        return updated

    def present_profile(self, account: Account) -> dict:
        return {
            "name": account.name,
            "cpf": mask_cpf(account.cpf),
            "email": account.email,
            "birthDate": account.birth_date,
            "phone": mask_phone(account.phone),
            "postalCode": mask_postal(account.postal_code),
            "state": account.state,
            "city": account.city,
            "avatar": account.avatar_data,
            "history": self.accounts.list_profile_changes(account.id),
        }

    def deactivate(self, account: Account, password: object, sessions, confirmation, ip_hash: str) -> None:
        """Status (the audit event comes from a database trigger), then sessions, then the confirmation code.

        These writes cannot roll back: the D1 backend treats atomic blocks as no-ops.
        """
        secret = password if isinstance(password, str) else ""
        if len(secret) > 32 or not self.hasher.verify(secret, account.password_hash):
            raise ApiError(400, "Confira sua senha para confirmar a desativação.")
        self.accounts.deactivate(account.id)
        sessions.revoke_all(account.id)
        confirmation.discard(account.id)

    def prune(self, now: int) -> None:
        self.attempts.prune(lambda value: value["window"] + 900 <= now and value["blockedUntil"] <= now)

    def _attempt(self, key: str) -> Attempt | None:
        value = self.attempts.get(key)
        return None if value is None else Attempt.from_dict(value)
