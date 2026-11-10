# ValorAI

Protótipo funcional de cadastro e gestão financeira em **Astro + React** e **Django no Cloudflare Python Worker**, com a identidade visual do ValorAI e da Nulfinance Inc. (sistema de design Stitch).

- **Acessar:** https://valorai-prototype.joselucas0303.workers.dev
- **Arquitetura e Decisões Técnicas:** Veja [**ARCHITECTURE.md**](ARCHITECTURE.md) e os registros de arquitetura em [`docs/adr/0001-django-workers-architecture.md`](docs/adr/0001-django-workers-architecture.md) e [`docs/adr/0002-dashboard-ledger-and-stitch-workspace.md`](docs/adr/0002-dashboard-ledger-and-stitch-workspace.md).

A tela inicial é o **login**. A opção **Criar conta** abre o cadastro abaixo; sessões existentes retomam o painel financeiro operacional ou a etapa pendente.

```text
Dados pessoais → Acesso → Confirmação simulada → Perfil financeiro → Painel Stitch (Visão Geral, Extratos, Metas e Guias)
                                                                       ↕
                                                       Entrar / sair / manter perfil (RF003) / lançamentos
```

## O que funciona

- Cadastro persistido: nome, CPF, nascimento, celular, CEP, UF, cidade, e-mail, senha e foto de perfil opcional (PNG/JPEG até 2 MB). Validação compartilhada entre navegador e servidor, CPF/e-mail únicos e idade mínima de 16 anos.
- Consulta de CEP pelo ViaCEP e sugestões de municípios pelo IBGE; preenchimento manual disponível quando os serviços falham.
- Confirmação por código de uso único em uma **caixa de demonstração**, acessível apenas à sessão da conta pendente.
- Manutenção do perfil cadastral (**RF003**): edição de dados pessoais, endereço e avatar mantendo CPF e e-mail imutáveis.
- Renda, gastos fixos, objetivo financeiro e metas com registro de aportes e acompanhamento de progresso.
- **Três canais de entrada de transações**: digitação manual, importação de extratos **OFX e CSV**, e leitura de comprovantes por **OCR/IA** com revisão antes de salvar.
- Categorização obrigatória em todos os lançamentos com sugestão automática por palavras-chave e distribuição visual por categoria.
- Limites de gastos configuráveis por categoria e período (`diário`, `semanal`, `mensal`) com **alertas visuais não bloqueantes** ao atingir 80%, 100% ou exceder o teto.
- Login por CPF/e-mail, sessão retomada ao recarregar, logout e desativação com revogação das sessões e preservação do histórico financeiro.
- Três guias educativos pré-carregados por migração com leitura interativa e marcação de conclusão, sem interface administrativa.
- Layout responsivo seguindo o design Stitch (`Visão Geral`, `Transações & Extratos`, `Planejamento & Metas`, `Guias Práticos`), campos rotulados, foco de teclado, diálogos nativos (`<dialog closedby="any">`) e respeito à preferência por movimento reduzido.

### Limites deste recorte

As referências de requisitos são a ATA **v1.3** em `docs/Ata_de_Reuniao_ValorAl_v1.3.docx` e `docs/valorai_requisitos.docx`. As implementações do protótipo não alteram a ata original de 22/10/2026 nem transformam decisões técnicas provisórias em requisitos aprovados.

| Requisito de trabalho | Cobertura no protótipo |
| --- | --- |
| RF001 — Cadastro | Fluxo inicial e persistência |
| RF002 — Confirmação de e-mail | Simulação autorizada; não verifica titularidade |
| RF003 — Manutenção cadastral | Edição de dados pessoais, endereço e avatar (CPF e e-mail imutáveis) |
| RF004 — Perfil financeiro | Renda, gastos fixos, objetivo e metas |
| RF005 — Desativação | Exclusão lógica; dados financeiros preservados e sessões revogadas |
| RF006/RF007 — Login/sessões | Login, timeout, retomada e logout |
| RF008 — Recuperação de senha | Pendente |
| Gestão Financeira (Dashboard) | Lançamentos (manual, OFX/CSV, recibo OCR), categorias, limites com alertas não bloqueantes, aportes em metas e progresso nos guias |

A diferença entre renda e gastos fixos e o saldo projetado no painel são instrumentos de planejamento, não saldo bancário sincronizado via Open Finance. A opção “Começar a investir” é apenas um objetivo, sem perfil de investidor ou recomendação financeira.

## Confirmação demonstrativa

