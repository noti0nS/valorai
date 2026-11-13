<div align="center">

# ValorAI

**Plataforma de gestão financeira pessoal com fluxo de cadastro, controle de gastos, metas, guias educativos e consultor financeiro por IA.**

[![Demo](https://img.shields.io/badge/demo-workers.dev-orange?style=flat-square)](https://valorai-prototype.joselucas0303.workers.dev)
[![Astro](https://img.shields.io/badge/Astro-7-BC52EE?style=flat-square&logo=astro&logoColor=white)](https://astro.build/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare-Python%20Worker%20%2B%20D1-F38020?style=flat-square&logo=cloudflare&logoColor=white)](https://developers.cloudflare.com/workers/)

[Acessar Demonstração](https://valorai-prototype.joselucas0303.workers.dev) · [Arquitetura](ARCHITECTURE.md) · [Registros de Decisão (ADRs)](docs/adr/)

</div>

---

## Visão Geral

O **ValorAI** é um protótipo funcional da *Nulfinance Inc.* construído sobre uma arquitetura serverless na borda (**Astro + React 19** no frontend e **Django em Cloudflare Python Worker** no backend, coordenado por um **Durable Object** com persistência em **Cloudflare D1**).

O fluxo principal cobre desde o cadastro com proteção anti-bot até o painel operacional em Bento Grid:

```text
Login / Cadastro (Turnstile) ──▶ Confirmação (Demo Inbox) ──▶ Perfil Financeiro ──▶ Painel Stitch
                                                                                        ├── Visão Geral + Resumo IA
                                                                                        ├── Transações & Extratos (Manual, OFX/CSV, Comprovante IA)
                                                                                        ├── Planejamento & Metas (Limites não bloqueantes)
                                                                                        └── Guias Práticos (Markdown)
```

---

## Funcionalidades

### Autenticação, Cadastro e Perfil
- **Cadastro e validação compartilhada:** Zod no navegador ([`shared/validation.ts`](shared/validation.ts)) espelhado no servidor ([`account/validation.py`](server/python/valorai/account/validation.py)), com verificação de CPF/e-mail únicos e idade mínima de 16 anos.
- **Preenchimento assistido de endereço:** Consulta automática de CEP via **ViaCEP** e municípios via **IBGE**, com fallback manual.
- **Segurança de sessão:** Senhas com `bcrypt` (custo 10), cookies `HttpOnly` / `SameSite=Strict` / `Secure`, expiração por inatividade (30 min) e teto de sessão (12 h).
- **Manutenção e desativação:** Edição de dados pessoais e avatar (JPG/PNG/WebP até 2 MB) e desativação lógica com revogação de sessões e preservação do histórico financeiro.
- **Trilha de auditoria no banco:** Triggers genéricos SQLite gerados para D1 ([`0009_generic_audit.sql`](server/migrations/0009_generic_audit.sql)).

### Gestão Financeira e Inteligência Artificial
- **Três canais de lançamento:**
  1. **Manual:** Lançamento rápido com sugestão automática de categoria por palavras-chave.
  2. **Importação de extratos:** Leitura local de arquivos **OFX** e **CSV** com pré-visualização antes de confirmar.
  3. **Leitura de comprovantes por IA:** Envio de foto ou captura por câmera com compressão client-side em `<canvas>`, extração multimodal (NFC-e, PIX, boletos, faturas) via API compatível com OpenAI e revisão humana obrigatória antes de salvar.
- **10 categorias padronizadas** e cálculo automático de comprometimento entre renda, gastos fixos, variáveis e saldo livre.
- **Limites e metas:** Tetos configuráveis por categoria, diário ou proporção de cartão com **alertas visuais não bloqueantes** (80%, 100% e excedido), além de registro de aportes em metas.
- **Consultor financeiro por IA (`POST /api/ai/summary`):**
  - Recebe apenas métricas condensadas e livres de PII, guiadas por estados determinísticos (`EXPENSE_RATIO_HIGH`, `LIMIT_EXCEEDED`, `NEAR_LIMIT`, `POSITIVE_SURPLUS`, `NO_LIMITS_SET`, `LOW_ACTIVITY`).
  - Cache em `DurableKv` invalidado apenas por **premissas materiais** (mudança de estado, objetivo, categoria líder, status de alerta ou variação `>= 15%` em renda/despesas), sem TTL fixo — evitando chamadas desnecessárias à LLM a cada movimentação ou expiração arbitrária.
  - Fallback determinístico local automático quando a IA não está configurada ou o circuit breaker (HTTP 429) está ativo.
- **Interface acessível:** Tema claro/escuro sincronizado com `prefers-color-scheme`, diálogos nativos (`<dialog closedby="any">`), animações numéricas (`NumberFlow`) e respeito a `prefers-reduced-motion`.

---

## Arquitetura e Stack

```text
Navegador ──▶ Cloudflare Static Assets (Astro + React 19 + Instrument Sans)
          └──▶ /api/* ──▶ Python Worker (Django WSGI)
                             └──▶ AuthCoordinator (Singleton Durable Object)
                                    ├── D1 (SQLite): contas, sessões, transações, limites, metas, guias, auditoria
                                    ├── DurableKv (module_kv): códigos, cooldowns, cache do resumo IA, circuit breaker
                                    ├── Turnstile: verificação anti-bot em produção
                                    └── OpenAI-Compatible API: extração de comprovantes e resumo financeiro
```

| Camada | Tecnologias |
| :--- | :--- |
| **Frontend** | Astro 7, React 19, TypeScript, Zod, Motion, Lucide, `@number-flow/react` |
| **Backend** | Python 3.14, Django (WSGI síncrono em Cloudflare Python Worker via `pywrangler`) |
| **Dados & Coordenação** | Cloudflare D1 (SQLite), Durable Object (`AuthCoordinator`), `DurableKv` |
| **Segurança** | Cloudflare Turnstile, `bcrypt` (custo 10), cookies `HttpOnly` + `SameSite=Strict` |
| **IA** | Endpoint compatível com OpenAI (padrão `gemini-3.5-flash-lite`) + fallback determinístico |
| **Testes** | `pytest` (backend em memória), `tsx --test` (Zod/validação), Playwright (E2E) |

---

## Como Executar Localmente

### Pré-requisitos
- **Node.js** `^22.23 || ^24.22 || ^26.12`
- **Python 3.14+** e [**uv**](https://docs.astral.sh/uv/) (ou **Docker Compose**)

### Opção 1: Docker Compose (Recomendado)

```bash
docker compose up --build
```

- **Aplicação completa (Worker + D1 + Assets):** `http://localhost:8787`
- **Frontend com Hot-Reload (Astro):** `http://localhost:4321` (com proxy `/api` para o Worker)
- **Executar testes no container:**
  ```bash
  docker compose run --rm test
  ```

### Opção 2: Execução Manual

1. **Instale as dependências e compile o frontend:**
   ```bash
   npm ci
   npm run build
   ```
2. **Inicie a API local** (aplica automaticamente as migrações no D1 local e sobe o Worker na porta `8787`):
   ```bash
   npm run dev:api
   ```
3. *(Opcional)* Em outro terminal, inicie o servidor Astro com HMR para desenvolvimento de UI:
   ```bash
   npm run dev
   ```

> **Modo de desenvolvimento:** com `ENVIRONMENT=development` (padrão local), o Turnstile é ignorado. Para habilitar IA localmente, configure `AI_API_KEY` em `server/python/.dev.vars`. Sem `AI_API_KEY`, o sistema opera normalmente usando extração heurística e resumo determinístico.

---

## Testes e Verificações

```bash
# Typecheck do frontend e contratos compartilhados
npm run check

# Testes unitários de validação (Zod)
npm test

# Testes unitários e de integração do backend (SQLite em memória + fakes)
uv run --directory server/python pytest

# Testes E2E com Playwright (requer `npm run build` e `npm run dev:api` ativos)
npx playwright install chromium   # apenas na primeira vez
npm run test:e2e
```

---

## Deploy (Cloudflare)

As configurações de bindings (`D1`, `Durable Objects` e variáveis públicas) ficam em [`server/python/wrangler.jsonc`](server/python/wrangler.jsonc). Os segredos (`TURNSTILE_SECRET_KEY` e `AI_API_KEY`) devem ser configurados via Wrangler secrets — nunca no repositório.

```bash
npm run deploy
```

O script executa `astro build`, aplica as migrações pendentes no D1 remoto (`--remote`) e publica o Worker no ambiente `production`.

---

## Estrutura do Projeto

```text
.
├── assets/                 # Logotipos oficiais (ValorAI e Nulfinance Inc.)
├── docs/                   # Requisitos (valorai_requisitos.docx), PRDs e ADRs (docs/adr/)
├── shared/                 # Schemas Zod, categorias e regras compartilhadas (TS)
├── src/
│   ├── components/         # RegistrationApp, DashboardWorkspace, Turnstile e tema
│   ├── pages/              # Entrada Astro (index.astro)
│   └── styles/             # Design tokens (claro/escuro) e layout Bento Grid
├── server/
│   ├── migrations/         # Migrações SQL do D1 (0001 a 0010)
│   ├── tools/              # Gerador de triggers genéricos de auditoria
│   └── python/
│       ├── valorai/        # Domínio (account, session, confirmation, finance, ledger, ai)
│       └── tests/          # Suíte pytest (42 testes)
└── tests/                  # Testes de validação (tsx) e E2E (Playwright)
```

---

## Documentação e Limites do Protótipo

- **Arquitetura detalhada:** [`ARCHITECTURE.md`](ARCHITECTURE.md) e ADRs [`0001`](docs/adr/0001-django-workers-architecture.md) a [`0007`](docs/adr/0007-openai-compatible-ai-integration.md).
- **Confirmação de e-mail simulada (`EMAIL_MODE=demo`):** nenhum e-mail real é enviado; o código de verificação fica disponível em `/api/demo-inbox` apenas para a sessão da conta pendente.
- **Escopo financeiro:** o painel é uma ferramenta de planejamento pessoal e não realiza sincronização bancária via Open Finance nem recomendações de investimento.
- **Dados de teste:** utilize dados fictícios no ambiente de demonstração.
