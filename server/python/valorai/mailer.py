import json
from collections.abc import Callable

from valorai.errors import ApiError

HttpPost = Callable[[str, dict[str, str], str, float], tuple[int, str]]


class ResendMailer:
    """Sends confirmation and password-recovery codes through Resend's HTTP API."""

    def __init__(self, api_key: str | None, sender: str, http_post: HttpPost | None = None):
        self.api_key = api_key
        self.sender = sender
        self.http_post = http_post

    def send_code(self, to_email: str, code: str, purpose: str) -> None:
        if not self.api_key or self.http_post is None:
            raise ApiError(503, "Serviço de envio de e-mail não configurado.")
        if purpose == "recovery":
            subject = "Seu código de recuperação de senha — ValorAI"
            body = (
                f"Olá,\n\n"
                f"Use o código abaixo para redefinir sua senha no ValorAI (válido por 15 minutos):\n\n"
                f"    {code}\n\n"
                f"Se você não solicitou esta recuperação, ignore este e-mail."
            )
        else:
            subject = "Seu código de confirmação — ValorAI"
            body = (
                f"Olá,\n\n"
                f"Use o código abaixo para confirmar seu cadastro no ValorAI (válido por 10 minutos):\n\n"
                f"    {code}\n\n"
                f"Se você não criou uma conta, ignore este e-mail."
            )
        payload = json.dumps({
            "from": self.sender,
            "to": [to_email],
            "subject": subject,
            "text": body,
        })
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "valorai-worker/1.0",
        }
        try:
            status, _raw = self.http_post("https://api.resend.com/emails", headers, payload, 8.0)
        except Exception as err:
            raise ApiError(502, "Não foi possível enviar o e-mail agora. Tente novamente em instantes.") from err
        if status >= 400:
            raise ApiError(502, "Não foi possível enviar o e-mail agora. Tente novamente em instantes.")