Nenhum e-mail é enviado. O hostname gratuito `workers.dev` hospeda o site, mas não fornece um domínio remetente de e-mail. A conta fica com status `demo_confirmed`; a API mantém `emailVerified: false`.

Parâmetros **provisórios**, ainda sujeitos à validação do RF002:

- Código: seis dígitos, validade de 10 minutos, até cinco tentativas.
- Reenvio: intervalo de 60 segundos e até três emissões por hora, incluindo a inicial.

Use dados fictícios e uma senha exclusiva para teste. A desativação preserva dados; reativação, retenção e exclusão definitiva continuam pendentes. Esta demonstração não estabelece conformidade LGPD.

## Executar localmente

### Com Docker Compose (Recomendado)

Suba todos os recursos do ecossistema local (API Django no Python Worker, banco D1 local, Durable Object coordenador e Frontend Astro) prontos para teste com um comando:

```powershell
docker compose up --build
```

- **Aplicação Completa (Worker + Assets + D1):** [http://localhost:8787](http://localhost:8787)
- **Frontend com Hot-Reload (Astro Dev Server):** [http://localhost:4321](http://localhost:4321) (encaminha `/api` para o Worker)
- **Bateria de testes automatizados no Docker:**
  ```powershell
  docker compose run --rm test
  ```
- **Encerrar containers:**
  ```powershell
  docker compose down
  # ou limpe os volumes persistidos do D1:
  docker compose down -v
  ```

### Sem Docker (Manual)

Requisitos: **Node 24.22+ na linha 24.x**, npm e navegador moderno. As outras linhas aceitas pelo CLI estão em `engines`. Instale as dependências fixadas nos lockfiles:

```powershell
npm ci
npm run build
```

Inicialize o D1 **local** a partir de `server/python`:

```powershell
cd server/python
uv run pywrangler d1 migrations apply valorai-prototype --local
```

Na raiz, inicie a API e os assets compilados:

```powershell
npm run dev:api
```

Abra **http://127.0.0.1:8787**. O estado local fica em `server/python/.wrangler/`, separado do banco remoto. Para editar o frontend com atualização automática, rode também `npm run dev` em outro terminal e abra o endereço exibido pelo Astro; `/api` é encaminhado ao Worker local. O modo de desenvolvimento dispensa Turnstile, sem credenciais de produção.

### Verificações

```powershell
npm run check
npm test
npx playwright install chromium
npm run test:e2e
```

Os testes de navegador usam a API local em `127.0.0.1:8787`, que precisa estar iniciada e com as migrações aplicadas. **Execute `npm run build` após alterar o frontend**, pois os testes acessam `dist/`, não o servidor Astro. Os testes criam dados sintéticos no banco local; não apontam para produção. Capturas são gravadas em `test-results/`, ignorado pelo Git. ViaCEP e IBGE são substituídos por respostas determinísticas somente nos testes.

Os testes cobrem validação, cadastro, confirmação, persistência, edição financeira, login/desativação, isolamento de sessão, origem das requisições e códigos de uso único. A suíte local não valida desafios reais do Turnstile.

Verificação em 29/10/2026, após o redesign: cinco testes de validação e dois de integração passaram; build e checagem de tipos passaram. Na publicação, o HTML correspondeu ao build local, os assets referenciados pela página retornaram HTTP 200 e a caixa demo rejeitou acesso anônimo. O desafio real do Turnstile não foi concluído pelos navegadores automatizados; o cadastro completo em produção ainda precisa de conferência manual.

## Cloudflare

```text
Navegador → Static Assets: HTML Astro, React, fontes e logos
          → /api/*: Python Worker → AuthCoordinator (Durable Object)
                                ├── D1: contas, sessões, perfis e guias
                                ├── Estado temporário: códigos e limites
                                └── Turnstile: validação de cadastro/login
```

O coordenador único serializa as operações de autenticação e executa bcrypt com custo 10. É uma escolha para o volume do protótipo; não é uma arquitetura de autenticação dimensionada para tráfego elevado. Os cookies são `HttpOnly`, `SameSite=Strict` e `Secure` em HTTPS; D1 guarda apenas hashes dos tokens de sessão. Expiração: 30 minutos de inatividade e teto de 12 horas. Dados autenticados usam `Cache-Control: no-store`.

### Recursos com faixa gratuita usados

Limites de referência consultados em **29/10/2026**, compartilhados com os demais projetos da conta:

| Recurso | Uso | Faixa gratuita de referência |
| --- | --- | --- |
| Workers Static Assets | Site, fontes e logos na CDN | Requisições estáticas gratuitas e ilimitadas |
| Workers | API e hostname HTTPS `workers.dev` | 100 mil requisições/dia; 10 ms de CPU por invocação do Worker |
| D1 | Contas, perfis, sessões, auditoria e guias | 5 milhões de linhas lidas/dia; 100 mil escritas/dia; 5 GB totais |
| Durable Objects SQLite | Coordenação, bcrypt, códigos, limitação de tentativas e limpeza por alarme | 100 mil requisições/dia; 13 mil GB-s/dia; armazenamento com cotas próprias |
| Turnstile | Proteção de cadastro e login | Desafios ilimitados no plano gratuito |
| Workers Logs | Observabilidade amostrada em 10% | 200 mil eventos/dia; retenção de três dias |

Nenhum plano pago foi ativado por este projeto. O uso gratuito depende das cotas e do plano efetivo da conta. No Workers Free, exceder os limites pode interromper operações. R2, Workers AI, Queues e KV não têm integração neste fluxo de cadastro; a extração de recibos e o processamento de importações exigirão uma etapa própria.

Fontes: [Workers e logs](https://developers.cloudflare.com/workers/platform/pricing/), [D1](https://developers.cloudflare.com/d1/platform/pricing/), [Durable Objects](https://developers.cloudflare.com/durable-objects/platform/pricing/), [Turnstile](https://developers.cloudflare.com/turnstile/plans/).

### Publicar

`server/python/wrangler.jsonc` identifica o Worker `valorai-prototype`, o D1 e o ambiente de produção. A credencial secreta do Turnstile fica no Worker como `TURNSTILE_SECRET_KEY` e não entra no repositório. A site key pública está no ambiente `production`. Para outra conta, crie os recursos correspondentes e atualize esses identificadores.

Autentique o CLI usado pelo `pywrangler`. Para aplicar novas migrações **remotas**, em `server/python`:

```powershell
uv run pywrangler d1 migrations apply valorai-prototype --remote
```

Depois, na raiz:

```powershell
npm run deploy
```

Esse script executa o build do Astro e `pywrangler deploy --env production`. Não publique com `ENVIRONMENT=development`.

Após publicar, confira o site, `/api/config`, a presença do Turnstile e um cadastro sintético no navegador. Um envio sem token válido deve ser rejeitado pela API.

## Estrutura e referência visual

```text
ARCHITECTURE.md            Visão geral da arquitetura, módulos, banco D1 e rotas da API
assets/                    Logos originais
.stitch/                   Sistema de design Stitch (DESIGN.md) e telas de referência
src/pages/index.astro      Página, metadados e hidratação
src/components/            Fluxo React de cadastro (RegistrationApp) e painel Stitch (DashboardWorkspace)
src/styles/                Identidade visual, Bento grid e responsividade
shared/validation.ts       Validações, categorias e objetivos compartilhados
server/python/             API Django no Python Worker (Account, Session, Confirmation, Finance, Ledger)
server/migrations/         Esquema D1 (0001_initial.sql e 0002_dashboard_ledger.sql) e conteúdo educativo
tests/                     Validações e suíte E2E de navegador/API (Playwright)
docs/                      Atas, requisitos e ADRs (docs/adr/)
```

Para detalhes completos da topologia de execução no Cloudflare, módulos de domínio, esquema de dados e histórico de decisões arquiteturais, consulte [**ARCHITECTURE.md**](ARCHITECTURE.md), [**ADR 0001**](docs/adr/0001-django-workers-architecture.md) e [**ADR 0002**](docs/adr/0002-dashboard-ledger-and-stitch-workspace.md).

Redesign de 29/10/2026 e Painel Stitch de 10/11/2026: paleta derivada da marca (sálvia `#7E9F8C`, esmeralda `#14281D` e grafite `#242830`), fonte Instrument Sans hospedada junto ao site, textos com tamanho mínimo de 12 px e contraste adequado. Após o login e confirmação, o usuário acessa o painel operacional em Bento Grid (`DashboardWorkspace.tsx`) com suporte aos três canais de lançamento, limites e alertas não bloqueantes, metas e guias educativos.

O **FGL MCP** (https://fglibs.com/mcp) indicou a [NumberFlow](https://github.com/barvian/number-flow), usada para animar os valores do perfil financeiro; o valor formatado também é exposto como texto para leitores de tela. A [Arc Library](https://github.com/kuratlielia/arc-library), encontrada pelo mesmo catálogo, serviu de referência inicial para etapas e cartões de seleção. A interface usa implementação própria em React, `motion` e Lucide.
