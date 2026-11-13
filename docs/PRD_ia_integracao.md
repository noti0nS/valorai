# PRD — Integração de IA no ValorAI (Extração de Recibos & Resumo Financeiro)

**Versão:** 1.0 (Draft para Avaliação)  
**Data:** 2026-11-13  
**Status:** Em revisão  
**Modelo Inicial:** `gemini-3.5-flash-lite` (Google AI Studio — Free Tier)  
**Padrão de Integração:** OpenAI-Compatible API (agnóstico de provedor)

---

## 1. Executive Summary

### Problem Statement
Usuários do ValorAI frequentemente utilizam smartphones de entrada (*low-cost*) em redes móveis limitadas e precisam registrar despesas manualmente ou a partir de fotos de cupons fiscais e comprovantes PIX. Atualmente, o endpoint `/api/transactions/receipt` utiliza apenas heurísticas determinísticas por nome de arquivo (`_extract_receipt_metadata`), e a tela inicial (*Visão Geral*) apresenta métricas estáticas sem interpretação personalizada dos padrões de gasto do usuário.

### Proposed Solution
Integrar uma camada de IA **agnóstica de provedor** compatível com a **OpenAI-Compatible API** (iniciando com `gemini-3.5-flash-lite` via Google AI Studio), executada integralmente no backend (Cloudflare Python Worker) após compressão leve da imagem no navegador. A solução entrega:
1. **Extração multimodal de comprovantes** (foto/print → transação estruturada nas categorias padronizadas do ValorAI, com revisão humana obrigatória).
2. **Resumo financeiro inteligente na Home** com recomendações customizadas geradas a partir de dados condensados e estados determinísticos calculados no backend, protegidos por cache para respeitar as cotas do Free Tier.

### Success Criteria (KPIs)
- **Acurácia de extração (valor exato):** `>= 95%` em um conjunto de avaliação com 50 comprovantes reais brasileiros cobrindo cupom fiscal (NFC-e/SAT), comprovante PIX, boleto bancário, fatura de cartão e recibo de maquininha.
- **Acurácia de categorização:** `>= 85%` de acerto direto dentro de `STANDARD_CATEGORIES` sem edição manual do usuário.
- **Conformidade de schema JSON:** `100%` das respostas parseadas sem falha de contrato (via *Structured Outputs* + validação defensiva no backend).
- **Performance em mobile low-cost:** Payload de imagem comprimida `<= 350 KB` antes do upload e tempo total de extração P95 `<= 5s` em 4G.
- **Resiliência e economia de cota:** `0%` de bloqueio do fluxo de lançamento em caso de erro/429 da API (100% de fallback para heurística determinística) e taxa de *cache hit* `>= 80%` no resumo da Home.

---

## 2. User Experience & Functionality

### User Personas
- **Cliente ValorAI (Mobile-first / Low-cost):** Pessoa física buscando organizar orçamento, sair das dívidas ou montar reserva financeira usando um celular com pouca RAM/CPU e franquia de dados limitada, que precisa registrar gastos rapidamente tirando foto do cupom ou print do PIX e entender sua situação financeira em segundos.

### User Stories & Acceptance Criteria

#### US-01 — Extração de Transação a partir de Qualquer Comprovante (Foto ou Print)
> *Como usuário do ValorAI, quero enviar a foto ou print de qualquer comprovante financeiro (cupom fiscal, PIX, boleto, fatura de cartão, TED/DOC ou recibo de maquininha) para que o sistema capture corretamente o valor e preencha a transação antes de eu confirmar.*

