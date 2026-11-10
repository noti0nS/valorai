from dataclasses import dataclass

from valorai.errors import ApiError
from valorai.kv import PrefixKv

CONFIRM_SECONDS = 10 * 60  # Prototype setting; RF002 limits remain pending approval.
MAX_ATTEMPTS = 5
RESEND_SECONDS = 60
MAX_SENDS = 3


@dataclass
class Challenge:
    code: str
    expires: int
    attempts: int
    sent_at: int
    hour: int
    sends: int

    def as_dict(self) -> dict:
        return {"code": self.code, "expires": self.expires, "attempts": self.attempts, "sentAt": self.sent_at, "hour": self.hour, "sends": self.sends}

    @classmethod
    def from_dict(cls, value: dict) -> "Challenge":
        return cls(str(value["code"]), int(value["expires"]), int(value["attempts"]), int(value["sentAt"]), int(value["hour"]), int(value["sends"]))


class ConfirmationModule:
    """Demo codes and their counters. The stored code is readable only through this module."""

    def __init__(self, kv, clock, numbers):
        self.codes = PrefixKv(kv, "code:")
        self.clock = clock
        self.numbers = numbers

    def limits(self) -> dict:
        return {"seconds": CONFIRM_SECONDS, "attempts": MAX_ATTEMPTS, "resendSeconds": RESEND_SECONDS}

    def issue(self, account_id: str) -> dict:
        previous = self._get(account_id)
        now = self.clock.now()
        if previous and previous.sent_at + RESEND_SECONDS > now:
            raise ApiError(429, "Aguarde 60 segundos entre envios.")
        same_hour = bool(previous and previous.hour + 3600 > now)
        if same_hour and previous is not None and previous.sends >= MAX_SENDS:
            raise ApiError(429, "Limite de três envios por hora atingido.")
        challenge = Challenge(
            code=f"{self.numbers() % 1000000:06d}", expires=now + CONFIRM_SECONDS, attempts=0, sent_at=now,
            hour=previous.hour if same_hour and previous else now, sends=previous.sends + 1 if same_hour and previous else 1,
        )
        self.codes.put(account_id, challenge.as_dict())
        return {"expiresAt": challenge.expires, "resendAt": challenge.sent_at + RESEND_SECONDS}

    def reveal(self, account) -> dict:
        if account.status != "pending":
            raise ApiError(409, "Essa etapa já foi concluída.")
        challenge = self._live(account.id, "Código expirado. Solicite outro código.")
        return {"code": challenge.code, "to": account.email, "expiresAt": challenge.expires, "simulated": True}

    def check(self, account, code: object) -> None:
        if account.status != "pending":
            raise ApiError(409, "Essa etapa já foi concluída.")
        challenge = self._live(account.id, "Código expirado ou bloqueado. Solicite outro.")
        if not isinstance(code, str) or len(code) != 6 or not code.isdigit() or code != challenge.code:
            challenge.attempts += 1
            self.codes.put(account.id, challenge.as_dict())
            if challenge.attempts >= MAX_ATTEMPTS:
                raise ApiError(400, "Limite de tentativas atingido. Solicite outro código.")
            raise ApiError(400, "Código incorreto. Confira os seis dígitos.")

    def discard(self, account_id: str) -> None:
        self.codes.delete(account_id)

    def prune(self, now: int) -> None:
        self.codes.prune(lambda value: value["hour"] + 3600 <= now)

    def _live(self, account_id: str, message: str) -> Challenge:
        challenge = self._get(account_id)
        if challenge is None or challenge.expires <= self.clock.now() or challenge.attempts >= MAX_ATTEMPTS:
            raise ApiError(410, message)
        return challenge

    def _get(self, account_id: str) -> Challenge | None:
        value = self.codes.get(account_id)
        return None if value is None else Challenge.from_dict(value)
