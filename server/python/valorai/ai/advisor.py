"""Condensed financial advisor with deterministic state injection and KV caching."""

import json

from valorai.ai.client import AiProviderError, AiRateLimitError, OpenAiCompatibleClient
from valorai.ai.receipt import CIRCUIT_BREAKER_KEY, CIRCUIT_COOLDOWN_SECONDS
from valorai.crypto import sha256_hex

MANUAL_REFRESH_COOLDOWN_SECONDS = 30
SIGNIFICANT_CHANGE_RATIO = 0.15  # 15% shift in income or total expenses
SIGNIFICANT_BASELINE_AMOUNT = 200.0  # Minimum R$ 200 shift when baseline was 0

ADVISOR_SYSTEM_PROMPT = (
    "Você é o consultor financeiro do ValorAI. Com base exclusivamente nas métricas condensadas "
    "e nos estados determinísticos informados, gere um resumo curto e recomendações práticas em português do Brasil.\n"
    "Regras:\n"
    "1. Seja direto, empático e objetivo: headline com no máximo 90 caracteres; summary com 2 a 3 frases curtas (máx. 400 caracteres).\n"
    "2. Gere 2 recomendações práticas e acionáveis alinhadas ao objetivo financeiro e aos estados ativos.\n"
    "3. Nunca invente números que não estejam nas métricas recebidas.\n"
    "4. Defina 'tone' como 'alert' se LIMIT_EXCEEDED ou EXPENSE_RATIO_HIGH estiver ativo; "
    "'warning' se NEAR_LIMIT ou NO_LIMITS_SET estiver ativo; caso contrário 'ok'."
)

ADVISOR_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
        },
        "tone": {"type": "string", "enum": ["ok", "warning", "alert"]},
    },
    "required": ["headline", "summary", "recommendations", "tone"],
}


def compute_deterministic_context(dashboard_data: dict) -> dict:
    """Builds a PII-free condensed financial snapshot and deterministic state flags."""
    summary = dashboard_data.get("summary") or {}
    goal = dashboard_data.get("goal") or {}
    limits = dashboard_data.get("limits") or []
    transactions = dashboard_data.get("transactions") or []
    breakdown = dashboard_data.get("categoryBreakdown") or []

    effective_income = float(summary.get("effectiveIncome") or 0)
    total_expenses = float(summary.get("totalExpenses") or 0)
    free_balance = float(summary.get("freeBalance") or 0)

    states: list[str] = []
    if effective_income > 0 and (total_expenses / effective_income) >= 0.85:
        states.append("EXPENSE_RATIO_HIGH")
    if any(lim.get("status") == "exceeded" for lim in limits):
        states.append("LIMIT_EXCEEDED")
    if any(lim.get("status") in ("warning", "reached") for lim in limits):
        states.append("NEAR_LIMIT")
    if free_balance > 0 and "LIMIT_EXCEEDED" not in states:
        states.append("POSITIVE_SURPLUS")
    if not limits:
        states.append("NO_LIMITS_SET")
    if len(transactions) < 3:
        states.append("LOW_ACTIVITY")

    condensed = {
        "goalTitle": str(goal.get("title") or "Reserva Financeira"),
        "monthlyIncome": round(effective_income, 2),
        "totalExpenses": round(total_expenses, 2),
        "freeBalance": round(free_balance, 2),
        "fixedShare": int(summary.get("fixedShare") or 0),
        "variableShare": int(summary.get("variableShare") or 0),
        "topCategories": [
            {"category": item["category"], "spent": round(float(item["spent"]), 2)}
            for item in breakdown[:3]
        ],
        "limitAlerts": [
            {"category": lim["category"], "status": lim["status"], "percent": int(lim.get("percent") or 0)}
            for lim in limits
            if lim.get("status") in ("warning", "reached", "exceeded")
        ][:4],
        "states": states,
    }
    condensed["fingerprint"] = sha256_hex(json.dumps(condensed, sort_keys=True, ensure_ascii=False))
    return condensed


def _material_shift(previous_value: float, current_value: float) -> bool:
    if previous_value <= 0:
        return current_value >= SIGNIFICANT_BASELINE_AMOUNT
    return abs(current_value - previous_value) / previous_value >= SIGNIFICANT_CHANGE_RATIO


def _top_category(condensed: dict) -> str | None:
    top = condensed.get("topCategories") or []
    if not top or not isinstance(top[0], dict):
        return None
    return top[0].get("category")


