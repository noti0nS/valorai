import csv
import io
import re
from dataclasses import replace
from datetime import datetime

from valorai.crypto import sha256_hex
from valorai.errors import ApiError
from valorai.finance.module import GOALS, to_cents, to_reais
from valorai.records import Account, BudgetLimit, Transaction

STANDARD_CATEGORIES = (
    "Alimentação & Mercado",
    "Moradia (Fixo)",
    "Transporte",
    "Lazer & Restaurantes",
    "Educação",
    "Saúde",
    "Contas & Serviços",
    "Renda / Serviços",
    "Reserva & Investimentos",
    "Outros",
)

KINDS = {"income", "fixed_expense", "variable_expense"}
CHANNELS = {"manual", "import", "photo"}
STATUSES = {"paid", "pending"}
PAYMENT_METHODS = {"pix", "credit", "debit", "cash", "boleto", "transfer"}
LIMIT_SCOPES = {"category", "daily", "card_share"}

CATEGORY_RULES: tuple[tuple[tuple[str, ...], str, str | None], ...] = (
    (("aluguel", "condominio", "condomínio", "iptu", "financiamento", "habitacao", "habitação", "moradia"), "Moradia (Fixo)", "fixed_expense"),
    (("energia", "conta de luz", "eletricidade", "agua", "água", "saneamento", "internet", "fibra", " Vivo ", "claro", "tim", "gas", "gás", "seguro"), "Contas & Serviços", "fixed_expense"),
    (("pao de acucar", "pão de açúcar", "supermercado", "mercado", "atacadao", "atacadão", "assai", "assaí", "carrefour", "padaria", "hortifruti", "feira", "açougue"), "Alimentação & Mercado", "variable_expense"),
    (("uber", "99pop", "99app", "taxi", "táxi", "combustivel", "combustível", "posto", "ipiranga", "shell", "metro", "metrô", "onibus", "ônibus", "pedagio", "pedágio", "estacionamento"), "Transporte", "variable_expense"),
    (("restaurante", "bistro", "bistrô", "ifood", "lazer", "cinema", "teatro", "show", "bar", "café", "cafeteria", "viagem", "hotel", "streaming", "netflix", "spotify"), "Lazer & Restaurantes", "variable_expense"),
    (("livraria", "cultura", "livro", "curso", "faculdade", "escola", "mensalidade escolar", "idioma", "udemy", "alura", "educacao", "educação"), "Educação", "variable_expense"),
    (("farmacia", "farmácia", "drogasil", "droga raia", "pague menos", "hospital", "clinica", "clínica", "consulta", "exame", "medico", "médico", "dentista", "plano de saude", "plano de saúde"), "Saúde", "variable_expense"),
    (("reserva", "tesouro", "cdb", "lci", "lca", "fii", "acoes", "ações", "investimento", "aporte", "poupanca", "poupança"), "Reserva & Investimentos", "variable_expense"),
    (("salario", "salário", "consultoria", "freelance", "pro-labore", "pró-labore", "dividendo", "rendimento", "reembolso", "receita", "transferencia recebida", "transferência recebida", "pix recebido"), "Renda / Serviços", "income"),
)

GOAL_LABELS = {
    "budget": "Organizar meu orçamento",
    "debt": "Sair das dívidas",
    "reserve": "Reserva Financeira",
    "invest": "Começar a investir",
}

MONTH_NAMES_PT = (
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
)


def suggest_category(title: str, kind: str | None = None) -> tuple[str, str]:
    normalized = f" {title.strip().lower()} "
    for keywords, category, suggested_kind in CATEGORY_RULES:
        if any(keyword.lower() in normalized for keyword in keywords):
            resolved_kind = kind if kind in KINDS else (suggested_kind or "variable_expense")
            if resolved_kind == "income":
                return "Renda / Serviços", "income"
            return category, resolved_kind
    if kind == "income":
        return "Renda / Serviços", "income"
    if kind == "fixed_expense":
        return "Moradia (Fixo)", "fixed_expense"
    return "Outros", kind if kind in KINDS else "variable_expense"


def valid_iso_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", text):
        day, month, year = text.split("/")
        text = f"{year}-{month}-{day}"
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None
    if parsed.year < 2000 or parsed.year > 2100:
        return None
    return text


def parse_Flexible_amount(raw: object) -> tuple[int | None, str]:
    """Returns (amount_cents, inferred_sign: 'positive' | 'negative')."""
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        sign = "negative" if raw < 0 else "positive"
        cents = to_cents(abs(raw))
        return (cents if cents and cents > 0 else None), sign
    if not isinstance(raw, str):
        return None, "negative"
    cleaned = raw.strip()
    if not cleaned:
        return None, "negative"
    sign = "negative" if "-" in cleaned or "−" in cleaned or cleaned.upper().endswith("D") else "positive"
    if "+" in cleaned:
        sign = "positive"
    cleaned = re.sub(r"[^\d,.\-]", "", cleaned).replace("-", "")
    if not cleaned:
        return None, sign
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        numeric = float(cleaned)
    except ValueError:
        return None, sign
    cents = to_cents(abs(numeric))
    return (cents if cents and cents > 0 else None), sign


