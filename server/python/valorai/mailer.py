import html
import json
from collections.abc import Callable

from valorai.errors import ApiError

HttpPost = Callable[[str, dict[str, str], str, float], tuple[int, str]]


def _render_code_email(code: str, purpose: str) -> tuple[str, str, str]:
    safe_code = html.escape(code)
    if purpose == "recovery":
        subject = "Seu código de recuperação de senha — ValorAI"
        eyebrow = "Recuperação de acesso"
        heading = "Redefina sua senha"
        intro = "Recebemos uma solicitação para redefinir a senha da sua conta no ValorAI. Use o código abaixo para continuar:"
        ttl_note = "Este código é válido por 15 minutos e de uso único."
        ignore_note = "Se você não solicitou esta recuperação, ignore este e-mail com segurança — sua senha atual permanece inalterada."
    else:
        subject = "Seu código de confirmação — ValorAI"
        eyebrow = "Verificação de cadastro"
        heading = "Confirme seu e-mail"
        intro = "Falta só um passo para liberar seu espaço financeiro no ValorAI. Digite o código abaixo na tela de confirmação:"
        ttl_note = "Este código é válido por 10 minutos e de uso único."
        ignore_note = "Se você não criou uma conta no ValorAI, ignore este e-mail."

    text = f"{heading}\n\n{intro}\n\n    {code}\n\n{ttl_note}\n{ignore_note}\n\nValorAI · Nulfinance Inc."
    body_html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{html.escape(subject)}</title>
</head>
<body style="margin:0;padding:0;background-color:#F7F6F2;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#14281D;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#F7F6F2;padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;background-color:#FFFFFF;border:1px solid #E5E3DC;border-radius:18px;overflow:hidden;">
          <tr>
            <td style="background-color:#14281D;padding:24px 28px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td>
                    <span style="display:inline-block;font-size:20px;font-weight:700;letter-spacing:-0.02em;color:#FFFFFF;">Valor<span style="color:#7E9F8C;">AI</span></span>
                  </td>
                  <td align="right" style="font-size:12px;color:#B9C9BF;letter-spacing:0.04em;text-transform:uppercase;">
                    {html.escape(eyebrow)}
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 28px 24px;">
              <h1 style="margin:0 0 12px;font-size:22px;line-height:1.25;font-weight:700;color:#14281D;">{html.escape(heading)}</h1>
              <p style="margin:0 0 24px;font-size:15px;line-height:1.55;color:#445049;">{html.escape(intro)}</p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td align="center" style="background-color:#F2F6F3;border:1px dashed #7E9F8C;border-radius:14px;padding:20px 16px;">
                    <span style="font-family:ui-monospace,'Cascadia Mono',Consolas,monospace;font-size:34px;font-weight:700;letter-spacing:0.28em;color:#14281D;padding-left:0.28em;">{safe_code}</span>
                  </td>
                </tr>
              </table>
              <p style="margin:20px 0 8px;font-size:13px;line-height:1.5;color:#525A55;">&#9201; {html.escape(ttl_note)}</p>
              <p style="margin:0;font-size:13px;line-height:1.5;color:#767E79;">{html.escape(ignore_note)}</p>
            </td>
          </tr>
          <tr>
            <td style="background-color:#FAF9F6;border-top:1px solid #ECEAE3;padding:16px 28px;font-size:12px;color:#767E79;">
              ValorAI · Gestão Financeira Pessoal · Nulfinance Inc.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    return subject, text, body_html


class ResendMailer:
    """Sends confirmation and password-recovery codes through Resend's HTTP API."""

    def __init__(self, api_key: str | None, sender: str, http_post: HttpPost | None = None):
        self.api_key = api_key
        self.sender = sender
        self.http_post = http_post

    def send_code(self, to_email: str, code: str, purpose: str) -> None:
        if not self.api_key or self.http_post is None:
            raise ApiError(503, "Serviço de envio de e-mail não configurado.")
        subject, text, body_html = _render_code_email(code, purpose)
        payload = json.dumps({
            "from": self.sender,
            "to": [to_email],
            "subject": subject,
            "text": text,
            "html": body_html,
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
