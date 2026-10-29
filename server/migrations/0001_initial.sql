CREATE TABLE accounts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  cpf TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  birth_date TEXT NOT NULL,
  phone TEXT NOT NULL,
  postal_code TEXT NOT NULL,
  state TEXT NOT NULL,
  city TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','demo_confirmed','inactive')),
  created_at INTEGER NOT NULL,
  income INTEGER,
  fixed_expenses INTEGER,
  goal TEXT,
  completed_at INTEGER
);
CREATE TABLE sessions (
  token_hash TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id),
  created_at INTEGER NOT NULL,
  last_seen INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX sessions_account ON sessions(account_id);
CREATE INDEX sessions_expiry ON sessions(expires_at);
CREATE TABLE audit_events (
  id INTEGER PRIMARY KEY,
  account_id TEXT,
  event TEXT NOT NULL,
  ip_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX audit_account ON audit_events(account_id, created_at);
CREATE TABLE lessons (id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, body TEXT NOT NULL, minutes INTEGER NOT NULL);
INSERT INTO lessons VALUES
('first-budget','Seu primeiro orçamento','Um plano possível começa com o que você já sabe.','Liste sua renda e os compromissos que se repetem todos os meses. Separe estimativas de valores já pagos. Reserve espaço para gastos variáveis e revise seu planejamento ao longo do mês. Um orçamento útil acompanha a vida real: ele pode ser ajustado.',3),
('emergency-fund','Uma reserva, um passo de cada vez','Tranquilidade também se constrói aos poucos.','Comece por uma meta pequena e possível dentro do seu orçamento. Pense nas despesas essenciais e no que você precisa para lidar com imprevistos. Acompanhe sua evolução sem comparar seu ritmo com o de outras pessoas. Este material é educativo e não recomenda produtos financeiros.',4),
('due-dates','Contas em dia, mente tranquila','Encontre um jeito simples de organizar seus vencimentos.','Liste as contas a pagar e os valores a receber, com suas datas. Diferencie previsão, vencimento e pagamento: não são a mesma coisa. Revisar essa lista semanalmente ajuda a perceber conflitos entre entradas e saídas antes que aconteçam.',3);
