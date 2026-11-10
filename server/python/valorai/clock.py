from datetime import datetime, timezone


class FixedClock:
    def __init__(self, now: int):
        self.moment = now

    def now(self) -> int:
        return self.moment

    def today(self) -> datetime:
        return datetime.fromtimestamp(self.moment, timezone.utc)

    def advance(self, seconds: int) -> None:
        self.moment += seconds


class SystemClock:
    def now(self) -> int:
        return int(datetime.now(timezone.utc).timestamp())

    def today(self) -> datetime:
        return datetime.now(timezone.utc)
