from valorai.account.validation import registration_from
from valorai.errors import ApiError
from valorai.ledger.module import suggest_category

from conftest import NOW, registration
from test_account import pytest_raises
from test_http import cookie_of, post


def _confirmed_account(world):
    account = world["account"].create(registration_from(registration(), world["clock"].today()), "ip")
    confirmed = world["account"].mark_demo_confirmed(account, "ip")
    updated = world["finance"].update(confirmed, {"income": 6200, "fixedExpenses": 3750, "goal": "reserve"}, "ip")
    return updated


def test_category_auto_suggestion_and_mandatory_categorization(world):
    account = _confirmed_account(world)
    assert suggest_category("Pão de Açúcar Supermercado")[0] == "Alimentação"
    assert suggest_category("Uber do Brasil")[0] == "Transporte"
    assert suggest_category("Aluguel Residencial")[0] == "Moradia"
    assert suggest_category("Consultoria Recebida", "income")[0] == "Renda"

    dash = world["ledger"].handle_transaction(
        account,
        {"action": "create", "title": "Pão de Açúcar", "amount": 342.80, "kind": "variable_expense", "category": "auto"},
        "ip",
    )
    assert len(dash["transactions"]) == 1
    tx = dash["transactions"][0]
    assert tx["category"] == "Alimentação"
    assert tx["amount"] == 342.8
    assert dash["summary"]["freeBalance"] == 2107.2


def test_budget_limits_trigger_non_blocking_alerts(world):
    account = _confirmed_account(world)
    world["ledger"].handle_limit(
        account,
        {"action": "upsert", "scope": "category", "category": "Lazer", "limit": 600, "warnPercent": 80},
        "ip",
    )
    dash = world["ledger"].handle_transaction(
        account,
        {
            "action": "create",
            "title": "Restaurante Jardins",
            "amount": 550,
            "kind": "variable_expense",
            "category": "Lazer",
        },
        "ip",
    )
    assert len(dash["alerts"]) == 1
    alert = dash["alerts"][0]
    assert alert["category"] == "Lazer"
    assert alert["percent"] == 92
    assert alert["status"] == "warning"
    assert "não são bloqueados" in alert["advisory"]

    # Exceeding the limit still saves the transaction and elevates alert to 'exceeded'
    dash2 = world["ledger"].handle_transaction(
        account,
        {
            "action": "create",
            "title": "Cinema IMAX",
            "amount": 90,
            "kind": "variable_expense",
            "category": "Lazer",
        },
        "ip",
    )
    assert len(dash2["transactions"]) == 2
    assert dash2["alerts"][0]["status"] == "exceeded"
    assert dash2["alerts"][0]["percent"] == 107


def test_ofx_and_csv_import_with_deduplication(world):
    account = _confirmed_account(world)
    ofx_sample = """
    OFXHEADER:100
    <OFX>
      <BANKMSGSRSV1>
        <STMTTRNRS>
          <STMTRS>
            <BANKTRANLIST>
              <STMTTRN>
                <TRNTYPE>DEBIT
                <DTPOSTED>20261005080000
                <TRNAMT>-2400.00
                <FITID>FIT-2026-001
                <MEMO>Aluguel e Condominio
              </STMTTRN>
              <STMTTRN>
                <TRNTYPE>CREDIT
                <DTPOSTED>20261001110000
                <TRNAMT>1200.00
                <FITID>FIT-2026-002
                <MEMO>Consultoria e Servicos
              </STMTTRN>
            </BANKTRANLIST>
          </STMTRS>
        </STMTTRNRS>
      </BANKMSGSRSV1>
    </OFX>
    """
    preview = world["ledger"].handle_import(account, {"format": "ofx", "fileName": "extrato.ofx", "content": ofx_sample, "preview": True}, "ip")
    assert preview["preview"] is True
    assert preview["totalCount"] == 2
    assert preview["duplicateCount"] == 0

    imported = world["ledger"].handle_import(account, {"format": "ofx", "fileName": "extrato.ofx", "content": ofx_sample, "preview": False}, "ip")
    assert imported["importResult"]["importedCount"] == 2
    assert imported["importResult"]["duplicateCount"] == 0

    # Re-importing the same OFX skips duplicates
    reimported = world["ledger"].handle_import(account, {"format": "ofx", "fileName": "extrato.ofx", "content": ofx_sample, "preview": False}, "ip")
    assert reimported["importResult"]["importedCount"] == 0
    assert reimported["importResult"]["duplicateCount"] == 2

    # CSV import
    csv_sample = "Data;Descrição;Valor;Categoria\n04/10/2026;Uber do Brasil;-42,90;Transporte\n02/10/2026;Livraria Cultura;-119,00;Educação"
    csv_imported = world["ledger"].handle_import(account, {"format": "csv", "fileName": "planilha.csv", "content": csv_sample, "preview": False}, "ip")
    assert csv_imported["importResult"]["importedCount"] == 2
    assert len(csv_imported["transactions"]) == 4