def _alert_statuses(condensed: dict) -> set[tuple[str | None, str | None]]:
    return {
        (item.get("category"), item.get("status"))
        for item in (condensed.get("limitAlerts") or [])
        if isinstance(item, dict)
    }


def should_regenerate_summary(previous_snapshot: dict | None, current_condensed: dict) -> bool:
    """Evaluates whether financial premises changed enough to justify a new AI summary."""
    if not isinstance(previous_snapshot, dict):
        return True
    if set(previous_snapshot.get("states") or []) != set(current_condensed.get("states") or []):
        return True
    if str(previous_snapshot.get("goalTitle") or "") != str(current_condensed.get("goalTitle") or ""):
        return True
    if _top_category(previous_snapshot) != _top_category(current_condensed):
        return True
    if _alert_statuses(previous_snapshot) != _alert_statuses(current_condensed):
        return True
    if _material_shift(
        float(previous_snapshot.get("monthlyIncome") or 0),
        float(current_condensed.get("monthlyIncome") or 0),
    ):
        return True
    if _material_shift(
        float(previous_snapshot.get("totalExpenses") or 0),
        float(current_condensed.get("totalExpenses") or 0),
    ):
        return True
    return False


def build_deterministic_summary(condensed: dict) -> dict:
    """Generates a deterministic local summary when AI is unavailable or in demo mode."""
    states = set(condensed.get("states") or [])
    income = float(condensed.get("monthlyIncome") or 0)
    expenses = float(condensed.get("totalExpenses") or 0)
    balance = float(condensed.get("freeBalance") or 0)
    top_cat = condensed["topCategories"][0]["category"] if condensed.get("topCategories") else None
    goal_title = condensed.get("goalTitle") or "Reserva Financeira"

    if "LIMIT_EXCEEDED" in states:
        tone = "alert"
        headline = "Atenção: um ou mais limites de gastos foram ultrapassados."
        summary = (
            f"Você já comprometeu R$ {expenses:.2f} de uma renda de R$ {income:.2f} neste ciclo. "
            f"O foco agora é conter despesas variáveis para proteger seu objetivo ({goal_title})."
        )
    elif "EXPENSE_RATIO_HIGH" in states:
        tone = "alert"
        headline = "Seus gastos já consomem mais de 85% da renda do mês."
        summary = (
            f"Seu saldo livre atual é de R$ {balance:.2f}. "
            + (f"A categoria {top_cat} lidera as saídas até aqui." if top_cat else "Evite novos parcelamentos neste ciclo.")
        )
    elif "NEAR_LIMIT" in states:
        tone = "warning"
        headline = "Você está próximo de atingir um teto de gastos configurado."
        summary = (
            f"Com R$ {expenses:.2f} gastos e saldo livre de R$ {balance:.2f}, "
            "vale segurar compras por impulso nos próximos dias."
        )
    elif "LOW_ACTIVITY" in states:
        tone = "ok"
        headline = "Poucos lançamentos registrados neste ciclo até agora."
        summary = (
            "Registre seus comprovantes por foto ou extrato para liberar uma leitura mais precisa "
            f"do seu ritmo em direção a '{goal_title}'."
        )
    else:
        tone = "ok"
        headline = "Orçamento equilibrado e dentro dos limites planejados."
        summary = (
            f"Você mantém R$ {balance:.2f} de saldo livre no ciclo atual"
            + (f", com maior concentração em {top_cat}." if top_cat else ".")
        )

    recommendations: list[str] = []
    if top_cat:
        recommendations.append(f"Revise os últimos lançamentos em {top_cat} para identificar cortes rápidos.")
    if "NO_LIMITS_SET" in states:
        recommendations.append("Configure ao menos um limite por categoria ou teto diário na aba Planejamento.")
    else:
        recommendations.append(f"Direcione parte do saldo livre para sua meta '{goal_title}'.")

    return {
        "headline": headline,
        "summary": summary,
        "recommendations": recommendations[:3],
        "tone": tone,
        "states": list(condensed.get("states") or []),
        "source": "fallback",
        "cached": False,
    }


