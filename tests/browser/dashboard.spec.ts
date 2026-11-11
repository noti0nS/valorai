import { test, expect, type APIRequestContext } from '@playwright/test';
import crypto from 'node:crypto';

const origin = 'http://127.0.0.1:8787';

function fixture() {
  const n = Array.from(crypto.randomBytes(9), b => b % 10);
  for (const size of [9, 10]) n.push((n.slice(0, size).reduce((sum, v, i) => sum + v * (size + 1 - i), 0) * 10 % 11) % 10);
  return {
    name: 'Mariana Costa',
    cpf: n.join(''),
    birthDate: '1994-04-12',
    phone: '82998887766',
    postalCode: '57035000',
    state: 'AL',
    city: 'Maceió',
    email: `mariana-${crypto.randomUUID()}@example.com`,
    password: 'PrototypeOnly8',
    confirmPassword: 'PrototypeOnly8',
    demoConsent: true,
  };
}

const post = (client: APIRequestContext, route: string, data: unknown) =>
  client.post(`/api/${route}`, { data, headers: { Origin: origin } });

test('Stitch dashboard operational flow: 3 input channels, limits & non-blocking alerts, goal contribution, RF003 profile, and sub-pages', async ({ page }) => {
  const data = fixture();
  const consoleErrors: string[] = [];
  page.on('pageerror', error => consoleErrors.push(error.message));

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.route('https://viacep.com.br/**', route => route.fulfill({ json: { localidade: 'Maceió', uf: 'AL' } }));
  await page.route('https://servicodados.ibge.gov.br/**', route => route.fulfill({ json: [{ nome: 'Maceió' }, { nome: 'Arapiraca' }] }));

  // Fast setup via API in the page context
  expect((await post(page.request, 'register', data)).status()).toBe(201);
  const inbox = await (await page.request.get('/api/demo-inbox')).json();
  expect((await post(page.request, 'confirm', { code: inbox.code })).status()).toBe(200);
  expect((await post(page.request, 'finance', { income: 4200, fixedExpenses: 1700, goal: 'reserve' })).status()).toBe(200);

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Visão Geral' })).toBeVisible();
  await expect(page.getByText('R$ 2.500,00', { exact: true })).toBeVisible();

  // 1. Channel 1: Manual Transaction via Unified 'Novo Lançamento' Button
  await page.getByRole('button', { name: /Novo Lançamento/ }).click();
  await page.getByRole('button', { name: 'Digitação manual' }).click();
  const manualDialog = page.getByRole('dialog');
  await expect(manualDialog).toBeVisible();
  await manualDialog.getByLabel('Descrição / Estabelecimento').fill('Restaurante Sabor Nordestino');
  await expect(manualDialog.getByLabel('Categoria (obrigatória)')).toHaveValue('Lazer & Restaurantes');
  await manualDialog.getByLabel('Valor (R$)').fill('120');
  await manualDialog.getByRole('button', { name: 'Registrar lançamento' }).click();
  await expect(page.getByText('Restaurante Sabor Nordestino')).toBeVisible();

  // 2. Channel 2: AI/OCR Receipt Extraction & Validation via 'Novo Lançamento'
  await page.getByRole('button', { name: /Novo Lançamento/ }).click();
  await page.getByRole('button', { name: 'Ler comprovante (OCR)' }).click();
  const receiptDialog = page.getByRole('dialog');
  await expect(receiptDialog).toBeVisible();
  await receiptDialog.getByRole('button', { name: 'NFC-e Supermercado (R$ 342,80)' }).click();
  await expect(receiptDialog.getByText(/Confiança IA:/)).toBeVisible();
  await expect(receiptDialog.getByLabel('Estabelecimento identificado')).toHaveValue('Pão de Açúcar • Supermercado');
  await receiptDialog.getByRole('button', { name: 'Confirmar e lançar comprovante' }).click();
  await expect(page.getByText('Pão de Açúcar • Supermercado')).toBeVisible();

  // 3. Channel 3: Batch Import (OFX) with Deduplication via 'Novo Lançamento'
  await page.getByRole('button', { name: /Novo Lançamento/ }).click();
  await page.getByRole('button', { name: 'Importar OFX / CSV' }).click();
  const importDialog = page.getByRole('dialog');
  await expect(importDialog).toBeVisible();
  // Verify that canceling a native file/input picker (which fires a bubbling `cancel` event) does not close the modal
  await importDialog.locator('#importFileInput').evaluate((el) => {
    el.dispatchEvent(new Event('cancel', { bubbles: true }));
  });
  await expect(importDialog).toBeVisible();
  await importDialog.getByRole('button', { name: 'Testar Extrato OFX Bancário' }).click();
  await expect(importDialog.getByText('Aluguel e Condominio Residencial')).toBeVisible();
  await importDialog.getByRole('button', { name: 'Confirmar importação em lote' }).click();
  await expect(page.getByText('Aluguel e Condominio Residencial')).toBeVisible();

  // 4. Budget Limit & Non-Blocking Alert
  await page.getByRole('button', { name: 'Configurar teto de gastos' }).click();
  const limitDialog = page.getByRole('dialog');
  await expect(limitDialog).toBeVisible();
  await limitDialog.getByLabel('Categoria monitorada').selectOption('Alimentação & Mercado');
  await limitDialog.getByLabel('Valor do teto (R$)').fill('500');
  await limitDialog.getByRole('button', { name: 'Salvar teto' }).click();
  await expect(page.getByText('Aviso de referência para disciplina orçamentária. Gastos não são bloqueados.')).toBeVisible();

  // 5. RF003 Personal Profile Update via Condensed Profile Panel
  await page.getByRole('button', { name: /Painel do perfil/ }).click();
  await page.getByRole('button', { name: 'Editar cadastro' }).click();
  const profileDialog = page.getByRole('dialog');
  await expect(profileDialog).toBeVisible();
  await expect(profileDialog.getByLabel('CPF (inalterável)')).toBeDisabled();
  await profileDialog.getByLabel('Nome completo').fill('Mariana Costa Silva');
  await profileDialog.getByRole('button', { name: 'Salvar dados cadastrais' }).click();
  await expect(page.getByText('Dados cadastrais atualizados e registrados no histórico.')).toBeVisible();

  // 6. Navigate Sub-views via Header Navigation (no duplicate switcher)
  await page.locator('.header-nav').getByRole('button', { name: 'Transações & Extratos' }).click();
  await expect(page.getByRole('heading', { name: 'Extrato & Conciliação de Movimentações' })).toBeVisible();
  await expect(page.getByText(/Extraído via IA • 99%/)).toBeVisible();

  await page.locator('.header-nav').getByRole('button', { name: 'Planejamento' }).click();
  await expect(page.getByRole('heading', { name: 'Metas & Limites Orçamentários' })).toBeVisible();

  // 7. Priority Goal Contribution (Aporte) in Planning view
  await page.getByRole('button', { name: 'Registrar aporte / Ajustar meta' }).click();
  const goalDialog = page.getByRole('dialog');
  await expect(goalDialog).toBeVisible();
  await goalDialog.getByLabel('Novo aporte hoje (opcional R$)').fill('500');
  await goalDialog.getByRole('button', { name: 'Salvar evolução da meta' }).click();
  await expect(page.getByText(/Aporte de R\$\s*500,00 registrado na sua meta\./)).toBeVisible();

  await page.locator('.header-nav').getByRole('button', { name: 'Guias' }).click();
  await expect(page.getByRole('heading', { name: 'Biblioteca de Educação Financeira' })).toBeVisible();
  await page.getByRole('button', { name: 'Ler guia' }).first().click();
  await page.getByRole('button', { name: 'Marcar como concluído' }).click();
  await expect(page.getByText('Leitura concluída').first()).toBeVisible();
  await page.getByRole('button', { name: 'Fechar guia' }).click();

  await page.locator('.header-nav').getByRole('button', { name: 'Visão Geral' }).click();
  await page.screenshot({ path: 'test-results/stitch-dashboard-operational.png', fullPage: true });
  expect(consoleErrors).toEqual([]);
});
