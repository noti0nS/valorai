from collections.abc import Callable, Iterator


class MemoryKv:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def get(self, key: str) -> dict | None:
        value = self.rows.get(key)
        return None if value is None else dict(value)

    def put(self, key: str, value: dict) -> None:
        self.rows[key] = dict(value)

    def delete(self, key: str) -> None:
        self.rows.pop(key, None)

    def items(self) -> Iterator[tuple[str, dict]]:
        for key, value in list(self.rows.items()):
            yield key, dict(value)


class PrefixKv:
    """One prefix of a shared store. Callers only see their own keys."""

    def __init__(self, kv: MemoryKv, prefix: str):
        self.kv = kv
        self.prefix = prefix

    def get(self, item_id: str) -> dict | None:
        return self.kv.get(self.prefix + item_id)

    def put(self, item_id: str, value: dict) -> None:
        self.kv.put(self.prefix + item_id, value)

    def delete(self, item_id: str) -> None:
        self.kv.delete(self.prefix + item_id)

    def matching(self) -> Iterator[tuple[str, dict]]:
        for key, value in self.kv.items():
            if key.startswith(self.prefix):
                yield key[len(self.prefix):], value

    def prune(self, expired: Callable[[dict], bool]) -> None:
        for item_id, value in list(self.matching()):
            if expired(value):
                self.delete(item_id)
