import hashlib


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def header(headers: dict[str, str], name: str) -> str | None:
    folded = name.lower()
    for key, value in headers.items():
        if key.lower() == folded:
            return value
    return None
