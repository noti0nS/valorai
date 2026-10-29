# ValorAI

Protótipo de cadastro em **Astro + React**, com a identidade visual do ValorAI e da Nulfinance Inc.

**Acessar:** https://valorai-prototype.joselucas0303.workers.dev

A tela inicial é o **login**. A opção **Criar conta** abre o cadastro abaixo; sessões existentes retomam o painel ou a etapa pendente.

```text
Dados pessoais → Acesso → Confirmação simulada → Perfil financeiro → Painel
                                                                      ↕
                                                       Entrar / sair / ajustar perfil
```

## O que funciona

- Cadastro persistido: nome, CPF, nascimento, celular, CEP, UF, cidade, e-mail e senha. Validação compartilhada entre navegador e servidor, CPF/e-mail únicos e idade mínima de 16 anos.
- Consulta de CEP pelo ViaCEP e sugestões de municípios pelo IBGE; preenchimento manual disponível quando os serviços falham.
- Confirmação por código de uso único em uma **caixa de demonstração**, acessível apenas à sessão da conta pendente.
- Renda, gastos fixos e objetivo financeiro, com edição posterior e painel de estimativas.
- Login por CPF/e-mail, sessão retomada ao recarregar, logout e desativação com revogação das sessões.
- Três guias educativos pré-carregados por migração, sem interface administrativa.
- Layout responsivo, campos rotulados, foco de teclado, diálogos nativos e respeito à preferência por movimento reduzido.

### Limites deste recorte

A referência é a ATA **v1.3** em `docs/Ata_de_Reuniao_ValorAl_v1.3.docx`. Esta implementação de 29/10/2026 não altera a ata nem transforma decisões técnicas em requisitos aprovados.

| Requisito de trabalho | Cobertura no protótipo |
| --- | --- |
| RF001 — Cadastro | Fluxo inicial e persistência |
| RF002 — Confirmação de e-mail | Simulação autorizada; não verifica titularidade |
| RF003 — Manutenção cadastral | Pendente; edição aqui é apenas do perfil financeiro |
| RF004 — Perfil financeiro | Renda, gastos fixos e objetivo |
| RF005 — Desativação | Exclusão lógica; dados preservados e sessões revogadas |
| RF006/RF007 — Login/sessões | Login, timeout, retomada e logout |
| RF008 — Recuperação de senha | Pendente |

Lançamentos, categorias, limites/alertas, importação CSV/Excel/OFX e leitura de recibos por IA pertencem às próximas etapas. A diferença entre renda e gastos fixos não é saldo bancário. A opção “Começar a investir” é apenas um objetivo, sem perfil de investidor ou recomendação financeira.

## Confirmação demonstrativa

Nenhum e-mail é enviado. O hostname gratuito `workers.dev` hospeda o site, mas não fornece um domínio remetente de e-mail. A conta fica com status `demo_confirmed`; a API mantém `emailVerified: false`.

Parâmetros **provisórios**, ainda sujeitos à validação do RF002:

- Código: seis dígitos, validade de 10 minutos, até cinco tentativas.
- Reenvio: intervalo de 60 segundos e até três emissões por hora, incluindo a inicial.

Use dados fictícios e uma senha exclusiva para teste. A desativação preserva dados; reativação, retenção e exclusão definitiva continuam pendentes. Esta demonstração não estabelece conformidade LGPD.

## Executar localmente

Requisitos: **Node 24.22+ na linha 24.x**, npm e navegador moderno. As outras linhas aceitas pelo CLI estão em `engines`. Instale as dependências fixadas nos lockfiles:

```powershell
npm ci
npm --prefix server ci
npm run build
```

Inicialize o D1 **local** a partir da pasta `server`:

```powershell
cd server
npx cf d1 migrations apply 9186a9b0-dce5-442b-96ee-a3e67b4fe2b0 --local --persist-to .cloudflare/state --dir migrations
```

Na raiz, inicie a API e os assets compilados:

```powershell
npm run dev:api
```

Abra **http://127.0.0.1:8787**. O estado local fica em `server/.cloudflare/`, separado do banco remoto. Para editar o frontend com atualização automática, rode também `npm run dev` em outro terminal e abra o endereço exibido pelo Astro; `/api` é encaminhado ao Worker local. O modo de desenvolvimento dispensa Turnstile, sem credenciais de produção.

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
          → /api/*: Worker → AuthCoordinator (Durable Object SQLite)
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

`server/cloudflare.config.ts` identifica a conta, o Worker `valorai-prototype`, o D1 e o widget já provisionados. A credencial secreta do Turnstile reside exclusivamente no Worker como `TURNSTILE_SECRET_KEY`; `bindings.secret()` a referencia sem incorporá-la ao build. A site key é pública. Para outra conta, crie os recursos correspondentes e atualize esses identificadores.

Autentique o CLI com `npx cf auth login` dentro de `server`. Para aplicar novas migrações **remotas**, nessa mesma pasta:

```powershell
npx cf d1 migrations apply 9186a9b0-dce5-442b-96ee-a3e67b4fe2b0 --dir migrations
```

Depois, na raiz:

```powershell
npm run deploy
```

Esse script executa Astro, `cf build` e `cf deploy --prebuilt --mode production`. O backend empacota `dist/` por meio de `server/vite.config.ts`. Para publicar um build já validado: `npm --prefix server run deploy:built`. Não publique com o modo `development`.

Após publicar, confira o site, `/api/config`, a presença do Turnstile e um cadastro sintético no navegador. Um envio sem token válido deve ser rejeitado pela API.

## Estrutura e referência visual

```text
assets/                    Logos originais
src/pages/index.astro      Página, metadados e hidratação
src/components/            Fluxo React e componentes de interface
src/styles/                Identidade visual e responsividade
shared/validation.ts       Validações e objetivos compartilhados
server/src/index.ts        Worker e coordenador de autenticação
server/migrations/         Esquema D1 e conteúdo educativo
tests/                     Validações e integração com navegador/API
docs/                      Atas e documentos históricos
```

Redesign de 29/10/2026: paleta derivada da marca (sálvia `#7E9F8C` e grafite `#242830`), fonte Instrument Sans hospedada junto ao site, textos com tamanho mínimo de 12 px e contraste adequado. O painel lateral do login e do cadastro é uma **ilustração** dos canais previstos (manual, CSV/Excel/OFX e foto de comprovante), das categorias e de um limite atingido que apenas alerta; não representa funcionalidade implementada.

O **FGL MCP** (https://fglibs.com/mcp) indicou a [NumberFlow](https://github.com/barvian/number-flow), usada para animar os valores do perfil financeiro; o valor formatado também é exposto como texto para leitores de tela. A [Arc Library](https://github.com/kuratlielia/arc-library), encontrada pelo mesmo catálogo, serviu de referência inicial para etapas e cartões de seleção. A interface usa implementação própria em React, `motion` e Lucide.
