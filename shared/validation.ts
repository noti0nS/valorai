import { z } from 'zod';

export const digits = (value: string) => value.replace(/\D/g, '');
export function validCpf(value: string) {
  const cpf = digits(value);
  if (cpf.length !== 11 || /^(\d)\1+$/.test(cpf)) return false;
  return [9, 10].every((size) => {
    const sum = [...cpf.slice(0, size)].reduce((total, n, index) => total + Number(n) * (size + 1 - index), 0);
    return ((sum * 10) % 11) % 10 === Number(cpf[size]);
  });
}
export function oldEnough(value: string, today = new Date()) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T12:00:00Z`);
  if (Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value) return false;
  const cutoff = new Date(Date.UTC(today.getUTCFullYear() - 16, today.getUTCMonth(), today.getUTCDate(), 23, 59));
  return date <= cutoff && date.getUTCFullYear() >= 1900;
}
export const states = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'] as const;
export const personalSchema = z.object({
  name: z.string().trim().min(3, 'Informe seu nome completo.').max(120),
  cpf: z.string().transform(digits).refine(validCpf, 'Confira os dígitos do CPF.'),
  birthDate: z.string().refine((value) => oldEnough(value), 'É necessário ter pelo menos 16 anos.'),
  phone: z.string().transform(digits).refine((v) => /^[1-9]{2}9\d{8}$/.test(v), 'Informe DDD e celular com 9 dígitos.'),
  postalCode: z.string().transform(digits).refine((v) => v.length === 8, 'Informe os 8 dígitos do CEP.'),
  state: z.enum(states, { error: 'Selecione seu estado.' }),
  city: z.string().trim().min(2, 'Informe sua cidade.').max(100),
});
export const profileUpdateSchema = z.object({
  name: z.string().trim().min(3, 'Informe seu nome completo.').max(120),
  birthDate: z.string().refine((value) => oldEnough(value), 'É necessário ter pelo menos 16 anos.'),
  phone: z.string().transform(digits).refine((v) => /^[1-9]{2}9\d{8}$/.test(v), 'Informe DDD e celular com 9 dígitos.'),
  postalCode: z.string().transform(digits).refine((v) => v.length === 8, 'Informe os 8 dígitos do CEP.'),
  state: z.enum(states, { error: 'Selecione seu estado.' }),
  city: z.string().trim().min(2, 'Informe sua cidade.').max(100),
});
export const passwordSchema = z.string().min(8, 'Use pelo menos 8 caracteres.').max(32, 'Use no máximo 32 caracteres.')
  .regex(/[A-Z]/, 'Inclua uma letra maiúscula.').regex(/[0-9]/, 'Inclua um número.')
  .refine((v) => new TextEncoder().encode(v).length <= 72, 'A senha excede o limite de 72 bytes.');
export const accessSchema = z.object({
  email: z.email('Informe um e-mail válido.').max(200).transform((v) => v.trim().toLowerCase()),
  password: passwordSchema,
  confirmPassword: z.string(),
  demoConsent: z.literal(true, { error: 'Confirme que está testando o protótipo.' }),
}).refine((v) => v.password === v.confirmPassword, { path: ['confirmPassword'], message: 'As senhas precisam ser iguais.' });
export const registrationSchema = personalSchema.and(accessSchema);
export const goals = [
  { id: 'budget', title: 'Organizar meu orçamento', description: 'Entender para onde meu dinheiro vai.' },
  { id: 'debt', title: 'Sair das dívidas', description: 'Dar um passo de cada vez, com clareza.' },
  { id: 'reserve', title: 'Criar uma reserva', description: 'Ter mais tranquilidade para o amanhã.' },
  { id: 'invest', title: 'Começar a investir', description: 'Preparar o terreno para novos planos.' },
] as const;
export const financeSchema = z.object({
  income: z.number().min(0).max(100000000),
  fixedExpenses: z.number().min(0).max(100000000),
  goal: z.enum(['budget','debt','reserve','invest']),
});
export const standardCategories = [
  'Alimentação & Mercado',
  'Moradia (Fixo)',
  'Transporte',
  'Lazer & Restaurantes',
  'Educação',
  'Saúde',
  'Contas & Serviços',
  'Renda / Serviços',
  'Reserva & Investimentos',
  'Outros',
] as const;

export const transactionKinds = [
  { id: 'variable_expense', label: 'Despesa Variável' },
  { id: 'fixed_expense', label: 'Gasto Fixo' },
  { id: 'income', label: 'Receita / Entrada' },
] as const;

export const paymentMethods = [
  { id: 'debit', label: 'Débito em conta' },
  { id: 'credit', label: 'Cartão de crédito' },
  { id: 'pix', label: 'Pix' },
  { id: 'boleto', label: 'Boleto' },
  { id: 'cash', label: 'Dinheiro' },
  { id: 'transfer', label: 'Transferência' },
] as const;

const categoryRules: Array<{ keywords: string[]; category: string; kind: 'income' | 'fixed_expense' | 'variable_expense' }> = [
  { keywords: ['aluguel', 'condominio', 'condomínio', 'iptu', 'financiamento', 'habitacao', 'habitação', 'moradia'], category: 'Moradia (Fixo)', kind: 'fixed_expense' },
  { keywords: ['energia', 'conta de luz', 'eletricidade', 'agua', 'água', 'saneamento', 'internet', 'fibra', 'claro', 'tim', 'vivo', 'gás', 'seguro'], category: 'Contas & Serviços', kind: 'fixed_expense' },
  { keywords: ['pao de acucar', 'pão de açúcar', 'supermercado', 'mercado', 'atacadao', 'atacadão', 'assai', 'assaí', 'carrefour', 'padaria', 'hortifruti', 'feira'], category: 'Alimentação & Mercado', kind: 'variable_expense' },
  { keywords: ['uber', '99pop', '99app', 'taxi', 'táxi', 'combustivel', 'combustível', 'posto', 'ipiranga', 'shell', 'metro', 'metrô', 'onibus', 'ônibus', 'estacionamento'], category: 'Transporte', kind: 'variable_expense' },
  { keywords: ['restaurante', 'bistro', 'bistrô', 'ifood', 'lazer', 'cinema', 'teatro', 'show', 'bar', 'café', 'cafeteria', 'viagem', 'hotel', 'netflix', 'spotify'], category: 'Lazer & Restaurantes', kind: 'variable_expense' },
  { keywords: ['livraria', 'cultura', 'livro', 'curso', 'faculdade', 'escola', 'idioma', 'udemy', 'alura', 'educacao', 'educação'], category: 'Educação', kind: 'variable_expense' },
  { keywords: ['farmacia', 'farmácia', 'drogasil', 'droga raia', 'hospital', 'clinica', 'clínica', 'consulta', 'exame', 'medico', 'médico', 'dentista', 'plano de saude', 'plano de saúde'], category: 'Saúde', kind: 'variable_expense' },
  { keywords: ['reserva', 'tesouro', 'cdb', 'lci', 'lca', 'fii', 'acoes', 'ações', 'investimento', 'aporte', 'poupanca', 'poupança'], category: 'Reserva & Investimentos', kind: 'variable_expense' },
  { keywords: ['salario', 'salário', 'consultoria', 'freelance', 'dividendo', 'rendimento', 'reembolso', 'receita', 'pix recebido', 'transferencia recebida', 'transferência recebida'], category: 'Renda / Serviços', kind: 'income' },
];

export function suggestCategory(title: string, currentKind?: 'income' | 'fixed_expense' | 'variable_expense'): { category: string; kind: 'income' | 'fixed_expense' | 'variable_expense' } {
  const normalized = ` ${title.trim().toLowerCase()} `;
  for (const rule of categoryRules) {
    if (rule.keywords.some((kw) => normalized.includes(kw))) {
      const kind = currentKind ?? rule.kind;
      return { category: kind === 'income' ? 'Renda / Serviços' : rule.category, kind };
    }
  }
  if (currentKind === 'income') return { category: 'Renda / Serviços', kind: 'income' };
  if (currentKind === 'fixed_expense') return { category: 'Moradia (Fixo)', kind: 'fixed_expense' };
  return { category: 'Outros', kind: currentKind ?? 'variable_expense' };
}

export const transactionSchema = z.object({
  title: z.string().trim().min(2, 'Informe uma descrição entre 2 e 120 caracteres.').max(120),
  amount: z.number({ error: 'Informe um valor válido.' }).gt(0, 'Informe um valor maior que zero.').max(100000000),
  kind: z.enum(['income', 'fixed_expense', 'variable_expense']),
  category: z.string().trim().min(2, 'Selecione ou informe uma categoria.').max(60),
  occurredOn: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Informe uma data válida.'),
  status: z.enum(['paid', 'pending']).default('paid'),
  paymentMethod: z.enum(['pix', 'credit', 'debit', 'cash', 'boleto', 'transfer']).default('debit'),
});

export type Registration = z.infer<typeof registrationSchema>;
export type Finance = z.infer<typeof financeSchema>;
export function fieldErrors(error: z.ZodError): Record<string, string> {
  return Object.fromEntries(error.issues.map((issue) => [String(issue.path[0]), issue.message]));
}
export const maskCpf = (v: string) => digits(v).slice(0,11).replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
export const maskPhone = (v: string) => digits(v).slice(0,11).replace(/^(\d{2})(\d)/, '($1) $2').replace(/(\d{5})(\d)/, '$1-$2');
export const maskPostal = (v: string) => digits(v).slice(0,8).replace(/(\d{5})(\d)/, '$1-$2');