**Acceptance Criteria:**
- [ ] O frontend redimensiona e comprime a imagem no navegador via `<canvas>` (largura máxima `1280px`, formato JPEG qualidade `0.75–0.80`, limite alvo `<= 350 KB`) antes de chamar `POST /api/transactions/receipt`.
- [ ] A extração suporta múltiplos formatos brasileiros: **cupom fiscal (NFC-e/SAT)**, **comprovante PIX** (enviado ou recebido), **boleto bancário**, **fatura de cartão de crédito**, **TED/DOC** e **comprovante de maquininha**.
- [ ] Em documentos com múltiplos valores (ex.: fatura de cartão com *valor total*, *pagamento mínimo* e *parcelamento*; boleto com *valor do documento*, *juros/desconto* e *valor pago*; cupom com *subtotal* e *total*), o modelo prioriza o **valor efetivamente pago** (ou o **valor total da fatura/documento** quando ainda não quitado) e preenche `amount` corretamente.
- [ ] O backend envia a imagem comprimida para o provedor OpenAI-Compatible e retorna `title`, `amount` (em reais/centavos válidos), `occurredOn` (`YYYY-MM-DD`), `category` (obrigatoriamente um item de `STANDARD_CATEGORIES`), `kind`, `paymentMethod`, `merchantDoc` (quando visível) e `confidence` (`0–100`).
- [ ] A transação **nunca** é salva automaticamente no D1: o modal de revisão no `DashboardWorkspace` exibe os campos preenchidos com o selo de confiança da IA e exige confirmação explícita do usuário (`action: "confirm"`).
- [ ] Caso a API de IA falhe, exceda o timeout ou retorne `429` (cota atingida), o backend aciona automaticamente o fallback heurístico (`_extract_receipt_metadata`) e sinaliza na resposta que a extração foi por fallback (`source: "fallback"`), permitindo que o usuário edite e salve normalmente.

#### US-02 — Resumo Financeiro e Recomendações Customizadas na Home
> *Como usuário do ValorAI, quero ver na Visão Geral um resumo curto (3 a 5 linhas) do meu momento financeiro atual com recomendações práticas personalizadas para saber onde ajustar meus gastos sem precisar analisar gráficos complexos.*

**Acceptance Criteria:**
- [ ] A aba *Visão Geral* exibe um card dedicado de **Análise & Recomendações (IA)** contendo um resumo conciso (máximo ~450 caracteres / 3–4 frases) e até 2–3 recomendações acionáveis.
- [ ] O prompt nunca recebe o histórico bruto de transações; o backend calcula primeiro os **estados determinísticos** (ex.: `LIMIT_EXCEEDED`, `NEAR_LIMIT`, `DAILY_CAP_RISK`, `POSITIVE_SURPLUS`, `NO_LIMITS_CONFIGURED`, `INSUFFICIENT_DATA`) e injeta apenas métricas condensadas no modelo.
- [ ] O resultado fica em **cache no backend** (`DurableKv`) indexado por conta + hash do estado do ledger/limites + TTL (ex.: `6 horas`), sendo invalidado apenas quando o usuário cria/edita/exclui transações, altera limites ou solicita atualização manual (respeitando cooldown mínimo para proteger o Free Tier).
- [ ] Em caso de indisponibilidade da IA ou `429`, o card exibe um resumo determinístico gerado localmente a partir dos mesmos estados calculados (sem quebrar o carregamento do `dashboard`).

#### US-03 — Transparência de Privacidade no Protótipo (Free Tier)
> *Como usuário testando o protótipo no Free Tier, quero ser informado claramente quando a funcionalidade de IA estiver rodando em modo de demonstração/Free Tier para não enviar documentos sensíveis reais antes da virada para produção.*

**Acceptance Criteria:**
- [ ] Quando `AI_TIER == "free_prototype"`, a UI exibe um aviso discreto nos pontos de entrada da IA (modal de foto e card de resumo) informando que o ambiente está em protótipo Free Tier e recomendando não enviar dados bancários sensíveis reais.
- [ ] A troca para produção (*Pay-as-you-go*, onde o Google não utiliza dados para treinamento) requer apenas alteração de variável/secret no Wrangler (`AI_TIER=paid` e `AI_API_KEY`), sem mudança de código.