class FinancialAdvisor:
    """Produces cached, state-guided financial summaries via an OpenAI-Compatible API."""

    def __init__(self, client: OpenAiCompatibleClient | None, kv, clock):
        self.client = client
        self.kv = kv
        self.clock = clock

    def _cache_key(self, account_id: str) -> str:
        return f"ai:summary:{account_id}"

    def _now_ts(self) -> int:
        return int(self.clock.now())

    def _circuit_open(self) -> bool:
        if self.kv is None:
            return False
        state = self.kv.get(CIRCUIT_BREAKER_KEY)
        return bool(state and int(state.get("until", 0)) > self._now_ts())

    def _trip_circuit(self) -> None:
        if self.kv is None:
            return
        self.kv.put(CIRCUIT_BREAKER_KEY, {"until": self._now_ts() + CIRCUIT_COOLDOWN_SECONDS})

    def _build_snapshot(self, condensed: dict) -> dict:
        return {k: v for k, v in condensed.items() if k != "fingerprint"}

    def _keep_cached(self, cached: dict, condensed: dict) -> bool:
        """Returns True if the cached AI summary remains valid under current financial premises."""
        snapshot = cached.get("snapshot") if isinstance(cached.get("snapshot"), dict) else None
        if snapshot is None:
            return False
        return not should_regenerate_summary(snapshot, condensed)

    def _can_call_ai(self) -> bool:
        return bool(self.client and self.client.is_configured() and not self._circuit_open())

    def get_cached_or_fallback(self, account_id: str, condensed: dict) -> tuple[dict, bool]:
        """Non-blocking read for GET /api/dashboard: returns (summary, needs_ai_refresh)."""
        key = self._cache_key(account_id)
        cached = self.kv.get(key) if self.kv is not None else None
        if cached and isinstance(cached.get("data"), dict):
            if self._keep_cached(cached, condensed):
                return {**cached["data"], "cached": True}, False
            return {**cached["data"], "cached": True}, self._can_call_ai()

        return build_deterministic_summary(condensed), self._can_call_ai()

    def generate_summary(self, account_id: str, condensed: dict, force: bool = False) -> dict:
        """Generates or returns cached AI summary, falling back to deterministic rules on error."""
        now_ts = self._now_ts()
        key = self._cache_key(account_id)
        cached = self.kv.get(key) if self.kv is not None else None
        has_cached_data = bool(cached and isinstance(cached.get("data"), dict))

        if has_cached_data:
            in_cooldown = (now_ts - int(cached.get("createdAt", 0))) < MANUAL_REFRESH_COOLDOWN_SECONDS
            if (not force or in_cooldown) and self._keep_cached(cached, condensed):
                return {**cached["data"], "cached": True}

        if not self._can_call_ai():
            return {**cached["data"], "cached": True} if has_cached_data else build_deterministic_summary(condensed)

        prompt_payload = self._build_snapshot(condensed)
        messages = [
            {"role": "system", "content": ADVISOR_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Métricas condensadas do usuário:\n{json.dumps(prompt_payload, ensure_ascii=False)}",
            },
        ]

        try:
            raw = self.client.chat_json(
                messages,
                json_schema=ADVISOR_JSON_SCHEMA,
                schema_name="financial_summary",
                timeout_s=8.0,
            )
            result = self._normalize(raw, condensed)
            if self.kv is not None:
                self.kv.put(
                    key,
                    {
                        "fingerprint": condensed["fingerprint"],
                        "snapshot": prompt_payload,
                        "createdAt": now_ts,
                        "data": result,
                    },
                )
            return {**result, "cached": False}
        except AiRateLimitError:
            self._trip_circuit()
            return {**cached["data"], "cached": True} if has_cached_data else build_deterministic_summary(condensed)
        except (AiProviderError, Exception):
            return {**cached["data"], "cached": True} if has_cached_data else build_deterministic_summary(condensed)

    def _normalize(self, raw: dict, condensed: dict) -> dict:
        headline = str(raw.get("headline") or "").strip()[:120]
        summary = str(raw.get("summary") or "").strip()[:500]
        recs_raw = raw.get("recommendations")
        recommendations = [
            str(item).strip()[:180]
            for item in (recs_raw if isinstance(recs_raw, list) else [])
            if str(item).strip()
        ][:3]
        tone = str(raw.get("tone") or "ok").strip().lower()
        if tone not in {"ok", "warning", "alert"}:
            tone = "ok"

        if not headline or not summary or not recommendations:
            return build_deterministic_summary(condensed)

        return {
            "headline": headline,
            "summary": summary,
            "recommendations": recommendations,
            "tone": tone,
            "states": list(condensed.get("states") or []),
            "source": "ai",
        }
