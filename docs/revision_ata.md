# ValorAI — Ressalvas para avaliação da ata

Data da revisão: 29/10/2026.

Fonte: `Ata_de_Reuniao_ValorAl.pdf`, reunião de 22/10/2026, especialmente a página 2.

## Escopo e conclusão

Esta revisão avalia a especificação de autenticação e sessão (RF002) resumida na ata, suas relações com RF001, RNF04 e RS001. Não houve análise do documento completo de requisitos, código ou ambiente em execução. As observações são lacunas e recomendações para avaliação da equipe, não vulnerabilidades comprovadas nem requisitos já aprovados.

O RF002 apresenta uma boa base: login por CPF ou e-mail, erro genérico, bloqueio após tentativas inválidas, expiração por inatividade, recuperação de senha, segregação inicial de perfis e registro de acessos. Entretanto, ainda não constitui uma especificação suficientemente fechada para implementação e testes.

## Ressalvas

### 1. Armazenamento de senhas

- **Na ata:** RF001 e requisitos não funcionais mencionam criptografia de senhas.
- **Ressalva:** a expressão pode ser interpretada como armazenamento reversível.
- **Para avaliação:** exigir hash não reversível específico para senhas, com salt individual e parâmetros de custo definidos; Argon2id é uma opção. Não armazenar senhas em texto puro nem registrá-las em logs. Manter a regra consistente entre cadastro e autenticação.

### 2. Recuperação de senha

- **Na ata:** código de seis dígitos com validade de 15 minutos.
- **Ressalva:** não estão definidos canal de entrega, verificação do contato, quantidade de tentativas e reenvios ou tratamento de códigos anteriores.
- **Para avaliação:** vincular o código à conta e à finalidade de recuperação, enviá-lo por canal previamente verificado, limitar tentativas e solicitações, garantir uso único e invalidar códigos anteriores ao emitir um novo. A resposta à solicitação não deve revelar se a conta existe.
- **Decisão pendente:** estabelecer limites concretos e o comportamento após atingir cada limite.

### 3. Bloqueio e limitação de tentativas

- **Na ata:** bloqueio de cinco minutos após cinco tentativas inválidas.
- **Ressalva:** não está claro como as tentativas são contabilizadas, quando o contador é reiniciado e se CPF e e-mail permitem contadores separados para a mesma conta.
- **Para avaliação:** contabilizar tentativas por conta de forma consistente entre os identificadores e complementar com limitação de requisições por origem e controles contra ataques distribuídos. Avaliar o risco de um terceiro provocar bloqueios sucessivos de uma conta legítima.
- **Decisão pendente:** definir janela de contagem, reinício do contador e tratamento de tentativas durante o bloqueio.

### 4. Ciclo de vida da sessão

- **Na ata:** expiração após 30 minutos de inatividade.
- **Ressalva:** faltam regras de logout, duração máxima absoluta, sessões simultâneas e revogação.
- **Para avaliação:** definir o que conta como atividade e exigir encerramento efetivo da sessão no logout. Definir revogação após recuperação/troca de senha, desativação da conta e mudanças relevantes de permissão. Estabelecer política para sessões simultâneas e duração máxima absoluta, com validação no servidor.
- **Decisão pendente:** escolher os prazos e determinar se a troca de senha encerra todas as sessões ou permite preservar a sessão atual após confirmação segura.

### 5. Autorização e isolamento dos dados

- **Na ata:** cliente visualiza apenas seus dados; servidor acessa suporte/conteúdos sem administração geral.
- **Ressalva:** faltam permissões explícitas por operação e recurso. Restringir telas não garante a proteção das APIs.
- **Para avaliação:** validar no servidor a autorização em toda operação de leitura ou alteração, usando a identidade autenticada e a titularidade do recurso. Documentar uma matriz de permissões para cliente, suporte e eventual administrador, com negação por padrão.

### 6. CPF como filtro no RS001

