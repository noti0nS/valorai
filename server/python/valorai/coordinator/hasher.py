import time

import bcrypt

_measured = False


class BcryptHasher:
    """Lives with the accounts-v1 coordinator. Account receives this object and does not import bcrypt."""

    def hash(self, password: str) -> str:
        global _measured
        started = time.perf_counter()
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()
        if not _measured:
            _measured = True
            print(f"bcrypt_cost_10_ms={(time.perf_counter() - started) * 1000:.1f}")
        return hashed

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except ValueError:
            return False
