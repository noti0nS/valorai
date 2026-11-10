from valorai.errors import ApiError
from valorai.kv import PrefixKv


class Throttle:
    def __init__(self, kv, clock):
        self.rates = PrefixKv(kv, "rate:")
        self.clock = clock

    def hit(self, ip_hash: str) -> None:
        now = self.clock.now()
        current = self.rates.get(ip_hash)
        if current is None or current["until"] <= now:
            nxt = {"count": 1, "until": now + 60}
        else:
            nxt = {"count": current["count"] + 1, "until": current["until"]}
        if nxt["count"] > 30:
            raise ApiError(429, "Muitas tentativas. Aguarde um minuto.")
        self.rates.put(ip_hash, nxt)

    def prune(self, now: int) -> None:
        self.rates.prune(lambda value: value["until"] <= now)