- **Na ata:** CPF definido como chave obrigatória de filtragem para mitigar colisão de dados.
- **Ressalva:** CPF é um identificador, não uma credencial nem garantia de autorização. Confiar no CPF enviado pelo cliente não assegura isolamento.
- **Para avaliação:** obter a identidade da sessão autenticada e verificar a titularidade do recurso no servidor. Não permitir que a simples alteração de um CPF na requisição dê acesso a outra conta. Separar a discussão de unicidade de cadastro da discussão de controle de acesso.
- **Ajuste textual já pendente na ata:** substituir a referência a “paciente” por “cliente/usuário”.

### 7. Contas de suporte e senha temporária

- **Na ata:** senha temporária de servidor com dez caracteres alfanuméricos, validade de 48 horas e troca obrigatória no primeiro acesso.
- **Ressalva:** “servidor” é ambíguo e não estão definidos o responsável pela criação da conta nem o canal de entrega da credencial.
- **Para avaliação:** usar um termo como “usuário de suporte” ou “colaborador”, definir quem pode provisionar essas contas e avaliar convite de ativação de uso único em vez de distribuir senha temporária. Caso a senha temporária seja mantida, restringir o acesso à troca de senha até concluir a ativação.

### 8. Contas inativas

- **Na ata:** RF001 prevê exclusão lógica com status Inativo.
- **Ressalva:** RF002 não explicita os efeitos desse status na autenticação e nas sessões existentes.
- **Para avaliação:** impedir novos acessos de contas inativas e revogar suas sessões. Definir quem pode reativar uma conta e sob quais condições.

### 9. Organização e testabilidade do RF002

- **Na ata:** cadastro de usuário, autenticação, recuperação, sessão e segregação de perfis aparecem agrupados.
- **Ressalva:** o agrupamento dificulta identificar fluxos alternativos e critérios de aceite de cada responsabilidade.
- **Para avaliação:** separar em requisitos ou subfluxos rastreáveis: autenticar; manter/encerrar sessão; recuperar senha; ativar conta de suporte. Tratar autorização por perfil como regra transversal ou requisito próprio.
- **Consistência textual:** a mensagem “CPF ou senha inválidos” deve contemplar também o login por e-mail; por exemplo, “Identificador ou senha inválidos”.

## Cenários de aceite sugeridos

Estes cenários devem ser detalhados após a aprovação das regras e executados com contas e dados fictícios.

1. Login por CPF e por e-mail resolve para a mesma conta e compartilha a contagem de falhas.
2. Conta inexistente e senha incorreta produzem resposta genérica sem expor a existência do cadastro.
3. Ao atingir o limite de falhas, o bloqueio dura o período definido, respeitando as regras de contagem e reinício aprovadas.
4. Código de recuperação expirado, já utilizado, substituído ou com tentativas esgotadas é rejeitado.
5. Reenvios e solicitações de recuperação respeitam os limites definidos.
6. Sessão expira por inatividade e pelo prazo absoluto aprovado; logout impede reutilização da sessão encerrada.
7. Troca/recuperação de senha e desativação aplicam a política de revogação aprovada.
8. Um cliente não consegue consultar nem alterar recursos de outro cliente ao modificar CPF ou identificadores de recursos na requisição.
9. Usuário de suporte não acessa operações administrativas ou dados fora de suas permissões, mesmo por chamada direta à API.
10. Conta inativa não autentica, e suas sessões anteriores deixam de autorizar operações.
11. Convite de ativação ou senha temporária respeita validade, uso único quando aplicável e obrigatoriedade de definir a senha antes do acesso funcional.

## Prioridades para a próxima revisão

1. Fechar recuperação de senha, revogação de sessões e isolamento entre usuários.
2. Corrigir a terminologia de armazenamento de senhas e a interpretação do CPF no RS001.
3. Definir permissões, provisionamento de suporte e comportamento de contas inativas.
4. Desdobrar os fluxos e aprovar critérios de aceite verificáveis.

As prioridades acima são de revisão da especificação, não classificações de severidade de falhas comprovadas.