def test_receipt_ai_extraction_and_confirmation(world):
    account = _confirmed_account(world)
    preview = world["ledger"].handle_receipt(
        account,
        {"fileName": "cupom_supermercado.jpg", "preset": "supermarket", "confirm": False},
        "ip",
    )
    extracted = preview["extracted"]
    assert extracted["category"] == "Alimentação"
    assert extracted["amount"] == 342.8
    assert extracted["confidence"] >= 95

    saved = world["ledger"].handle_receipt(
        account,
        {"confirm": True, "transaction": extracted},
        "ip",
    )
    assert len(saved["transactions"]) == 1
    assert saved["transactions"][0]["channel"] == "photo"
    assert saved["transactions"][0]["validated"] is True


def test_rf003_profile_maintenance_and_rs001_isolation(world):
    api = world["api"]
    created = post(api, "/api/register", registration())
    owner_cookie = cookie_of(created)
    inbox = api.handle("GET", "http://127.0.0.1:8787/api/demo-inbox", {"cookie": owner_cookie}, b"")
    confirmed = post(api, "/api/confirm", {"code": inbox.body["code"]}, owner_cookie)
    owner_cookie = cookie_of(confirmed)
    post(api, "/api/finance", {"income": 5000, "fixedExpenses": 2500, "goal": "reserve"}, owner_cookie)

    # Attempt to change CPF must be rejected (RF003)
    bad_cpf = post(
        api,
        "/api/profile",
        {
            "name": "José Lucas Silva",
            "cpf": "123.456.789-01",
            "birthDate": "1995-06-15",
            "phone": "(82) 98888-7777",
            "postalCode": "57030-000",
            "state": "AL",
            "city": "Maceió",
        },
        owner_cookie,
    )
    assert bad_cpf.status == 422
    assert "inalterável" in bad_cpf.body["fields"]["cpf"]

    # Valid profile update records history
    ok_profile = post(
        api,
        "/api/profile",
        {
            "name": "José Lucas Silva",
            "birthDate": "1995-06-15",
            "phone": "(82) 98888-7777",
            "postalCode": "57030-000",
            "state": "AL",
            "city": "Arapiraca",
        },
        owner_cookie,
    )
    assert ok_profile.status == 200
    assert ok_profile.body["account"]["name"] == "José Lucas Silva"
    assert ok_profile.body["profile"]["city"] == "Arapiraca"
    assert len(ok_profile.body["profile"]["history"]) == 1


def test_limit_reports_reached_at_exactly_100_percent_and_never_blocks(world):
    account = _confirmed_account(world)
    world["ledger"].handle_limit(
        account,
        {"action": "upsert", "scope": "category", "category": "Lazer", "limit": 600, "warnPercent": 80},
        "ip",
    )
    dash = world["ledger"].handle_transaction(
        account,
        {"action": "create", "title": "Show", "amount": 600, "kind": "variable_expense", "category": "Lazer"},
        "ip",
    )
    assert dash["alerts"][0]["status"] == "reached"
    assert dash["alerts"][0]["percent"] == 100
    assert "atingido" in dash["alerts"][0]["title"].lower()
    assert len(dash["transactions"]) == 1


def test_non_standard_categories_are_rejected(world):
    import pytest
    from valorai.errors import ApiError

    account = _confirmed_account(world)
    with pytest.raises(ApiError) as error:
        world["ledger"].handle_transaction(
            account,
            {"action": "create", "title": "Algo", "amount": 10, "kind": "variable_expense", "category": "Inventada"},
            "ip",
        )
    assert error.value.status == 422
    with pytest.raises(ApiError):
        world["ledger"].handle_limit(
            account, {"action": "upsert", "scope": "category", "category": "Inventada", "limit": 10}, "ip"
        )


def test_weekly_limit_evaluates_current_week_expenses(world):
    account = _confirmed_account(world)
    today = world["clock"].today().date()
    today_iso = today.isoformat()
    from datetime import timedelta
    last_month_iso = (today - timedelta(days=21)).isoformat()

    world["ledger"].handle_limit(
        account,
        {"action": "upsert", "scope": "weekly", "limit": 400, "warnPercent": 80},
        "ip",
    )
    # Expense outside current week should not count toward weekly limit
    world["ledger"].handle_transaction(
        account,
        {"action": "create", "title": "Antiga", "amount": 500, "kind": "variable_expense", "category": "Outros", "occurredOn": last_month_iso},
        "ip",
    )
    dash = world["ledger"].handle_transaction(
        account,
        {"action": "create", "title": "Semana", "amount": 350, "kind": "variable_expense", "category": "Alimentação", "occurredOn": today_iso},
        "ip",
    )
    weekly = [lim for lim in dash["limits"] if lim["scope"] == "weekly"][0]
    assert weekly["category"] == "Teto Semanal"
    assert weekly["spent"] == 350
    assert weekly["status"] == "warning"
    assert weekly["percent"] == 88
