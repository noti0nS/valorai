import test from 'node:test';
import assert from 'node:assert/strict';
import { validCpf, oldEnough, passwordSchema, registrationSchema, financeSchema } from '../shared/validation';

test('CPF verifies both check digits and rejects repeated digits', () => {
  assert.equal(validCpf('529.982.247-25'), true);
  assert.equal(validCpf('529.982.247-24'), false);
  assert.equal(validCpf('111.111.111-11'), false);
  assert.equal(validCpf('123'), false);
});
test('age validation respects the exact sixteenth birthday and rejects impossible dates', () => {
  const today = new Date('2026-10-29T12:00:00Z');
  assert.equal(oldEnough('2010-10-29', today), true);
  assert.equal(oldEnough('2010-10-30', today), false);
  assert.equal(oldEnough('2000-02-30', today), false);
  assert.equal(oldEnough('2030-01-01', today), false);
});
test('bcrypt input is never silently truncated, including multibyte passwords', () => {
  assert.equal(passwordSchema.safeParse('DemoPassword8').success, true);
  assert.equal(passwordSchema.safeParse('a'.repeat(8)).success, false);
  assert.equal(passwordSchema.safeParse('A1' + '界'.repeat(24)).success, false);
  assert.equal(passwordSchema.safeParse('A1' + 'x'.repeat(31)).success, false);
});
test('registration requires matching passwords and explicit demonstration consent', () => {
  const data = { name: 'Cliente de Teste', cpf: '529.982.247-25', birthDate: '1995-01-01', phone: '(82) 99999-0000', postalCode: '57000-000', state: 'AL', city: 'Maceió', email: 'fixture@example.com', password: 'TestingOnly8', confirmPassword: 'Different8', demoConsent: true };
  assert.equal(registrationSchema.safeParse(data).success, false);
  assert.equal(registrationSchema.safeParse({ ...data, confirmPassword: data.password }).success, true);
  assert.equal(registrationSchema.safeParse({ ...data, confirmPassword: data.password, demoConsent: false }).success, false);
});
test('financial estimates permit zero and deficits but reject invalid amounts', () => {
  assert.equal(financeSchema.safeParse({ income: 0, fixedExpenses: 50, goal: 'budget' }).success, true);
  for (const income of [-1, NaN, Infinity]) assert.equal(financeSchema.safeParse({ income, fixedExpenses: 0, goal: 'budget' }).success, false);
});
