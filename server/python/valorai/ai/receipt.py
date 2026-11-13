"""Multimodal payment receipt/invoice extraction using an OpenAI-Compatible VLM."""

from collections.abc import Callable

from valorai.ai.client import AiProviderError, AiRateLimitError, OpenAiCompatibleClient
from valorai.records import PaymentMethod, TransactionKind

CIRCUIT_BREAKER_KEY = "ai:circuit_open_until"
CIRCUIT_COOLDOWN_SECONDS = 60

RECEIPT_SYSTEM_PROMPT = (
    "Você é um extrator financeiro brasileiro de alta precisão para o aplicativo ValorAI. "
    "Sua tarefa é ler a imagem (foto ou print) de qualquer comprovante financeiro brasileiro — "
    "incluindo cupom fiscal (NFC-e/SAT), comprovante PIX (enviado ou recebido), boleto bancário, "
    "fatura de cartão de crédito, TED/DOC ou recibo de maquininha — e retornar apenas JSON estruturado.\n\n"
    "Regras obrigatórias:\n"
    "1. VALOR (amount): Em documentos com múltiplos valores, priorize sempre o VALOR EFETIVAMENTE PAGO "
    "(ou o VALOR TOTAL da fatura/documento caso ainda não esteja quitado). Nunca use subtotal, limite disponível, "
    "pagamento mínimo da fatura ou valor de parcela isolada como valor principal.\n"
    "2. TIPO (kind): Use 'income' apenas se for claramente um PIX/transferência RECEBIDA ou crédito em conta. "
    "Use 'fixed_expense' para contas recorrentes (aluguel, energia, água, internet, telefone, condomínio, seguro). "
    "Use 'variable_expense' para compras, mercado, restaurante, transporte, farmácia e demais pagamentos.\n"
    "3. CATEGORIA (category): Escolha EXATAMENTE uma das categorias permitidas.\n"
    "4. FORMA DE PAGAMENTO (paymentMethod): Escolha EXATAMENTE entre pix, credit, debit, cash, boleto, transfer.\n"
    "5. DATA (occurredOn): Formato YYYY-MM-DD. Se não estiver legível na imagem, use a data de referência informada.\n"
    "6. ESTABELECIMENTO/TÍTULO (title): Nome curto e claro do estabelecimento, recebedor ou emissor (máx. 80 caracteres)."
)


def build_receipt_schema(categories: tuple[str, ...]) -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "amount": {"type": "number"},
            "kind": {"type": "string", "enum": [k.value for k in TransactionKind]},
            "category": {"type": "string", "enum": list(categories)},
            "occurredOn": {"type": "string"},
            "paymentMethod": {"type": "string", "enum": [m.value for m in PaymentMethod]},
            "merchantDoc": {"type": "string"},
            "confidence": {"type": "integer"},
        },
        "required": ["title", "amount", "kind", "category", "occurredOn", "paymentMethod", "merchantDoc", "confidence"],
    }


class AiReceiptExtractor:
    """Extracts structured transaction fields from receipt/payment images with deterministic fallback."""

    def __init__(self, client: OpenAiCompatibleClient | None = None, kv=None, clock=None):
        self.client = client
        self.kv = kv
        self.clock = clock

    def _circuit_open(self) -> bool:
        if self.kv is None or self.clock is None:
            return False
        state = self.kv.get(CIRCUIT_BREAKER_KEY)
        return bool(state and int(state.get("until", 0)) > int(self.clock.now()))

    def _trip_circuit(self) -> None:
        if self.kv is None or self.clock is None:
            return
        self.kv.put(CIRCUIT_BREAKER_KEY, {"until": int(self.clock.now()) + CIRCUIT_COOLDOWN_SECONDS})

    def extract(
        self,
        *,
        file_name: str,
        text_hint: str,
        image_data_url: str | None,
        today_iso: str,
        categories: tuple[str, ...],
        standard_category_fn: Callable[[object], str | None],
        suggest_category_fn: Callable[[str, str | None], tuple[str, str]],
        valid_iso_date_fn: Callable[[object], str | None],
        fallback_fn: Callable[[], dict],
    ) -> dict:
        if (
            self.client is None
            or not self.client.is_configured()
            or not image_data_url
            or not image_data_url.startswith("data:image/")
            or self._circuit_open()
        ):
            reason = "rate_limit" if self._circuit_open() else "demo_or_no_image"
            return {**fallback_fn(), "source": "fallback", "fallbackReason": reason}

        user_text = (
            f"Data de referência (hoje): {today_iso}.\n"
            f"Nome do arquivo: {file_name}.\n"
            f"Categorias permitidas: {', '.join(categories)}.\n"
        )
        if text_hint:
            user_text += f"Observação do usuário: {text_hint}\n"
        user_text += "Extraia os campos da transação a partir da imagem."

        messages = [
            {"role": "system", "content": RECEIPT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": image_data_url, "detail": "low"}},
                ],
            },
        ]

        try:
            raw = self.client.chat_json(
                messages,
                json_schema=build_receipt_schema(categories),
                schema_name="receipt_extraction",
                timeout_s=8.0,
            )
            return self._normalize(
                raw,
                today_iso=today_iso,
                standard_category_fn=standard_category_fn,
                suggest_category_fn=suggest_category_fn,
                valid_iso_date_fn=valid_iso_date_fn,
                fallback_fn=fallback_fn,
            )
        except AiRateLimitError:
            self._trip_circuit()
            return {**fallback_fn(), "source": "fallback", "fallbackReason": "rate_limit"}
        except (AiProviderError, Exception):
            return {**fallback_fn(), "source": "fallback", "fallbackReason": "unavailable"}

    def _normalize(
        self,
        raw: dict,
        *,
        today_iso: str,
        standard_category_fn: Callable[[object], str | None],
        suggest_category_fn: Callable[[str, str | None], tuple[str, str]],
        valid_iso_date_fn: Callable[[object], str | None],
        fallback_fn: Callable[[], dict],
    ) -> dict:
        try:
            amount = round(float(raw.get("amount", 0)), 2)
        except (TypeError, ValueError):
            amount = 0.0
        if amount <= 0:
            return {**fallback_fn(), "source": "fallback", "fallbackReason": "invalid_amount"}

        title = str(raw.get("title") or "").strip()[:80] or "Comprovante Fiscal"
        kind_raw = str(raw.get("kind") or "variable_expense").strip()
        valid_kinds = {k.value for k in TransactionKind}
        kind = kind_raw if kind_raw in valid_kinds else "variable_expense"

        category = standard_category_fn(raw.get("category"))
        if category is None:
            category, kind = suggest_category_fn(title, kind)

        occurred_on = valid_iso_date_fn(raw.get("occurredOn")) or today_iso
        method_raw = str(raw.get("paymentMethod") or "pix").strip().lower()
        valid_methods = {m.value for m in PaymentMethod}
        payment_method = method_raw if method_raw in valid_methods else "pix"

        merchant_doc = str(raw.get("merchantDoc") or "").strip()[:120] or "Extraído via IA"
        try:
            confidence = max(1, min(100, int(raw.get("confidence", 85))))
        except (TypeError, ValueError):
            confidence = 85

        return {
            "title": title,
            "amount": amount,
            "kind": kind,
            "category": category,
            "occurredOn": occurred_on,
            "paymentMethod": payment_method,
            "merchantDoc": merchant_doc,
            "confidence": confidence,
            "source": "ai",
        }