### Non-Goals (Fora de Escopo nesta v1.0)
- Processamento de IA ou OCR local no dispositivo do usuário (WebGPU / TFLite / Tesseract.js).
- Salvamento automático de transações sem revisão manual do usuário.
- Extração em lote de múltiplos comprovantes em uma única chamada.
- Chat conversacional aberto (*chatbot*) ou integração com Open Finance / bancos.
- Armazenamento permanente das imagens originais dos comprovantes em Blob Storage (R2 fica para v2.0).

---

## 3. AI System Requirements

### 3.1 Arquitetura Agnóstica via OpenAI-Compatible API
Toda comunicação com LLM/VLM será encapsulada atrás de um protocolo único (`AiProvider`) usando o contrato padrão OpenAI Chat Completions (`POST {AI_BASE_URL}/chat/completions`):

- **Provedor inicial (Google AI Studio):**
  - `AI_BASE_URL`: `https://generativelanguage.googleapis.com/v1beta/openai/`
  - `AI_MODEL`: `gemini-3.5-flash-lite`
  - `AI_API_KEY`: armazenada exclusivamente como Wrangler Secret (nunca no repositório).
- **Portabilidade:** A troca para OpenAI, Cloudflare AI Gateway, OpenRouter, Groq ou vLLM local exige apenas atualizar `AI_BASE_URL`, `AI_MODEL` e `AI_API_KEY`.
- **Structured Outputs:** Utilizar `response_format: { "type": "json_schema", "json_schema": { ... } }` (com fallback de parsing/validação Pydantic/manual caso algum endpoint OpenAI-compatible futuro não suporte `strict: true`).

### 3.2 Contratos de Prompt e Saída

#### A) Extração de Comprovantes (Visão + JSON)
- **Entrada:** Imagem JPEG base64 (`detail: "low"` ou `"auto"`, reduzida no cliente) + `textHint` opcional do usuário + lista fechada de `STANDARD_CATEGORIES` e `PAYMENT_METHODS` + `today_iso`.
- **Regras de desambiguação no prompt:**
  - Suportar cupom fiscal (NFC-e/SAT), comprovante PIX (identificando se é envio `expense` ou recebimento `income`), boleto bancário, fatura de cartão de crédito, TED/DOC e recibo de maquininha.
  - Priorizar **Valor Pago / Valor Total** sobre subtotal, limite disponível, pagamento mínimo da fatura ou valores de parcelas individuais.
  - Identificar `paymentMethod` (`pix`, `credit`, `debit`, `cash`, `transfer`) conforme o documento (ex.: boleto/TED -> `transfer` ou conforme `PaymentMethod` do sistema; fatura -> `credit`).
- **Saída JSON obrigatória:**
  ```json
  {
    "title": "Supermercado Exemplo",
    "amount": 142.80,
    "occurredOn": "2026-11-12",
    "category": "Alimentação",
    "kind": "variable_expense",
    "paymentMethod": "pix",
    "merchantDoc": "12.345.678/0001-90",
    "confidence": 92
  }
  ```

#### B) Resumo Financeiro & Recomendações (Texto Condensado + Estados Determinísticos)
O backend executa um **motor de regras determinístico** antes de chamar a IA, gerando flags explícitas que guiam o modelo e evitam alucinações numéricas:
- **Estados determinísticos possíveis:**
  - `EXPENSE_RATIO_HIGH` (gastos >= 85% da renda informada no mês)
  - `LIMIT_EXCEEDED` (1 ou mais limites por categoria/diário/cartão ultrapassados)
  - `NEAR_LIMIT` (limites entre 80% e 99%)
  - `POSITIVE_SURPLUS` (saldo mensal positivo e limites sob controle)
  - `NO_LIMITS_SET` (usuário ainda não configurou limites de alerta)
  - `LOW_ACTIVITY` (menos de 3 transações no ciclo atual)
- **Contexto condensado enviado no prompt:**
  - Objetivo financeiro (`GOAL_LABELS`), renda mensal declarada, total gasto no ciclo, saldo restante, top 3 categorias com valores, lista curta dos limites em alerta/excedidos e as flags determinísticas ativas.
  - **Regra de privacidade:** Nunca enviar nome completo, e-mail, CPF do usuário, IDs internos ou descrições brutas de todas as transações.
