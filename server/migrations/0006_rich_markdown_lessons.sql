-- Seed rich Markdown financial guides tailored to ValorAI's target audience
-- (Brazilian individuals organizing personal budgets, debts, emergency funds, and first investments).

INSERT INTO lessons (id, title, description, body, minutes) VALUES
(
  'first-budget',
  'Seu primeiro orçamento na prática (regra 50-30-20)',
  'Monte um plano mensal realista a partir da sua renda líquida e ajuste os limites sem culpa.',
  '## Por onde começar sem complicar

Um orçamento útil não serve para engessar sua vida, e sim para mostrar **para onde o dinheiro está indo** antes que o mês acabe. O ponto de partida é sempre a sua **renda líquida** (o valor que realmente cai na conta após descontos), e não o salário bruto.

### 1. Separe o que é fixo do que é variável

- **Gastos fixos essenciais:** aluguel ou prestação, condomínio, energia, água, internet, plano de saúde, mensalidade escolar e transporte recorrente.
- **Gastos variáveis essenciais:** supermercado, farmácia e manutenção básica.
- **Estilo de vida (desejos):** delivery, lazer, assinaturas, viagens e compras não urgentes.

### 2. A regra 50-30-20 adaptada à realidade brasileira

Use essa divisão como **referência inicial**, ajustando conforme sua fase atual:

| Bloco | Meta sugerida | O que entra aqui |
| --- | --- | --- |
| **Necessidades (50%)** | Até 50% da renda | Moradia, alimentação básica, saúde, transporte e contas da casa |
| **Desejos (30%)** | Até 30% da renda | Lazer, restaurantes, streaming, hobbies e compras pessoais |
| **Metas e dívidas (20%)** | Pelo menos 20% | Reserva de emergência, quitação de dívidas e objetivos futuros |

> **Dica prática:** se suas necessidades hoje consomem 65% ou 70% da renda, não abandone o plano. Reduza temporariamente o bloco de desejos para 15% e proteja os 10%–15% de metas até renegociar contratos ou aumentar a renda.

### 3. Como aplicar no ValorAI hoje

1. Informe sua renda e gastos fixos no **Perfil Financeiro**.
2. Registre lançamentos pelo canal mais rápido (manual, importação `CSV`/`OFX` ou foto de comprovante).
3. Crie **tetos mensais** nas categorias em que você mais costuma escorregar (como *Alimentação* e *Lazer*). Os alertas avisam quando você chega a **80%** do limite, sem bloquear seus lançamentos.',
  5
),
(
  'emergency-fund',
  'Reserva de emergência: quanto juntar e como começar',
  'Calcule o tamanho ideal da sua reserva e construa tranquilidade financeira um passo por vez.',
  '## O que é (e o que não é) uma emergência

A reserva de emergência é o colchão financeiro que impede você de recorrer ao **rotativo do cartão** ou a empréstimos caros quando algo inesperado acontece — como perda de renda, problema de saúde ou reparo urgente em casa.

- **É emergência:** desemprego, despesa médica imprevista, conserto urgente do carro ou vazamento em casa.
- **Não é emergência:** IPVA, IPTU, matrícula escolar, troca planejada de celular ou presentes de fim de ano. Esses gastos são **previsíveis** e devem ter provisão própria.

### Quanto juntar de acordo com sua estabilidade

Multiplique seus **gastos essenciais mensais** (não a renda total, apenas o necessário para viver bem) pelo número de meses do seu perfil:

| Perfil profissional | Meses recomendados | Exemplo (custo essencial de R$ 2.500) |
| --- | --- | --- |
| **CLT ou servidor estável** | 3 a 6 meses | R$ 7.500 a R$ 15.000 |
| **Autônomo, MEI ou comissionado** | 6 a 12 meses | R$ 15.000 a R$ 30.000 |

### Plano em 3 degraus para não desistir

1. **Degrau 1 — Micro-reserva (R$ 500 a R$ 1.000):** cobre pequenos imprevistos imediatos e quebra o ciclo de endividamento.
2. **Degrau 2 — 1 mês de tranquilidade:** protege você contra atrasos de pagamento ou oscilações de renda.
3. **Degrau 3 — Reserva completa:** avance com aportes automáticos logo no dia em que o salário cair, antes de gastar.

### Onde manter a reserva (critérios, sem indicação de produto)

Ao avaliar opções no mercado, priorize três características:
- **Liquidez diária:** poder resgatar no mesmo dia ou no próximo dia útil sem perder valor.
- **Baixo risco:** evitar ativos que oscilam muito na bolsa ou em moedas voláteis.
- **Proteção contra a inflação:** buscar opções que acompanhem a taxa básica de juros ao longo do tempo.

> **Aviso educativo:** este conteúdo tem finalidade exclusivamente educacional e não recomenda instituições financeiras ou produtos específicos.',
  6
),
(
  'due-dates',
  'Fluxo de caixa pessoal e vencimentos sem atraso',
  'Organize datas de entrada e saída para evitar multas, juros por esquecimento e sustos no fim do mês.',
  '## Previsão, vencimento e pagamento não são a mesma coisa

Muitas pessoas têm renda suficiente para pagar todas as contas do mês, mas mesmo assim pagam multa ou entram no cheque especial por um problema de **descasamento de datas**: as contas vencem no dia 5, mas o dinheiro só entra no dia 10.

### O método dos 2 blocos no mês

Se você recebe uma vez por mês (ou em duas parcelas, como adiantamento + salário), divida suas contas em dois blocos:

- **Bloco A (dias 1 a 15):** pague com o saldo do início do mês ou do adiantamento.
- **Bloco B (dias 16 a 31):** pague com a segunda parcela da renda.

Se quase todas as contas vencem antes do seu pagamento cair, peça a **alteração da data de vencimento** de energia, internet, telefone e cartão de crédito para 3 a 5 dias após o recebimento principal.

### Rotina semanal de 10 minutos

1. **Toda segunda ou sexta-feira**, abra seu extrato no ValorAI.
2. **Confira o que venceu e o que vence nos próximos 7 dias**, diferenciando o que é *previsão* do que já foi *pago*.
3. **Concilie lançamentos** importando o arquivo `OFX` ou `CSV` do banco para não esquecer débitos automáticos nem assinaturas.

> **Regra de ouro:** uma conta paga com atraso de 3 dias pode gerar multa de 2% + juros proporcionais. Em um ano, pequenos esquecimentos custam o equivalente a uma conta inteira a mais.',
  4
),
(
  'debt-exit',
  'Saindo das dívidas: Bola de Neve vs. Avalanche',
  'Compare estratégias comprovadas para quitar pendências mais rápido e negociar com segurança.',
  '## Passo 1: tire a dívida do escuro

Antes de escolher um método, liste **todas** as pendências em um único lugar com quatro informações:
1. Credor (banco, loja, cartão, familiar).
2. Saldo total para quitação hoje.
3. Valor da parcela mínima mensal.
4. **CET (Custo Efetivo Total)** — a taxa real que inclui juros, seguros e tarifas.

### Passo 2: escolha sua estratégia de ataque

Enquanto paga o mínimo de todas as contas para não aumentar a inadimplência, direcione **todo dinheiro extra** para uma única dívida por vez:

| Critério | Método Avalanche | Método Bola de Neve |
| --- | --- | --- |
| **Qual quitar primeiro?** | A dívida com **maior taxa de juros (CET)** | A dívida com **menor saldo devedor** |
| **Principal vantagem** | Economiza mais dinheiro em juros no total | Gera vitórias rápidas e mantém a motivação alta |
| **Melhor para quem…** | Tem dívidas no rotativo do cartão ou cheque especial | Tem várias dívidas pequenas e se sente sobrecarregado |

### Passo 3: regras de negociação no Brasil

- **Troque dívida cara por mais barata:** se os juros do cartão passam de 10% ao mês, avalie quitar com uma linha de crédito mais barata apenas se você **cancelar ou travar o limite** para não dobrar a dívida.
- **Respeite o limite de 30%:** nunca feche um acordo cuja parcela comprometa mais do que 30% da sua renda líquida; acordo impagável vira uma segunda dívida.
- **Desconto à vista:** sempre pergunte qual é o valor para quitação imediata antes de aceitar um parcelamento longo.

> **Checklist imediato:** pause compras parceladas no cartão, remova cartões salvos em aplicativos de compra e direcione qualquer renda extra (13º, férias, bônus ou venda de itens parados) para a dívida-alvo.',
  6
),
(
  'invisible-spending',
  'Gastos invisíveis: assinaturas, delivery e compras por impulso',
  'Identifique o "efeito goteira" que consome seu saldo em pequenas cobranças recorrentes.',
  '## O perigo dos valores que parecem inofensivos

R$ 29,90 de um streaming, R$ 19,90 de clube de vantagens, R$ 45 de taxa de entrega no fim de semana, R$ 18 de café na rua. Isolados, parecem irrelevantes. Juntos, podem somar **R$ 400 a R$ 800 por mês** — o suficiente para atrasar uma meta importante o ano inteiro.

### Auditoria de 15 minutos no extrato

Pegue seus últimos 30 dias de movimentações (use a importação `CSV` ou `OFX` no ValorAI) e faça três perguntas para cada gasto recorrente:

1. **Eu usei isso nos últimos 14 dias?** Se a resposta for não, pause ou cancele hoje mesmo.
2. **Estou pagando por dois serviços parecidos?** (Ex.: dois apps de música ou três streamings ao mesmo tempo.)
3. **Qual é o custo anual disso?** Multiplique o valor mensal por `12` — R$ 49,90/mês vira **R$ 598,80/ano**.

### Como frear compras por impulso sem radicalismo

- **Regra das 48 horas:** para qualquer compra não essencial acima de R$ 100, espere dois dias antes de fechar o pedido. Na maioria das vezes, a urgência desaparece.
- **Teto por categoria:** defina no ValorAI um limite semanal ou mensal para *Alimentação* (delivery) e *Lazer*. Receber o alerta ao atingir 80% ajuda a recalibrar a última semana do mês.
- **Orçamento para o prazer:** cortar 100% do lazer gera efeito sanfona. Reserve um valor fixo e consciente para gastar sem culpa — dentro do limite.',
  5
),
(
  'credit-card-control',
  'Cartão de crédito: aliado do orçamento ou armadilha da fatura?',
  'Domine o parcelamento, o fechamento da fatura e evite cair no crédito rotativo.',
  '## O cartão não é extensão da sua renda

O erro mais comum no uso do cartão de crédito é olhar apenas para o **limite disponível** em vez de olhar para a sua **capacidade de pagamento mensal**. Parcelar compras pequenas cria uma ilusão perigosa: dez parcelas "baratas" de R$ 80 já comprometem **R$ 800 fixos** do seu próximo mês.

### 4 regras de ouro para usar o cartão a seu favor

1. **Pague sempre a fatura integral:** nunca pague apenas o mínimo nem entre no rotativo. Os juros do rotativo estão entre os mais altos do país.
2. **Trave um teto para a fatura:** defina um valor máximo mensal para a soma de tudo que vai no cartão, compatível com seu orçamento no ValorAI.
3. **Cuidado com o parcelamento longo:** evite parcelar gastos de consumo imediato (supermercado, combustível, restaurantes). Se o item acaba antes da última parcela, você está pagando o passado.
4. **Conheça o melhor dia de compra:** compras feitas logo após a data de **fechamento** da fatura só vencem no mês seguinte, dando mais fôlego ao fluxo de caixa.

### Como registrar no ValorAI sem duplicidade

- **Preferência por competência:** lance a compra na categoria real (*Alimentação*, *Transporte*, *Saúde*) para saber exatamente onde você gasta.
- **Na virada do mês:** se preferir importar a fatura, revise as categorias sugeridas antes de confirmar para que seus limites por categoria reflitam a realidade.',
  5
),
(
  'irregular-income',
  'Renda variável e autônomos: como ter previsibilidade financeira',
  'Estratégias práticas para quem é MEI, freelancer ou comissionado estabilizar o orçamento mensal.',
  '## O erro de planejar pelo melhor mês

Quem trabalha por conta própria, recebe comissões ou atua como MEI enfrenta um desafio clássico: em um mês entra R$ 6.000; no seguinte, R$ 2.400. Quando você ajusta seu padrão de vida pelo **melhor mês**, qualquer baixa sazonal vira aperto.

### Passo 1: descubra o seu "salário-base"

Some sua renda líquida dos últimos **6 a 12 meses** e divida pelo número de meses (ou use a média dos 3 meses mais fracos como piso de segurança). Esse número é o seu **orçamento mensal real**.

- **Nos meses acima da média:** não aumente os gastos fixos. Guarde a diferença em um **pulmão de caixa**.
- **Nos meses abaixo da média:** complete seu salário-base usando o pulmão de caixa acumulado, sem precisar cortar contas essenciais nem pegar empréstimo.

### Passo 2: separe pessoa física de trabalho

1. **Conta separada:** receba pagamentos de clientes em uma conta dedicada e transfira um **pró-labore fixo** para sua conta pessoal em data combinada (ex.: todo dia 5).
2. **Reserve para impostos e manutenção:** antes de gastar, separe o valor mensal do DAS/impostos e de reposição de equipamentos (notebook, veículo, ferramentas).
3. **Reserva de emergência reforçada:** para renda variável, mire de **6 a 12 meses** de despesas essenciais.

> **Dica no ValorAI:** mantenha no Perfil Financeiro a sua renda média conservadora, e não o pico do mês anterior. Assim os cálculos de margem mensal ficam sempre seguros.',
  6
),
(
  'annual-expenses',
  'Despesas anuais e sazonais: IPVA, IPTU e volta às aulas',
  'Transforme contas pesadas de início e fim de ano em pequenas provisões mensais previsíveis.',
  '## Por que janeiro sempre parece mais caro?

IPVA, IPTU, seguro do carro, matrícula escolar, renovação de conselhos profissionais, presentes de fim de ano e viagens de férias não são imprevistos — eles acontecem **todos os anos na mesma época**. O problema é tentar pagá-los apenas com a renda de janeiro ou dezembro.

### A solução: fundo de provisão anual

Some quanto você gasta por ano com essas despesas sazonais e **divida por 12**. Esse é o valor mensal que deve ser separado todo mês para não sufocar o orçamento quando a conta chegar.

| Despesa anual estimada | Valor anual | Provisão mensal (÷ 12) |
| --- | --- | --- |
| **IPVA + Licenciamento** | R$ 1.800 | R$ 150/mês |
| **IPTU** | R$ 960 | R$ 80/mês |
| **Material escolar / cursos** | R$ 1.200 | R$ 100/mês |
| **Presentes e festas** | R$ 840 | R$ 70/mês |
| **Total provisionado** | **R$ 4.800** | **R$ 400/mês** |

### Benefício extra: desconto à vista

Quem junta os R$ 400/mês ao longo do ano chega em janeiro com o dinheiro na mão e consegue aproveitar **descontos à vista** (comuns em IPTU, IPVA e matrículas), que muitas vezes superam o rendimento de aplicações conservadoras no mesmo período.

> **Como acompanhar:** crie uma meta específica no ValorAI ou reserve essa parcela no seu planejamento mensal de **Metas & Limites**.',
  4
),
(
  'first-investments',
  'Primeiros passos para investir sem complicação',
  'Entenda os pré-requisitos, o tripé dos investimentos e como alinhar cada objetivo ao seu prazo.',
  '## Antes do primeiro real investido

Investir não substitui organização financeira — ele **potencializa** o que você já economiza. Antes de buscar qualquer aplicação, confira três pré-requisitos:

1. **Orçamento positivo:** suas receitas superam seus gastos com regularidade.
2. **Sem dívidas caras:** quitar dívidas com juros altos (como cartão ou empréstimo pessoal) quase sempre gera um "ganho" garantido maior do que qualquer aplicação segura.
3. **Reserva de emergência iniciada:** evita que você precise resgatar investimentos de médio ou longo prazo no pior momento.

### O tripé dos investimentos

Todo investimento equilibra três características, e **nenhum entrega o máximo das três ao mesmo tempo**:

- **Liquidez:** velocidade com que você transforma o investimento em dinheiro na conta.
- **Segurança:** estabilidade e previsibilidade do valor aplicado.
- **Rentabilidade:** potencial de retorno acima da inflação (IPCA) ou de referenciais como Selic e CDI.

### Alinhe o objetivo ao prazo

| Prazo do objetivo | Exemplo prático | Prioridade no tripé |
| --- | --- | --- |
| **Curto prazo (até 1–2 anos)** | Reserva de emergência, IPVA, viagem próxima | **Liquidez e segurança** acima de retorno |
| **Médio prazo (2–5 anos)** | Troca de carro, curso, entrada de imóvel | Equilíbrio entre **segurança e rentabilidade** |
| **Longo prazo (5+ anos)** | Aposentadoria, independência financeira | **Rentabilidade real** acima da inflação |

> **Aviso educativo:** o ValorAI é uma ferramenta de organização e educação financeira. Este guia explica conceitos gerais e **não recomenda** ativos, corretoras ou produtos específicos de investimento.',
  6
)
ON CONFLICT(id) DO UPDATE SET
  title = excluded.title,
  description = excluded.description,
  body = excluded.body,
  minutes = excluded.minutes;