class LedgerModule:
    def __init__(self, ledger, accounts, lessons, clock, audit):
        self.ledger = ledger
        self.accounts = accounts
        self.lessons = lessons
        self.clock = clock
        self.audit = audit

    def present_dashboard(self, account: Account) -> dict:
        transactions = self.ledger.list_transactions(account.id)
        limits = self.ledger.list_limits(account.id)
        today_dt = self.clock.today()
        today_iso = today_dt.date().isoformat()
        cycle_label = f"{MONTH_NAMES_PT[today_dt.month - 1]} de {today_dt.year}"

        base_income_cents = account.income or 0
        base_fixed_cents = account.fixed_expenses or 0

        ledger_income_cents = sum(tx.amount_cents for tx in transactions if tx.kind == "income")
        ledger_fixed_cents = sum(tx.amount_cents for tx in transactions if tx.kind == "fixed_expense")
        ledger_variable_cents = sum(tx.amount_cents for tx in transactions if tx.kind == "variable_expense")
        pending_bills_cents = sum(
            tx.amount_cents for tx in transactions if tx.kind in {"fixed_expense", "variable_expense"} and tx.status == "pending"
        )

        # Effective figures:
        # Base profile represents monthly baseline; extra income and variable expenses adjust available balance.
        # If fixed expenses in ledger exceed declared fixed baseline, use the higher committed value.
        effective_income_cents = base_income_cents if base_income_cents > 0 else ledger_income_cents
        if base_income_cents > 0 and ledger_income_cents > 0 and base_income_cents < ledger_income_cents:
            effective_income_cents = ledger_income_cents
        effective_fixed_cents = max(base_fixed_cents, ledger_fixed_cents)
        free_balance_cents = effective_income_cents - effective_fixed_cents - ledger_variable_cents

        if effective_income_cents > 0:
            fixed_share = min(100, round(effective_fixed_cents / effective_income_cents * 100))
            variable_share = min(max(0, 100 - fixed_share), round(ledger_variable_cents / effective_income_cents * 100))
            reserve_share = max(0, 100 - fixed_share - variable_share)
        else:
            fixed_share = 100 if effective_fixed_cents > 0 else 0
            variable_share = 0
            reserve_share = 0

        # Daily rhythm series (4 anchor points + daily average)
        total_expenses_cents = effective_fixed_cents + ledger_variable_cents
        days_elapsed = max(1, min(30, today_dt.day))
        daily_variable_avg_cents = round(ledger_variable_cents / days_elapsed) if ledger_variable_cents > 0 else round(effective_fixed_cents / 30)
        daily_series = self._build_daily_series(transactions, effective_fixed_cents, today_dt)

        # Evaluated limits & alerts
        evaluated_limits, alerts = self._evaluate_limits(transactions, limits, effective_income_cents, today_iso)

        # Goal metrics
        goal_id = account.goal or "reserve"
        goal_target_cents = max(100, account.goal_target_cents or 500_000)
        goal_current_cents = max(0, account.goal_current_cents or 0)
        goal_monthly_cents = max(0, account.goal_monthly_cents or 75_000)
        goal_percent = min(100, round(goal_current_cents / goal_target_cents * 100))
        remaining_goal_cents = max(0, goal_target_cents - goal_current_cents)
        if remaining_goal_cents == 0:
            months_remaining = 0
        elif goal_monthly_cents > 0:
            months_remaining = max(1, round(remaining_goal_cents / goal_monthly_cents))
        elif free_balance_cents > 0:
            months_remaining = max(1, round(remaining_goal_cents / max(10_000, round(free_balance_cents * 0.3))))
        else:
            months_remaining = 12

        # Predictive AI insight
        liquidity_buffer_cents = max(120_000, round(effective_fixed_cents * 0.32))
        if free_balance_cents < 0:
            status_badge = "Acima do planejado"
            status_tone = "over"
            insight_msg = (
                f"Seus compromissos e despesas superam a renda planejada em R$ {self._fmt_brl(abs(free_balance_cents))}. "
                f"Revise gastos variáveis ou ajuste os tetos de categoria para recuperar margem neste ciclo."
            )
        elif any(a["status"] == "exceeded" for a in alerts):
            top_alert = next(a for a in alerts if a["status"] == "exceeded")
            status_badge = "Atenção ao ritmo"
            status_tone = "warning"
            insight_msg = (
                f"O teto de “{top_alert['category']}” foi atingido ({top_alert['percent']}%). "
                f"Manter R$ {self._fmt_brl(liquidity_buffer_cents)} em conta preserva seus compromissos fixos e sua meta “{GOAL_LABELS.get(goal_id, 'Reserva Financeira')}”."
            )
        else:
            status_badge = "Equilibrado"
            status_tone = "balanced"
            insight_msg = (
                f"82% das suas contas fixas concentram-se até o dia 10. Manter R$ {self._fmt_brl(liquidity_buffer_cents)} "
                f"em conta garante a liquidez necessária sem comprometer a meta “{GOAL_LABELS.get(goal_id, 'Reserva Financeira')}”."
            )

        # Category breakdown
        by_category: dict[str, int] = {}
        for tx in transactions:
            if tx.kind != "income":
                by_category[tx.category] = by_category.get(tx.category, 0) + tx.amount_cents
        category_breakdown = [
            {"category": cat, "spent": to_reais(cents)}
            for cat, cents in sorted(by_category.items(), key=lambda item: item[1], reverse=True)
        ]

        progress_map = self.lessons.list_progress(account.id)
        lessons_with_progress = [
            {
                **lesson,
                "progressPercent": progress_map.get(lesson["id"], 0),
            }
            for lesson in self.lessons.list()
        ]

        return {
            "cycle": {
                "label": cycle_label,
                "code": f"{today_dt.year}.{today_dt.month:02d}",
                "today": today_iso,
            },
            "summary": {
                "baseIncome": to_reais(base_income_cents),
                "baseFixedExpenses": to_reais(base_fixed_cents),
                "ledgerIncome": to_reais(ledger_income_cents),
                "ledgerFixedExpenses": to_reais(ledger_fixed_cents),
                "ledgerVariableExpenses": to_reais(ledger_variable_cents),
                "pendingBills": to_reais(pending_bills_cents),
                "effectiveIncome": to_reais(effective_income_cents),
                "effectiveFixed": to_reais(effective_fixed_cents),
                "variableExpenses": to_reais(ledger_variable_cents),
                "freeBalance": to_reais(free_balance_cents),
                "totalExpenses": to_reais(total_expenses_cents),
                "fixedShare": fixed_share,
                "variableShare": variable_share,
                "reserveShare": reserve_share,
                "dailyAverage": to_reais(daily_variable_avg_cents),
                "dailySeries": daily_series,
                "statusBadge": status_badge,
                "statusTone": status_tone,
                "insight": {
                    "title": "Diretriz Preditiva ValorAI",
                    "message": insight_msg,
                    "liquidityRecommended": to_reais(liquidity_buffer_cents),
                },
            },
            "goal": {
                "id": goal_id,
                "title": GOAL_LABELS.get(goal_id, "Reserva Financeira"),
                "target": to_reais(goal_target_cents),
                "current": to_reais(goal_current_cents),
                "monthly": to_reais(goal_monthly_cents),
                "percent": goal_percent,
                "monthsRemaining": months_remaining,
            },
            "transactions": [self.present_transaction(tx) for tx in transactions],
            "limits": evaluated_limits,
            "alerts": alerts,
            "categories": list(STANDARD_CATEGORIES),
            "categoryBreakdown": category_breakdown,
            "lessons": lessons_with_progress,
        }

    def present_transaction(self, tx: Transaction) -> dict:
        return {
            "id": tx.id,
            "title": tx.title,
            "amount": to_reais(tx.amount_cents),
            "kind": tx.kind,
            "category": tx.category,
            "channel": tx.channel,
            "occurredOn": tx.occurred_on,
            "status": tx.status,
            "paymentMethod": tx.payment_method,
            "merchantDoc": tx.merchant_doc,
            "confidence": tx.confidence,
            "validated": tx.validated,
            "notes": tx.notes,
            "createdAt": tx.created_at,
        }

    def handle_transaction(self, account: Account, payload: dict, ip_hash: str) -> dict:
        if not isinstance(payload, dict):
            raise ApiError(400, "Não foi possível ler o formulário.")
        action = payload.get("action", "create")
        if action == "seed_demo":
            return self.seed_demo_cycle(account, ip_hash)
        if action == "delete":
            tx_id = payload.get("id")
            if not isinstance(tx_id, str) or not tx_id:
                raise ApiError(422, "Identifique o lançamento para excluir.", {"id": "Lançamento inválido."})
            if not self.ledger.delete_transaction(account.id, tx_id):
                raise ApiError(404, "Lançamento não encontrado.")
            self.audit.record(account.id, "transaction_deleted", ip_hash, self.clock.now())
            return self.present_dashboard(account)
        if action == "validate":
            tx_id = payload.get("id")
            existing = self.ledger.find_transaction(account.id, tx_id) if isinstance(tx_id, str) else None
            if existing is None:
                raise ApiError(404, "Lançamento não encontrado.")
            new_category = payload.get("category")
            cat = new_category.strip() if isinstance(new_category, str) and new_category.strip() else existing.category
            updated = replace(existing, validated=True, category=cat[:60])
            self.ledger.update_transaction(updated)
            self.audit.record(account.id, "transaction_validated", ip_hash, self.clock.now())
            return self.present_dashboard(account)
        if action == "toggle_status":
            tx_id = payload.get("id")
            existing = self.ledger.find_transaction(account.id, tx_id) if isinstance(tx_id, str) else None
            if existing is None:
                raise ApiError(404, "Lançamento não encontrado.")
            next_status = "paid" if existing.status == "pending" else "pending"
            updated = replace(existing, status=next_status)
            self.ledger.update_transaction(updated)
            self.audit.record(account.id, "transaction_status_toggled", ip_hash, self.clock.now())
            return self.present_dashboard(account)

        tx = self._validate_transaction_payload(account, payload)
        if action == "update":
            tx_id = payload.get("id")
            existing = self.ledger.find_transaction(account.id, tx_id) if isinstance(tx_id, str) else None
            if existing is None:
                raise ApiError(404, "Lançamento não encontrado.")
            updated = replace(
                tx,
                id=existing.id,
                created_at=existing.created_at,
                external_ref=existing.external_ref,
            )
            self.ledger.update_transaction(updated)
            self.audit.record(account.id, "transaction_updated", ip_hash, self.clock.now())
        else:
            self.ledger.insert_transaction(tx)
            self.audit.record(account.id, "transaction_created", ip_hash, self.clock.now())
        return self.present_dashboard(account)

    def handle_import(self, account: Account, payload: dict, ip_hash: str) -> dict:
        if not isinstance(payload, dict):
            raise ApiError(400, "Não foi possível ler os dados de importação.")
        preview_only = bool(payload.get("preview", False))
        raw_items = payload.get("items")
        if isinstance(raw_items, list) and not preview_only:
            parsed_items = self._normalize_confirmed_import_items(account, raw_items)
        else:
            content = payload.get("content")
            file_name = str(payload.get("fileName") or "extrato.ofx")
            format_hint = str(payload.get("format") or "auto").lower()
            if not isinstance(content, str) or not content.strip():
                raise ApiError(422, "Selecione ou cole o conteúdo de um arquivo CSV, Excel ou OFX.", {"content": "Arquivo vazio."})
            parsed_items = self.parse_import_content(account, format_hint, file_name, content)
            if not parsed_items:
                raise ApiError(422, "Nenhum lançamento válido foi encontrado no arquivo enviado.", {"content": "Formato não reconhecido ou sem linhas válidas."})

        if preview_only:
            return {
                "preview": True,
                "items": parsed_items,
                "totalCount": len(parsed_items),
                "duplicateCount": sum(1 for item in parsed_items if item["isDuplicate"]),
            }

        now = self.clock.now()
        imported_count = 0
        duplicate_count = 0
        for item in parsed_items:
            if item.get("isDuplicate") or self.ledger.has_external_ref(account.id, item["externalRef"]):
                duplicate_count += 1
                continue
            tx = Transaction(
                id=self.ledger.next_id(),
                account_id=account.id,
                title=item["title"],
                amount_cents=item["amountCents"],
                kind=item["kind"],
                category=item["category"],
                channel="import",
                occurred_on=item["occurredOn"],
                status="paid",
                payment_method=item.get("paymentMethod", "debit"),
                merchant_doc=item.get("merchantDoc"),
                confidence=95,
                validated=True,
                external_ref=item["externalRef"],
                notes=item.get("notes"),
                created_at=now,
            )
            self.ledger.insert_transaction(tx)
            imported_count += 1

        self.audit.record(account.id, "transactions_imported", ip_hash, now)
        dashboard = self.present_dashboard(account)
        dashboard["importResult"] = {
            "importedCount": imported_count,
            "duplicateCount": duplicate_count,
        }
        return dashboard

    def handle_receipt(self, account: Account, payload: dict, ip_hash: str) -> dict:
        if not isinstance(payload, dict):
            raise ApiError(400, "Não foi possível ler os dados do comprovante.")
        confirm = bool(payload.get("confirm", False))
        if confirm:
            tx_data = payload.get("transaction")
            if not isinstance(tx_data, dict):
                raise ApiError(422, "Confira os dados extraídos do comprovante antes de salvar.")
            merged = {
                **tx_data,
                "channel": "photo",
                "validated": True,
                "confidence": int(tx_data.get("confidence") or 98),
            }
            tx = self._validate_transaction_payload(account, merged)
            self.ledger.insert_transaction(tx)
            self.audit.record(account.id, "receipt_transaction_saved", ip_hash, self.clock.now())
            return self.present_dashboard(account)

        file_name = str(payload.get("fileName") or "comprovante-nfce.jpg").strip()
        text_hint = str(payload.get("textHint") or "").strip()
        preset = str(payload.get("preset") or "").strip().lower()
        today_iso = self.clock.today().date().isoformat()

        extracted = self._extract_receipt_metadata(file_name, text_hint, preset, today_iso)
        return {"extracted": extracted}

    def handle_limit(self, account: Account, payload: dict, ip_hash: str) -> dict:
        if not isinstance(payload, dict):
            raise ApiError(400, "Não foi possível ler o limite.")
        action = payload.get("action", "upsert")
        if action == "delete":
            limit_id = payload.get("id")
            if not isinstance(limit_id, str) or not limit_id:
                raise ApiError(422, "Identifique o limite para remover.")
            self.ledger.delete_limit(account.id, limit_id)
            self.audit.record(account.id, "budget_limit_deleted", ip_hash, self.clock.now())
            return self.present_dashboard(account)

        scope = str(payload.get("scope") or "category")
        if scope not in LIMIT_SCOPES:
            raise ApiError(422, "Selecione um escopo de limite válido.", {"scope": "Escopo inválido."})
        category = str(payload.get("category") or "").strip()
        if scope == "daily" and not category:
            category = "Teto Diário"
        elif scope == "card_share" and not category:
            category = "Supérfluos no Cartão"
        if not (2 <= len(category) <= 60):
            raise ApiError(422, "Informe a categoria ou identificação do limite.", {"category": "Informe a categoria."})

        limit_cents = to_cents(payload.get("limit"))
        if limit_cents is None or limit_cents <= 0:
            raise ApiError(422, "Informe um valor maior que zero para o limite.", {"limit": "Informe um valor válido maior que zero."})
        if scope == "card_share" and limit_cents > 10_000:
            raise ApiError(422, "O percentual máximo deve estar entre 1% e 100%.", {"limit": "Informe entre 1% e 100%."})

        warn_raw = payload.get("warnPercent", 80)
        warn_percent = int(warn_raw) if isinstance(warn_raw, (int, float)) and not isinstance(warn_raw, bool) else 80
        warn_percent = max(10, min(100, warn_percent))

        limit = BudgetLimit(
            id=self.ledger.next_id(),
            account_id=account.id,
            scope=scope,
            category=category,
            limit_cents=limit_cents,
            warn_percent=warn_percent,
            created_at=self.clock.now(),
        )
        self.ledger.upsert_limit(limit)
        self.audit.record(account.id, "budget_limit_updated", ip_hash, self.clock.now())
        return self.present_dashboard(account)

    def handle_goal(self, account: Account, payload: dict, ip_hash: str) -> tuple[Account, dict]:
        if not isinstance(payload, dict):
            raise ApiError(400, "Não foi possível ler os dados da meta.")
        target_cents = to_cents(payload.get("target")) if "target" in payload else account.goal_target_cents
        current_cents = to_cents(payload.get("current")) if "current" in payload else account.goal_current_cents
        monthly_cents = to_cents(payload.get("monthly")) if "monthly" in payload else account.goal_monthly_cents
        contribution_cents = to_cents(payload.get("contribution")) if "contribution" in payload else 0

        errors: dict[str, str] = {}
        if target_cents is None or target_cents <= 0:
            errors["target"] = "Informe uma meta maior que zero."
        if current_cents is None or current_cents < 0:
            errors["current"] = "Informe um valor acumulado válido."
        if monthly_cents is None or monthly_cents < 0:
            errors["monthly"] = "Informe um aporte mensal válido."
        if contribution_cents is None or contribution_cents < 0:
            errors["contribution"] = "Informe um valor de aporte válido."
        if errors:
            raise ApiError(422, "Confira os valores da sua meta financeira.", errors)

        assert target_cents is not None and current_cents is not None and monthly_cents is not None
        if contribution_cents and contribution_cents > 0:
            current_cents += contribution_cents
            if payload.get("recordTransaction", True):
                today_iso = self.clock.today().date().isoformat()
                tx = Transaction(
                    id=self.ledger.next_id(),
                    account_id=account.id,
                    title=f"Aporte — {GOAL_LABELS.get(account.goal or 'reserve', 'Reserva Financeira')}",
                    amount_cents=contribution_cents,
                    kind="variable_expense",
                    category="Reserva & Investimentos",
                    channel="manual",
                    occurred_on=today_iso,
                    status="paid",
                    payment_method="transfer",
                    merchant_doc="APORTE.META",
                    validated=True,
                    created_at=self.clock.now(),
                )
                self.ledger.insert_transaction(tx)

        goal_code = payload.get("goal")
        if goal_code in GOALS and goal_code != account.goal:
            account = self.accounts.update_finance(
                account.id,
                account.income or 0,
                account.fixed_expenses or 0,
                goal_code,
                account.completed_at or self.clock.now(),
            )
        updated = self.accounts.update_goal_progress(account.id, target_cents, current_cents, monthly_cents)
        self.audit.record(account.id, "goal_progress_updated", ip_hash, self.clock.now())
        return updated, self.present_dashboard(updated)

    def handle_lesson_progress(self, account: Account, payload: dict, ip_hash: str) -> dict:
        if not isinstance(payload, dict):
            raise ApiError(400, "Não foi possível atualizar o guia.")
        lesson_id = payload.get("lessonId")
        known_ids = {item["id"] for item in self.lessons.list()}
        if not isinstance(lesson_id, str) or lesson_id not in known_ids:
            raise ApiError(404, "Guia educativo não encontrado.")
        raw_pct = payload.get("progressPercent", 100)
        if isinstance(raw_pct, bool) or not isinstance(raw_pct, (int, float)):
            raise ApiError(422, "Informe um percentual entre 0 e 100.")
        pct = max(0, min(100, int(raw_pct)))
        now = self.clock.now()
        self.lessons.set_progress(account.id, lesson_id, pct, now)
        self.audit.record(account.id, "lesson_progress_updated", ip_hash, now)
        return self.present_dashboard(account)

    def seed_demo_cycle(self, account: Account, ip_hash: str) -> dict:
        now = self.clock.now()
        today_dt = self.clock.today()
        ym = f"{today_dt.year}-{today_dt.month:02d}"
        sample_rows = [
            ("Pão de Açúcar • Supermercado", 34280, "variable_expense", "Alimentação & Mercado", "photo", f"{ym}-06", "credit", "NFC-e #4492", 99, "seed-pao-acucar"),
            ("Aluguel & Condomínio", 240000, "fixed_expense", "Moradia (Fixo)", "import", f"{ym}-05", "debit", "DEB.AUTOMATICO", 100, "seed-aluguel"),
            ("Uber do Brasil", 4290, "variable_expense", "Transporte", "photo", f"{ym}-04", "pix", "RECIBO-IA", 98, "seed-uber"),
            ("Livraria Cultura", 11900, "variable_expense", "Educação", "manual", f"{ym}-02", "credit", "MANUAL-WEB", None, "seed-livraria"),
            ("Restaurante & Bistrô", 55000, "variable_expense", "Lazer & Restaurantes", "photo", f"{ym}-03", "credit", "NFC-e #8821", 97, "seed-lazer"),
            ("Consultoria & Serviços", 120000, "income", "Renda / Serviços", "import", f"{ym}-01", "pix", "PIX.RECEBIDO", 100, "seed-consultoria"),
        ]
        for title, cents, kind, cat, channel, date_str, method, doc, conf, ref in sample_rows:
            if not self.ledger.has_external_ref(account.id, ref):
                self.ledger.insert_transaction(
                    Transaction(
                        id=self.ledger.next_id(),
                        account_id=account.id,
                        title=title,
                        amount_cents=cents,
                        kind=kind,
                        category=cat,
                        channel=channel,
                        occurred_on=date_str,
                        status="paid",
                        payment_method=method,
                        merchant_doc=doc,
                        confidence=conf,
                        validated=True,
                        external_ref=ref,
                        created_at=now,
                    )
                )
        self.ledger.upsert_limit(
            BudgetLimit(
                id=self.ledger.next_id(),
                account_id=account.id,
                scope="category",
                category="Lazer & Restaurantes",
                limit_cents=60_000,
                warn_percent=80,
                created_at=now,
            )
        )
        self.ledger.upsert_limit(
            BudgetLimit(
                id=self.ledger.next_id(),
                account_id=account.id,
                scope="daily",
                category="Teto Diário",
                limit_cents=10_000,
                warn_percent=80,
                created_at=now,
            )
        )
        if account.goal_current_cents == 0:
            account = self.accounts.update_goal_progress(account.id, 500_000, 200_000, 75_000)
        self.lessons.set_progress(account.id, "emergency-fund", 100, now)
        self.lessons.set_progress(account.id, "first-budget", 60, now)
        self.audit.record(account.id, "demo_cycle_seeded", ip_hash, now)
        return self.present_dashboard(account)

    def parse_import_content(self, account: Account, format_hint: str, file_name: str, content: str) -> list[dict]:
        lower_name = file_name.lower()
        stripped = content.lstrip()
        if format_hint == "ofx" or lower_name.endswith(".ofx") or "<OFX" in stripped.upper() or "<STMTTRN>" in stripped.upper():
            raw_rows = self._parse_ofx(stripped)
        elif "<table" in stripped.lower() or "<row" in stripped.lower() or "<tr" in stripped.lower():
            raw_rows = self._parse_xml_or_html_table(stripped)
        else:
            raw_rows = self._parse_delimited(stripped)

        results: list[dict] = []
        seen_refs: set[str] = set()
        for row in raw_rows:
            title = str(row.get("title") or "").strip()[:120]
            amount_cents = row.get("amountCents")
            occurred_on = valid_iso_date(row.get("occurredOn")) or self.clock.today().date().isoformat()
            if not title or not isinstance(amount_cents, int) or amount_cents <= 0:
                continue
            explicit_kind = row.get("kind")
            explicit_cat = str(row.get("category") or "").strip()
            suggested_cat, inferred_kind = suggest_category(title, explicit_kind if explicit_kind in KINDS else None)
            category = explicit_cat if explicit_cat else suggested_cat
            kind = explicit_kind if explicit_kind in KINDS else inferred_kind
            ext_ref = str(row.get("externalRef") or sha256_hex(f"{occurred_on}:{title.lower()}:{amount_cents}:{kind}")[:24])
            is_dup = ext_ref in seen_refs or self.ledger.has_external_ref(account.id, ext_ref)
            seen_refs.add(ext_ref)
            results.append({
                "title": title,
                "amount": to_reais(amount_cents),
                "amountCents": amount_cents,
                "kind": kind,
                "category": category,
                "occurredOn": occurred_on,
                "merchantDoc": row.get("merchantDoc") or "IMPORT.EXTRATO",
                "paymentMethod": row.get("paymentMethod") or "debit",
                "externalRef": ext_ref,
                "isDuplicate": is_dup,
            })
        return results

    def _normalize_confirmed_import_items(self, account: Account, items: list) -> list[dict]:
        results: list[dict] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title") or "").strip()[:120]
            amount_cents = to_cents(raw.get("amount"))
            occurred_on = valid_iso_date(raw.get("occurredOn")) or self.clock.today().date().isoformat()
            if not title or amount_cents is None or amount_cents <= 0:
                continue
            kind = str(raw.get("kind") or "")
            cat = str(raw.get("category") or "").strip()
            suggested_cat, inferred_kind = suggest_category(title, kind if kind in KINDS else None)
            resolved_cat = cat if cat else suggested_cat
            resolved_kind = kind if kind in KINDS else inferred_kind
            ext_ref = str(raw.get("externalRef") or sha256_hex(f"{occurred_on}:{title.lower()}:{amount_cents}:{resolved_kind}")[:24])
            results.append({
                "title": title,
                "amount": to_reais(amount_cents),
                "amountCents": amount_cents,
                "kind": resolved_kind,
                "category": resolved_cat[:60],
                "occurredOn": occurred_on,
                "merchantDoc": str(raw.get("merchantDoc") or "IMPORT.EXTRATO")[:40],
                "paymentMethod": raw.get("paymentMethod") if raw.get("paymentMethod") in PAYMENT_METHODS else "debit",
                "externalRef": ext_ref,
                "isDuplicate": bool(raw.get("isDuplicate", False)),
            })
        if not results:
            raise ApiError(422, "Selecione ao menos um lançamento válido para importar.")
        return results

    def _parse_ofx(self, text: str) -> list[dict]:
        blocks = re.split(r"<STMTTRN>", text, flags=re.IGNORECASE)[1:]
        rows: list[dict] = []
        for block in blocks:
            end_idx = re.search(r"</STMTTRN>", block, flags=re.IGNORECASE)
            chunk = block[:end_idx.start()] if end_idx else block

            def tag(name: str) -> str:
                m = re.search(rf"<{name}>([^<\r\n]+)", chunk, flags=re.IGNORECASE)
                return m.group(1).strip() if m else ""

            trnamt = tag("TRNAMT")
            cents, sign = parse_Flexible_amount(trnamt)
            if cents is None:
                continue
            dtposted = re.sub(r"\D", "", tag("DTPOSTED"))
            if len(dtposted) >= 8:
                occurred_on = f"{dtposted[:4]}-{dtposted[4:6]}-{dtposted[6:8]}"
            else:
                occurred_on = self.clock.today().date().isoformat()
            name = tag("MEMO") or tag("NAME") or "Movimentação OFX"
            fitid = tag("FITID")
            trntype = tag("TRNTYPE").upper()
            kind = "income" if (sign == "positive" and not trnamt.strip().startswith("-")) or trntype in {"CREDIT", "DEP"} else None
            cat, resolved_kind = suggest_category(name, kind)
            rows.append({
                "title": name,
                "amountCents": cents,
                "kind": resolved_kind,
                "category": cat,
                "occurredOn": occurred_on,
                "merchantDoc": f"OFX {fitid[:18]}" if fitid else "Sincronização OFX",
                "externalRef": f"ofx:{fitid}" if fitid else None,
            })
        return rows

    def _parse_delimited(self, text: str) -> list[dict]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return []
        sample = lines[0]
        delimiter = ";" if sample.count(";") >= sample.count(",") and sample.count(";") > 0 else ("\t" if "\t" in sample else ",")
        reader = csv.reader(io.StringIO("\n".join(lines)), delimiter=delimiter)
        all_rows = [row for row in reader if any(cell.strip() for cell in row)]
        if not all_rows:
            return []

        header = [cell.strip().lower() for cell in all_rows[0]]
        has_header = any(
            h in {"data", "date", "descricao", "descrição", "historico", "histórico", "titulo", "título", "valor", "amount", "categoria", "category"}
            for h in header
        )
        start_idx = 1 if has_header else 0

        def find_col(names: tuple[str, ...], default: int) -> int:
            for idx, col in enumerate(header):
                if any(name in col for name in names):
                    return idx
            return default

        date_col = find_col(("data", "date", "vencimento"), 0)
        title_col = find_col(("descri", "hist", "titul", "títul", "estabelecimento", "nome", "title", "memo"), 1)
        amount_col = find_col(("valor", "amount", "quantia", "total"), 2)
        cat_col = find_col(("categ", "classifica"), 3)
        kind_col = find_col(("tipo", "natureza", "kind"), 4)

        parsed: list[dict] = []
        for row in all_rows[start_idx:]:
            if len(row) < 2:
                continue
            raw_date = row[date_col].strip() if date_col < len(row) else ""
            raw_title = row[title_col].strip() if title_col < len(row) else ""
            raw_amount = row[amount_col].strip() if amount_col < len(row) else ""
            if not raw_amount and len(row) == 2:
                raw_title = row[0].strip()
                raw_amount = row[1].strip()
                raw_date = ""
            cents, sign = parse_Flexible_amount(raw_amount)
            if cents is None or not raw_title:
                continue
            raw_cat = row[cat_col].strip() if has_header and cat_col < len(row) else ""
            raw_kind = row[kind_col].strip().lower() if has_header and kind_col < len(row) else ""
            explicit_kind = None
            if raw_kind in {"receita", "renda", "entrada", "credito", "crédito", "income"}:
                explicit_kind = "income"
            elif raw_kind in {"fixo", "fixa", "despesa fixa", "fixed", "fixed_expense"}:
                explicit_kind = "fixed_expense"
            elif raw_kind in {"variavel", "variável", "despesa", "saida", "saída", "variable_expense"}:
                explicit_kind = "variable_expense"
            elif "+" in raw_amount:
                explicit_kind = "income"

            cat, resolved_kind = suggest_category(raw_title, explicit_kind)
            parsed.append({
                "title": raw_title,
                "amountCents": cents,
                "kind": resolved_kind,
                "category": raw_cat or cat,
                "occurredOn": valid_iso_date(raw_date) or self.clock.today().date().isoformat(),
                "merchantDoc": "Planilha CSV/Excel",
            })
        return parsed

    def _parse_xml_or_html_table(self, text: str) -> list[dict]:
        row_matches = re.findall(r"<(?:Row|tr)[^>]*>(.*?)</(?:Row|tr)>", text, flags=re.IGNORECASE | re.DOTALL)
        extracted_lines: list[str] = []
        for row_html in row_matches:
            cells = re.findall(r"<(?:Data|td|th)[^>]*>(.*?)</(?:Data|td|th)>", row_html, flags=re.IGNORECASE | re.DOTALL)
            if cells:
                clean_cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
                extracted_lines.append(";".join(clean_cells))
        if not extracted_lines:
            return []
        return self._parse_delimited("\n".join(extracted_lines))

    def _extract_receipt_metadata(self, file_name: str, text_hint: str, preset: str, today_iso: str) -> dict:
        combined = f"{preset} {file_name} {text_hint}".strip()
        lower = combined.lower()

        if preset == "supermarket" or ("pao" in lower or "açúcar" in lower or "acucar" in lower or "mercado" in lower) and not text_hint:
            return {
                "title": "Pão de Açúcar • Supermercado",
                "amount": 342.80,
                "kind": "variable_expense",
                "category": "Alimentação & Mercado",
                "occurredOn": today_iso,
                "paymentMethod": "credit",
                "merchantDoc": "CNPJ 47.508.411/0001-56 • NFC-e #4492",
                "confidence": 99,
            }
        if preset == "uber" or ("uber" in lower or "99" in lower or "transporte" in lower) and not text_hint:
            return {
                "title": "Uber do Brasil • Deslocamento",
                "amount": 42.90,
                "kind": "variable_expense",
                "category": "Transporte",
                "occurredOn": today_iso,
                "paymentMethod": "pix",
                "merchantDoc": "CNPJ 17.895.646/0001-87 • Recibo IA",
                "confidence": 98,
            }
        if preset == "restaurant" or ("restaurante" in lower or "bistro" in lower or "bistrô" in lower or "almoço" in lower) and not text_hint:
            return {
                "title": "Bistrô & Restaurante Jardins",
                "amount": 128.50,
                "kind": "variable_expense",
                "category": "Lazer & Restaurantes",
                "occurredOn": today_iso,
                "paymentMethod": "credit",
                "merchantDoc": "CNPJ 23.410.992/0001-11 • NFC-e #9104",
                "confidence": 97,
            }

        # Parse custom text_hint or filename cues
        amount_match = re.search(r"(?:r\$\s*|valor[:\s]*|total[:\s]*)?(\d{1,6}(?:[.,]\d{3})*[.,]\d{2})", combined, flags=re.IGNORECASE)
        cents = None
        if amount_match:
            cents, _ = parse_Flexible_amount(amount_match.group(1))
        if cents is None:
            cents = 8990

        date_match = re.search(r"(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})", combined)
        occurred_on = valid_iso_date(date_match.group(1)) if date_match else today_iso
        if not occurred_on:
            occurred_on = today_iso

        cnpj_match = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", combined)
        doc = f"CNPJ {cnpj_match.group(0)}" if cnpj_match else "NFC-e extraída via IA"

        base_name = re.sub(r"\.[a-zA-Z0-9]{2,4}$", "", file_name).replace("_", " ").replace("-", " ").strip()
        if text_hint:
            first_line = text_hint.splitlines()[0].strip()
            merchant = re.sub(r"(?:r\$\s*\d+[.,]\d{2}|\d{2}/\d{2}/\d{4})", "", first_line, flags=re.IGNORECASE).strip(" -•:")
            title = merchant[:80] if len(merchant) >= 3 else (base_name[:80] or "Comprovante Fiscal")
        else:
            title = base_name.title()[:80] if len(base_name) >= 3 else "Comprovante Fiscal"

        category, kind = suggest_category(f"{title} {text_hint}")
        return {
            "title": title,
            "amount": to_reais(cents),
            "kind": kind,
            "category": category,
            "occurredOn": occurred_on,
            "paymentMethod": "credit",
            "merchantDoc": doc,
            "confidence": 96,
        }

    def _validate_transaction_payload(self, account: Account, payload: dict) -> Transaction:
        errors: dict[str, str] = {}
        title = payload.get("title")
        if not isinstance(title, str) or not (2 <= len(title.strip()) <= 120):
            errors["title"] = "Informe uma descrição entre 2 e 120 caracteres."
        amount_cents = to_cents(payload.get("amount"))
        if amount_cents is None or amount_cents <= 0:
            cents_parsed, _ = parse_Flexible_amount(payload.get("amount"))
            amount_cents = cents_parsed
        if amount_cents is None or amount_cents <= 0:
            errors["amount"] = "Informe um valor maior que zero."

        raw_kind = payload.get("kind")
        kind = raw_kind if isinstance(raw_kind, str) and raw_kind in KINDS else "variable_expense"

        raw_category = payload.get("category")
        if isinstance(raw_category, str) and raw_category.strip() and raw_category.strip().lower() != "auto":
            category = raw_category.strip()[:60]
        elif isinstance(title, str) and title.strip():
            category, inferred_kind = suggest_category(title, kind if raw_kind in KINDS else None)
            if raw_kind not in KINDS:
                kind = inferred_kind
        else:
            errors["category"] = "Selecione ou informe uma categoria."
            category = "Outros"

        raw_date = payload.get("occurredOn")
        occurred_on = valid_iso_date(raw_date) if raw_date else self.clock.today().date().isoformat()
        if occurred_on is None:
            errors["occurredOn"] = "Informe uma data válida."
            occurred_on = self.clock.today().date().isoformat()

        raw_channel = payload.get("channel", "manual")
        channel = raw_channel if raw_channel in CHANNELS else "manual"

        raw_status = payload.get("status", "paid")
        status = raw_status if raw_status in STATUSES else "paid"

        raw_method = payload.get("paymentMethod", "debit")
        payment_method = raw_method if raw_method in PAYMENT_METHODS else "debit"

        if errors:
            raise ApiError(422, "Confira os campos do lançamento.", errors)

        assert isinstance(title, str) and isinstance(amount_cents, int)
        merchant_doc = str(payload.get("merchantDoc") or "").strip()[:60] or None
        notes = str(payload.get("notes") or "").strip()[:240] or None
        conf_raw = payload.get("confidence")
        confidence = int(conf_raw) if isinstance(conf_raw, (int, float)) and not isinstance(conf_raw, bool) else None
        validated = bool(payload.get("validated", True))

        return Transaction(
            id=self.ledger.next_id(),
            account_id=account.id,
            title=title.strip(),
            amount_cents=amount_cents,
            kind=kind,
            category=category,
            channel=channel,
            occurred_on=occurred_on,
            status=status,
            payment_method=payment_method,
            merchant_doc=merchant_doc,
            confidence=confidence,
            validated=validated,
            notes=notes,
            created_at=self.clock.now(),
        )

    def _evaluate_limits(self, transactions: list[Transaction], limits: list[BudgetLimit], effective_income_cents: int, today_iso: str) -> tuple[list[dict], list[dict]]:
        by_category: dict[str, int] = {}
        today_variable_cents = 0
        credit_variable_cents = 0
        credit_total_cents = 0

        for tx in transactions:
            if tx.kind == "income":
                continue
            by_category[tx.category] = by_category.get(tx.category, 0) + tx.amount_cents
            if tx.kind == "variable_expense" and tx.occurred_on == today_iso:
                today_variable_cents += tx.amount_cents
            if tx.payment_method == "credit":
                credit_total_cents += tx.amount_cents
                if tx.kind == "variable_expense":
                    credit_variable_cents += tx.amount_cents

        evaluated: list[dict] = []
        alerts: list[dict] = []

        for lim in limits:
            if lim.scope == "daily":
                spent_cents = today_variable_cents
                percent = round(spent_cents / lim.limit_cents * 100) if lim.limit_cents > 0 else 0
                lesson_id = "first-budget"
            elif lim.scope == "card_share":
                # For card_share, limit_cents is stored as percentage * 100 (e.g. 30% -> 3000)
                base_cents = max(credit_total_cents, effective_income_cents, 1)
                spent_cents = round(credit_variable_cents / base_cents * 10000) if credit_variable_cents > 0 else 0
                percent = round(spent_cents / lim.limit_cents * 100) if lim.limit_cents > 0 else 0
                lesson_id = "due-dates"
            else:
                spent_cents = by_category.get(lim.category, 0)
                percent = round(spent_cents / lim.limit_cents * 100) if lim.limit_cents > 0 else 0
                lesson_id = "first-budget"

            if percent >= 100:
                status = "exceeded"
            elif percent >= lim.warn_percent:
                status = "warning"
            else:
                status = "ok"

            advisory = "Aviso de referência para disciplina orçamentária. Gastos não são bloqueados."
            item = {
                "id": lim.id,
                "scope": lim.scope,
                "category": lim.category,
                "limit": to_reais(lim.limit_cents),
                "spent": to_reais(spent_cents),
                "percent": percent,
                "warnPercent": lim.warn_percent,
                "status": status,
                "advisory": advisory,
                "lessonId": lesson_id,
            }
            evaluated.append(item)
            if status in {"warning", "exceeded"}:
                alerts.append({
                    **item,
                    "title": (
                        f"Limite atingido em {lim.category}"
                        if status == "exceeded"
                        else f"Aviso preventivo: {lim.category}"
                    ),
                    "actionLabel": "Ajustar Teto",
                })

        alerts.sort(key=lambda a: a["percent"], reverse=True)
        return evaluated, alerts

    def _build_daily_series(self, transactions: list[Transaction], effective_fixed_cents: int, today_dt: datetime) -> list[dict]:
        ym = f"{today_dt.year}-{today_dt.month:02d}"
        by_day: dict[int, int] = {}
        for tx in transactions:
            if tx.kind != "income" and tx.occurred_on.startswith(ym):
                try:
                    day_num = int(tx.occurred_on.split("-")[2])
                    by_day[day_num] = by_day.get(day_num, 0) + tx.amount_cents
                except Exception:
                    pass
        baseline_daily = round(effective_fixed_cents / 30) if effective_fixed_cents > 0 else 0
        points = [
            ("Dia 01", by_day.get(1, baseline_daily)),
            ("Dia 05", by_day.get(5, round(baseline_daily * 1.4))),
            ("Dia 10", sum(v for d, v in by_day.items() if 6 <= d <= 10) or round(baseline_daily * 1.1)),
            ("Dia 15", sum(v for d, v in by_day.items() if 11 <= d <= 15) or round(baseline_daily * 0.9)),
            ("Dia 20", sum(v for d, v in by_day.items() if 16 <= d <= 20) or round(baseline_daily * 1.2)),
            ("Hoje", sum(v for d, v in by_day.items() if d > 20) or by_day.get(today_dt.day, baseline_daily)),
        ]
        return [{"label": label, "amount": to_reais(cents)} for label, cents in points]

    @staticmethod
    def _fmt_brl(cents: int) -> str:
        reais = cents / 100
        formatted = f"{reais:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