- **Saída JSON obrigatória:**
  ```json
  {
    "headline": "Seus gastos em Alimentação já passaram do limite este mês.",
    "summary": "Você comprometeu 78% da renda mensal até agora, com destaque para Alimentação e Transporte. Como seu objetivo é montar reserva financeira, reduzir gastos variáveis nos próximos dias ajuda a preservar seu saldo.",
    "recommendations": [
      "Reduza pedidos de delivery nesta semana para conter a categoria Alimentação.",
      "Defina um teto diário para segurar pequenas compras no cartão."
    ],
    "tone": "alert"
  }
  ```

### 3.3 Evaluation Strategy
- **Dataset de Avaliação (Golden Set):** Curar 50 imagens reais/sintéticas cobrindo 5 cenários (10 de cada): (1) Cupom fiscal NFC-e/SAT, (2) Cupom amassado/baixa luz, (3) Print de comprovante PIX (enviado e recebido), (4) Boleto bancário (com juros/desconto ou valor do documento), (5) Fatura de cartão de crédito (com valor total vs. pagamento mínimo) e comprovante de maquininha.
- **Métricas offline:** Script Python de benchmark comparando a saída do `gemini-3.5-flash-lite` contra o gabarito esperado (exact match em `amount`, match de data, acerto de categoria e taxa de JSON válido).
- **Testes automatizados no repositório:** Testes unitários em `server/python/tests/` com *fake* de `AiProvider` validando:
  1. Parsing e sanitização de categorias inválidas retornadas pelo modelo.
  2. Acionamento automático do fallback determinístico em timeout, HTTP `429` ou JSON malformado.
  3. Comportamento de cache hit/invalidação no `DurableKv` para o resumo da Home.

---

## 4. Technical Specifications

### 4.1 Architecture Overview
```text
[Browser / Mobile Low-Cost]
   │ 1. Redimensiona foto (<canvas> <= 1280px, JPEG ~0.75)
   ▼
POST /api/transactions/receipt  (ou GET /dashboard + POST /api/ai/summary)
   │
[Cloudflare Python Worker — http.py / worker.py (Sync WSGI + Durable Object)]
   │
   ├─► [LedgerModule / FinancialAdvisor]
   │      ├─ Calcula estados determinísticos + checa cache (DurableKv / module_kv)
   │      └─ Se miss ou extração de foto: chama AiProvider (OpenAI-Compatible)
   │             ├─ Sucesso -> Valida schema + normaliza categoria -> Retorna para revisão
   │             └─ Erro / 429 / Timeout -> Fallback determinístico (_extract_receipt_metadata / resumo local)
   │
   └─► [Google AI Studio OpenAI-Compatible Endpoint]
          (gemini-3.5-flash-lite)
```

### 4.2 Integration Points no Código Existente
- **Frontend (`src/components/DashboardWorkspace.tsx`):**
  - Adicionar utilitário leve de compressão de imagem no cliente (`resizeImageToDataUrl`) antes do envio para `transactions/receipt`.
  - Exibir indicador `source: "ai" | "fallback"` e banner informativo quando `config.aiTier === "free_prototype"`.
  - Adicionar card de **Resumo Inteligente** na sub-página *Visão Geral*, consumindo `dashboard.aiSummary` (gerado em cache) e botão opcional de atualização manual com debounce/cooldown.
- **HTTP & Worker (`server/python/valorai/http.py`):**
  - `/api/transactions/receipt` já está em `LARGE_BODY_PATHS` (suporta payload maior que 16 KB; confirmar/ajustar teto de bytes adequado para JPEG base64 de até ~500 KB, ex.: `750_000` bytes).
  - Novo endpoint opcional `POST /api/ai/summary` (ou campo assíncrono/sob demanda separado de `GET /api/dashboard` para não travar o carregamento inicial da tela caso a API externa demore). *Recomendação:* manter `GET /api/dashboard` retornando apenas o resumo se já estiver em cache no `DurableKv`, e disparar a geração via `POST /api/ai/summary` pelo cliente quando não houver cache válido.
  - Expor em `GET /api/config` flags públicas: `aiEnabled: bool` e `aiTier: "free_prototype" | "paid"`.
