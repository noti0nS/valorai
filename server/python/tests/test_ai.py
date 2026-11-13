import json

from test_account import registration
from test_http import cookie_of, post

from valorai.ai import (
    AiConfig,
    AiProviderError,
    AiRateLimitError,
    AiReceiptExtractor,
    FinancialAdvisor,
    OpenAiCompatibleClient,
    compute_deterministic_context,
)
from valorai.http import RegistrationApi
from valorai.ledger.module import STANDARD_CATEGORIES, LedgerModule, suggest_category, standard_category, valid_iso_date


def _ok_openai_body(payload: dict) -> str:
    return json.dumps({"choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}]})


def test_openai_compatible_client_parses_json_and_strips_fences():
    captured = {}

    def fake_post(url, headers, body, timeout_s):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = json.loads(body)
        return 200, json.dumps({"choices": [{"message": {"content": '```json\n{"ok": true, "value": 42}\n```'}}]})

    cfg = AiConfig(mode="openai_compatible", base_url="https://example.test/v1/", api_key="secret", model="gemini-3.5-flash-lite")
    client = OpenAiCompatibleClient(cfg, http_post=fake_post)
    out = client.chat_json([{"role": "user", "content": "hi"}], json_schema={"type": "object"}, schema_name="test")

    assert out == {"ok": True, "value": 42}
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["body"]["model"] == "gemini-3.5-flash-lite"
    assert captured["body"]["response_format"]["type"] == "json_schema"


def test_openai_compatible_client_raises_on_429_and_500():
    cfg = AiConfig(mode="openai_compatible", base_url="https://example.test/v1", api_key="secret")

    client_429 = OpenAiCompatibleClient(cfg, http_post=lambda *_: (429, "rate limit"))
    try:
        client_429.chat_json([{"role": "user", "content": "hi"}])
        assert False, "Expected AiRateLimitError"
    except AiRateLimitError:
        pass

    client_500 = OpenAiCompatibleClient(cfg, http_post=lambda *_: (500, "boom"))
    try:
        client_500.chat_json([{"role": "user", "content": "hi"}])
        assert False, "Expected AiProviderError"
    except AiProviderError:
        pass


def test_receipt_extractor_handles_boleto_fatura_pix_and_sanitizes_category(world):
    responses = [
        _ok_openai_body({
            "title": "Fatura Cartão Nubank",
            "amount": 1850.45,
            "kind": "variable_expense",
            "category": "CategoriaInventada",  # must be sanitized
            "occurredOn": "2026-10-28",
            "paymentMethod": "credit",
            "merchantDoc": "Nu Pagamentos S.A.",
            "confidence": 94,
        }),
        _ok_openai_body({
            "title": "PIX Recebido - Freelance",
            "amount": 600.00,
            "kind": "income",
            "category": "Renda",
            "occurredOn": "2026-10-29",
            "paymentMethod": "pix",
            "merchantDoc": "PIX E2E 12345",
            "confidence": 97,
        }),
    ]

    cfg = AiConfig(mode="openai_compatible", api_key="k")
    client = OpenAiCompatibleClient(cfg, http_post=lambda *_: (200, responses.pop(0)))
    extractor = AiReceiptExtractor(client, world["kv"], world["clock"])

    fatura = extractor.extract(
        file_name="fatura.jpg",
        text_hint="",
        image_data_url="data:image/jpeg;base64,/9j/4AAQ",
        today_iso="2026-10-29",
        categories=STANDARD_CATEGORIES,
        standard_category_fn=standard_category,
        suggest_category_fn=suggest_category,
        valid_iso_date_fn=valid_iso_date,
        fallback_fn=lambda: {"title": "Fallback", "amount": 10.0, "kind": "variable_expense", "category": "Outros", "occurredOn": "2026-10-29", "paymentMethod": "pix", "merchantDoc": "doc", "confidence": 50},
    )
    assert fatura["source"] == "ai"
    assert fatura["amount"] == 1850.45
    assert fatura["category"] in STANDARD_CATEGORIES
    assert fatura["paymentMethod"] == "credit"

    pix_in = extractor.extract(
        file_name="pix.png",
        text_hint="",
        image_data_url="data:image/png;base64,iVBOR",
        today_iso="2026-10-29",
        categories=STANDARD_CATEGORIES,
        standard_category_fn=standard_category,
        suggest_category_fn=suggest_category,
        valid_iso_date_fn=valid_iso_date,
        fallback_fn=lambda: {"title": "Fallback", "amount": 10.0, "kind": "variable_expense", "category": "Outros", "occurredOn": "2026-10-29", "paymentMethod": "pix", "merchantDoc": "doc", "confidence": 50},
    )
    assert pix_in["source"] == "ai"
    assert pix_in["kind"] == "income"
    assert pix_in["category"] == "Renda"


def test_receipt_extractor_fallback_and_circuit_breaker_on_429(world):
    calls = {"n": 0}

    def post_429(*_):
        calls["n"] += 1
        return 429, "quota exceeded"

    cfg = AiConfig(mode="openai_compatible", api_key="k")
    client = OpenAiCompatibleClient(cfg, http_post=post_429)
    extractor = AiReceiptExtractor(client, world["kv"], world["clock"])
    fb = lambda: {"title": "Fallback Boleto", "amount": 99.9, "kind": "fixed_expense", "category": "Serviços", "occurredOn": "2026-10-29", "paymentMethod": "boleto", "merchantDoc": "Fallback", "confidence": 70}

    res1 = extractor.extract(
        file_name="boleto.jpg",
        text_hint="",
        image_data_url="data:image/jpeg;base64,/9j/4AAQ",
        today_iso="2026-10-29",
        categories=STANDARD_CATEGORIES,
        standard_category_fn=standard_category,
        suggest_category_fn=suggest_category,
        valid_iso_date_fn=valid_iso_date,
        fallback_fn=fb,
    )
    assert res1["source"] == "fallback"
    assert res1["fallbackReason"] == "rate_limit"
    assert calls["n"] == 1

    # Second call within 60s should short-circuit without calling HTTP
    res2 = extractor.extract(
        file_name="boleto2.jpg",
        text_hint="",
        image_data_url="data:image/jpeg;base64,/9j/4AAQ",
        today_iso="2026-10-29",
        categories=STANDARD_CATEGORIES,
        standard_category_fn=standard_category,
        suggest_category_fn=suggest_category,
        valid_iso_date_fn=valid_iso_date,
        fallback_fn=fb,
    )
    assert res2["source"] == "fallback"
    assert calls["n"] == 1


def test_advisor_deterministic_states_and_kv_caching(world):
    calls = {"n": 0}

    def post_ok(*_):
        calls["n"] += 1
        return 200, _ok_openai_body({
            "headline": "Gastos elevados em Alimentação",
            "summary": "Você ultrapassou o limite configurado nesta categoria.",
            "recommendations": ["Reduza pedidos de delivery.", "Defina um teto diário."],
            "tone": "alert",
        })

    cfg = AiConfig(mode="openai_compatible", api_key="k")
    client = OpenAiCompatibleClient(cfg, http_post=post_ok)
    advisor = FinancialAdvisor(client, world["kv"], world["clock"])

    dashboard_sample = {
        "summary": {"effectiveIncome": 3000.0, "totalExpenses": 2700.0, "freeBalance": 300.0, "fixedShare": 50, "variableShare": 40},
        "goal": {"title": "Reserva Financeira"},
        "limits": [{"category": "Alimentação", "status": "exceeded", "percent": 115}],
        "transactions": [{"id": "1"}, {"id": "2"}],
        "categoryBreakdown": [{"category": "Alimentação", "spent": 1150.0}],
    }
    condensed = compute_deterministic_context(dashboard_sample)
    assert "EXPENSE_RATIO_HIGH" in condensed["states"]
    assert "LIMIT_EXCEEDED" in condensed["states"]
    assert "LOW_ACTIVITY" in condensed["states"]
    assert "transactions" not in condensed

    # Before generation: cache miss -> fallback + needs_refresh=True
    cached_initial, needs_refresh = advisor.get_cached_or_fallback("acc-1", condensed)
    assert cached_initial["source"] == "fallback"
    assert needs_refresh is True

    # First generation calls API and caches
    gen1 = advisor.generate_summary("acc-1", condensed)
    assert gen1["source"] == "ai"
    assert gen1["cached"] is False
    assert calls["n"] == 1

    # Second call with same fingerprint hits cache
    gen2 = advisor.generate_summary("acc-1", condensed)
    assert gen2["source"] == "ai"
    assert gen2["cached"] is True
    assert calls["n"] == 1

    # Advance clock past cooldown and force refresh
    world["clock"].advance(45)
    gen3 = advisor.generate_summary("acc-1", condensed, force=True)
    assert gen3["source"] == "ai"
    assert calls["n"] == 2


def test_http_ai_summary_and_config_endpoints(world):
    cfg = AiConfig(mode="openai_compatible", api_key="k", model="gemini-3.5-flash-lite", tier="free_prototype")
    client = OpenAiCompatibleClient(
        cfg,
        http_post=lambda *_: (200, _ok_openai_body({
            "headline": "Resumo IA ativo",
            "summary": "Seu orçamento está sob controle no ciclo atual.",
            "recommendations": ["Mantenha os registros em dia."],
            "tone": "ok",
        })),
    )
    ledger = LedgerModule(
        world["ledger_store"],
        world["accounts"],
        world["lessons"],
        world["clock"],
        world["audit"],
        receipt_extractor=AiReceiptExtractor(client, world["kv"], world["clock"]),
        advisor=FinancialAdvisor(client, world["kv"], world["clock"]),
    )
    api = RegistrationApi(
        world["account"], world["session"], world["confirmation"], world["finance"],
        world["api"].throttle, world["lessons"], world["bot"], world["clock"], "", "demo",
        ledger=ledger, ai_config=cfg,
    )

    cfg_res = api.handle("GET", "http://127.0.0.1:8787/api/config", {}, b"")
    assert cfg_res.status == 200
    assert cfg_res.body["aiEnabled"] is True
    assert cfg_res.body["aiTier"] == "free_prototype"
    assert cfg_res.body["aiModel"] == "gemini-3.5-flash-lite"

    created = post(api, "/api/register", registration())
    owner = cookie_of(created)
    inbox = api.handle("GET", "http://127.0.0.1:8787/api/demo-inbox", {"cookie": owner}, b"")
    confirmed = post(api, "/api/confirm", {"code": inbox.body["code"]}, owner)
    owner = cookie_of(confirmed)
    post(api, "/api/finance", {"income": 4000, "fixedExpenses": 1500, "goal": "reserve"}, owner)

    summary_res = post(api, "/api/ai/summary", {"force": False}, owner)
    assert summary_res.status == 200
    assert summary_res.body["aiSummary"]["source"] == "ai"
    assert summary_res.body["aiSummary"]["headline"] == "Resumo IA ativo"
