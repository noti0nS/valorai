-- Add category grouping to lessons and seed 6 additional Markdown guides (15 total across 5 categories).

ALTER TABLE lessons ADD COLUMN category TEXT NOT NULL DEFAULT 'Orçamento & Rotina';

UPDATE lessons SET category = 'Orçamento & Rotina' WHERE id IN ('first-budget', 'due-dates', 'invisible-spending');
UPDATE lessons SET category = 'Dívidas & Crédito' WHERE id IN ('debt-exit', 'credit-card-control');
UPDATE lessons SET category = 'Reserva & Metas' WHERE id IN ('emergency-fund', 'annual-expenses');
UPDATE lessons SET category = 'Renda & Carreira' WHERE id IN ('irregular-income');
UPDATE lessons SET category = 'Primeiros Investimentos' WHERE id IN ('first-investments');

INSERT INTO lessons (id, title, description, body, minutes, category) VALUES
(
  'credit-score-negotiation',
  'Nome limpo, score e renegociação sem cair em armadilhas',
  'Entenda como funciona a negativação, o que realmente influencia seu score e como negociar com segurança.',
  '## O que acontece quando o nome vai para os órgãos de proteção

Ter uma dívida em atraso registrada em cadastros de inadimplência (como Serasa ou SPC) dificulta aprovações de crédito, aluguel e financiamentos. Antes de aceitar qualquer proposta, vale entender seus direitos e prioridades.

### 1. Como funciona a negociação segura

- **Confirme a origem da dívida:** peça o detalhamento do valor original, juros e encargos antes de pagar qualquer boleto.
- **Desconfie de "taxa para limpar o nome":** ninguém pode cobrar taxa adiantada para aumentar score ou apagar apontamentos legítimos.
- **Formalize o acordo por escrito:** guarde o termo com número de parcelas, datas de vencimento e protocolo. Após o pagamento da primeira parcela (ou quitação à vista), o credor tem até **5 dias úteis** para retirar a restrição.

### 2. O que ajuda (e o que não ajuda) o seu score

| Fator | Impacto no score | Como agir na prática |
| --- | --- | --- |
| **Contas pagas em dia** | Muito alto (positivo) | Use lembretes e alinhe vencimentos à data do salário |
| **Uso moderado do cartão** | Alto (positivo) | Evite comprometer todo o limite todo mês |
| **Muitos pedidos de crédito seguidos** | Negativo no curto prazo | Compare condições antes de enviar várias propostas |
| **Quitar dívida antiga com desconto** | Positivo após baixa | Exija o comprovante de quitação e acompanhe a atualização |

> **Atenção ao orçamento:** nunca troque uma dívida negativada antiga por um parcelamento novo que não cabe no seu mês. Negocie apenas o valor que você consegue sustentar até a última parcela.',
  5,
  'Dívidas & Crédito'
),
(
  'smart-goals',
  'Metas financeiras realizáveis: da viagem ao novo equipamento',
  'Transforme desejos vagos em metas com valor, prazo e aporte mensal que cabem no seu orçamento.',
  '## Por que "quero guardar dinheiro" quase nunca funciona

Quando o objetivo não tem **valor definido** nem **prazo**, qualquer gasto imediato parece mais urgente do que poupar. Dar nome e número à meta muda sua decisão no dia a dia.

### A fórmula simples da meta realizável

Toda meta no seu planejamento precisa responder a quatro perguntas:

1. **O quê?** (Ex.: trocar de notebook, fazer um curso, viajar nas férias.)
2. **Quanto custa no total?** (Inclua taxas, frete ou custos extras.)
3. **Quando quero realizar?** (Número de meses até a data.)
4. **Quanto preciso separar por mês?** (`Valor total ÷ Meses`.)

### Exemplo prático no orçamento

| Objetivo | Valor total | Prazo | Aporte mensal necessário |
| --- | --- | --- | --- |
| **Notebook de trabalho** | R$ 3.600 | 12 meses | R$ 300/mês |
| **Curso de especialização** | R$ 1.800 | 6 meses | R$ 300/mês |
| **Viagem de fim de ano** | R$ 2.400 | 10 meses | R$ 240/mês |

### Como manter o ritmo sem desistir

- **Priorize uma ou duas metas por vez:** dividir R$ 300 em seis metas diferentes dá a sensação de que nada sai do lugar.
- **Pague a meta primeiro:** faça o aporte logo que receber a renda, e não apenas com "o que sobrar" no fim do mês.
- **Use a aba Planejamento & Metas do ValorAI:** acompanhe o percentual concluído e registre cada aporte para visualizar seu avanço real.',
  5,
  'Reserva & Metas'
),
(
  'thirteenth-and-extras',
  '13º salário, férias e renda extra: como dividir sem desperdiçar',
  'Um método prático para aproveitar ganhos sazonais no presente sem abrir mão de dívidas e metas.',
  '## O risco de gastar o dinheiro extra antes mesmo de receber

O 13º salário, o terço de férias, bônus ou trabalhos extras são grandes aliados para acelerar planos — desde que não sejam comprometidos inteiro em compras parceladas que continuam pesando nos meses seguintes.

### A regra de divisão 50-30-20 para entradas extras

Quando cair um valor fora do salário comum, experimente fatiar no mesmo dia:

1. **50% para tranquilidade financeira:** quitar dívidas caras (cartão, cheque especial), completar a reserva de emergência ou provisionar IPVA/IPTU de janeiro.
2. **30% para objetivos de médio prazo:** acelerar uma meta prioritária no ValorAI (curso, reforma, viagem, equipamento).
3. **20% para aproveitar agora sem culpa:** lazer, presentes ou uma compra desejada à vista.

> **Dica prática:** se você está com dívidas em atraso com juros altos, inverta a prioridade e direcione **70% a 80%** do valor extra para encerrar ou reduzir a dívida mais cara, reservando uma pequena parcela para não gerar sensação de privação total.

### Cuidado com o "efeito férias"

No mês seguinte às férias, o salário volta ao valor normal — e às vezes vem menor por causa do adiantamento. Antes de viajar ou gastar o adicional, já deixe separado o dinheiro das **contas fixas do mês de retorno**.',
  4,
  'Renda & Carreira'
),
(
  'family-budget',
  'Finanças em família ou casal: combinados que evitam conflitos',
  'Modelos simples de divisão de contas e rotina de alinhamento para manter transparência em casa.',
  '## Dinheiro compartilhado pede regras claras, não adivinhação

Mesmo casais ou famílias com ótima relação enfrentam atritos quando não está claro **quem paga o quê**, qual é o limite para gastos conjuntos e quanto cada pessoa tem de autonomia para despesas individuais.

### 3 modelos comuns de organização em casa

| Modelo | Como funciona | Quando costuma funcionar melhor |
| --- | --- | --- |
| **Rateio proporcional à renda** | Cada pessoa contribui para as contas da casa no mesmo percentual da própria renda | Quando há diferença relevante entre os salários |
| **Divisão 50/50 das despesas fixas** | Contas da casa são somadas e divididas igualmente | Quando as rendas são próximas |
| **Caixa único + mesada individual** | Toda a renda vai para o orçamento familiar e cada um tem um valor livre mensal | Quando ambos preferem gestão totalmente conjunta |

### Acordo mínimo para evitar desgaste

- **Reunião rápida mensal (20 minutos):** revisem juntos vencimentos, metas da casa e compras maiores previstas para o próximo mês.
- **Teto sem consulta:** combinem um valor acima do qual qualquer compra conjunta é conversada antes (ex.: acima de R$ 200).
- **Respeitem o espaço individual:** manter uma parcela pequena do orçamento para escolhas pessoais sem justificativa reduz conflitos no dia a dia.

> **No ValorAI:** categorizar corretamente despesas compartilhadas (*Moradia*, *Alimentação*, *Serviços*) ajuda a enxergar o custo real da casa antes de fechar qualquer divisão.',
  5,
  'Renda & Carreira'
),
(
  'inflation-purchasing-power',
  'Inflação, poder de compra e juros compostos no dia a dia',
  'Entenda por que R$ 100 compram menos com o tempo e como os juros trabalham a favor ou contra você.',
  '## Por que o dinheiro parado perde valor

**Inflação** é o aumento generalizado dos preços ao longo do tempo (medido no Brasil principalmente pelo **IPCA**). Se os preços sobem 5% em um ano e seu dinheiro fica parado sem rendimento, ele passa a comprar menos coisas — você perdeu **poder de compra**, mesmo que o número na conta continue igual.

### O conceito de ganho real

Para saber se uma aplicação realmente aumentou seu patrimônio, olhe além da taxa nominal:

- **Rendimento nominal:** o percentual bruto mostrado antes de descontar impostos e inflação.
- **Rendimento real:** o que sobra **acima da inflação** após impostos. É o ganho real que protege seu padrão de vida no futuro.

### Juros compostos: os dois lados da mesma força

Nos **juros compostos**, os juros de cada período passam a incidir sobre o valor acumulado até ali (juros sobre juros):

- **Contra você (dívidas):** uma fatura no rotativo ou empréstimo caro cresce em ritmo acelerado se você paga só o mínimo.
- **A seu favor (metas e reservas):** aportes mensais consistentes somados ao tempo multiplicam o resultado muito mais do que tentar "acertar a tacada" com um único depósito alto.

> **Regra prática:** no longo prazo, **constância + tempo + proteção contra a inflação** importam mais do que tentar prever movimentos de curto prazo do mercado.',
  5,
  'Primeiros Investimentos'
),
(
  'fixed-vs-variable-concepts',
  'Renda fixa vs. renda variável: conceitos essenciais para iniciantes',
  'Compreenda a diferença entre previsibilidade e oscilação antes de dar os próximos passos.',
  '## Duas famílias diferentes de investimentos

Quando alguém começa a estudar investimentos, encontra dois grandes grupos. Entender a lógica de cada um evita sustos e escolhas incompatíveis com o seu prazo.

### Comparativo conceitual

| Aspecto | Renda Fixa | Renda Variável |
| --- | --- | --- |
| **Como funciona** | Você empresta dinheiro (a um banco, empresa ou governo) sob regras definidas de remuneração | Você compra uma fração de um negócio, imóvel ou ativo cujo preço oscila diariamente |
| **Previsibilidade** | Maior: você conhece antes o critério de rendimento (prefixado, pós-fixado ou atrelado à inflação) | Menor no curto prazo: o valor pode subir ou cair conforme resultados e mercado |
| **Uso mais comum** | Reserva de emergência e objetivos de curto/médio prazo | Objetivos de longo prazo (5+ anos), quando você tolera oscilações temporárias |

### Três termos que você vai ouvir com frequência

- **Pós-fixado:** acompanha um indicador (como a taxa Selic ou o CDI); costuma ter baixa oscilação diária.
- **Prefixado:** define uma taxa fixa no momento da aplicação; o valor de mercado oscila se você resgatar antes do vencimento.
- **Atrelado à inflação (IPCA+):** combina a variação da inflação com uma taxa fixa adicional, ajudando a preservar poder de compra no médio e longo prazo.

> **Aviso educativo:** este guia apresenta conceitos gerais para educação financeira e **não recomenda** títulos, ações, fundos, corretoras ou produtos específicos.',
  6,
  'Primeiros Investimentos'
)
ON CONFLICT(id) DO UPDATE SET
  title = excluded.title,
  description = excluded.description,
  body = excluded.body,
  minutes = excluded.minutes,
  category = excluded.category;
