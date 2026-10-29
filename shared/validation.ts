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
export const personalSchema = z.object({
  name: z.string().trim().min(3, 'Informe seu nome completo.').max(120),
  cpf: z.string().transform(digits).refine(validCpf, 'Confira os dígitos do CPF.'),
  birthDate: z.string().refine((value) => oldEnough(value), 'É necessário ter pelo menos 16 anos.'),
  phone: z.string().transform(digits).refine((v) => /^[1-9]{2}9\d{8}$/.test(v), 'Informe DDD e celular com 9 dígitos.'),
  postalCode: z.string().transform(digits).refine((v) => v.length === 8, 'Informe os 8 dígitos do CEP.'),
  state: z.enum(['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'], { error: 'Selecione seu estado.' }),
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
export type Registration = z.infer<typeof registrationSchema>;
export type Finance = z.infer<typeof financeSchema>;
export function fieldErrors(error: z.ZodError): Record<string, string> {
  return Object.fromEntries(error.issues.map((issue) => [String(issue.path[0]), issue.message]));
}
export const maskCpf = (v: string) => digits(v).slice(0,11).replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
export const maskPhone = (v: string) => digits(v).slice(0,11).replace(/^(\d{2})(\d)/, '($1) $2').replace(/(\d{5})(\d)/, '$1-$2');
export const maskPostal = (v: string) => digits(v).slice(0,8).replace(/(\d{5})(\d)/, '$1-$2');