- **Domínio (`server/python/valorai/ledger/module.py`):**
  - Injetar `AiProvider` seguindo o mesmo padrão de `clock`, `hasher`, `kv` e `audit` (sem `await`, compatível com WSGI síncrono no Durable Object).
  - Manter `_validate_transaction_payload` como fonte única de verdade antes de persistir no D1.
- **Configuração (`server/python/wrangler.jsonc`):**
  - Adicionar em `vars` (e replicar em `env.production.vars`):
    - `AI_MODE`: `"openai_compatible"` (ou `"demo"` para testes locais sem chave)
    - `AI_BASE_URL`: `"https://generativelanguage.googleapis.com/v1beta/openai"`
    - `AI_MODEL`: `"gemini-3.5-flash-lite"`
    - `AI_TIER`: `"free_prototype"`
  - Configurar `AI_API_KEY` via `wrangler secret put AI_API_KEY`.

### 4.3 Security & Privacy
- **Segredos:** `AI_API_KEY` nunca deve ser commitada no repositório ou exposta ao frontend.
- **Minimização de dados:** Prompts de resumo enviam apenas agregados numéricos e flags de estado; nunca enviam nome, e-mail, senha ou identificadores de conta.
- **Free Tier vs. Produção:** Documentar e sinalizar na UI que no Free Tier os dados podem ser usados para treinamento pelo provedor; antes da abertura para usuários reais em produção, migrar a chave para *Pay-as-you-go* (`AI_TIER=paid`).
- **Rate Limiting / Circuit Breaker:** Registrar no `DurableKv` um cooldown curto (ex.: 60s) caso o provedor retorne `429`, evitando cascata de chamadas que falhariam em sequência.

---

## 5. Risks & Roadmap

### Phased Rollout
- **Fase 1 — MVP (Atual):**
  - Implementação do `OpenAiCompatibleClient` síncrono no Worker.
  - Extração de recibos via `gemini-3.5-flash-lite` em `/api/transactions/receipt` com compressão no cliente e fallback determinístico.
  - Card de Resumo & Recomendações na Home via `POST /api/ai/summary` com estados determinísticos e cache no `DurableKv`.
- **Fase 2 — v1.1 (Otimização & Escala):**
  - Categorização assistida por IA em lote na importação CSV/OFX (`/api/transactions/import`).
  - Melhorias de prompt e calibração de confiança com base nos erros do Golden Set.
- **Fase 3 — v2.0 (Produção):**
  - Migração para tier *Pay-as-you-go* (`AI_TIER=paid`).
  - Roteamento via **Cloudflare AI Gateway** (observabilidade, cache de borda e fallback automático entre provedores).
  - Armazenamento opcional de comprovantes no **Cloudflare R2**.

### Technical Risks & Mitigations
| Risco | Impacto | Mitigação |
| :--- | :--- | :--- |
| **Estouro de cota Free Tier (HTTP 429)** | Falha temporária na IA | Cache no `DurableKv`, circuit breaker no `429`, geração do resumo fora do `GET /api/dashboard` e fallback determinístico automático. |
| **Latência/Timeout no Worker WSGI** | Erro na requisição do usuário | Compressão de imagem no cliente (`<= 350 KB`), timeout explícito na chamada HTTP (ex.: 8s) e fallback imediato. |
| **Alucinação de categoria ou valor** | Lançamento incorreto no D1 | *Structured Outputs* com enum de `STANDARD_CATEGORIES`, validação via `_validate_transaction_payload` e revisão obrigatória na UI. |
| **Dependência de um único provedor** | Lock-in / mudança de API | Interface `AiProvider` estritamente aderente ao padrão OpenAI-Compatible (`AI_BASE_URL` + `AI_MODEL` configuráveis via env). |
