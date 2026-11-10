from valorai.errors import ApiError


class Turnstile:
    def __init__(self, environment: str, secret: str | None, verify):
        self.environment = environment
        self.secret = secret
        self.verify = verify

    def check(self, body: dict, hostname: str, remote_ip: str) -> None:
        if self.environment == "development":
            return
        if not self.secret:
            raise ApiError(503, "A proteção do protótipo está sendo configurada.")
        token = body.get("turnstileToken")
        result = self.verify(self.secret, token if isinstance(token, str) else "", remote_ip)
        if not result.get("success") or result.get("hostname") != hostname:
            raise ApiError(400, "Confirme a verificação de segurança e tente novamente.")
