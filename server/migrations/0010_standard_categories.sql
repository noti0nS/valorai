-- Aligns stored category names with the ten standard categories of RF013 (rev. 1.4).
-- Custom categories are left untouched. Audit triggers only write when audit_context is bound, so this is silent.
UPDATE transactions SET category = 'Alimentação'   WHERE category = 'Alimentação & Mercado';
UPDATE transactions SET category = 'Moradia'       WHERE category = 'Moradia (Fixo)';
UPDATE transactions SET category = 'Lazer'         WHERE category = 'Lazer & Restaurantes';
UPDATE transactions SET category = 'Serviços'      WHERE category = 'Contas & Serviços';
UPDATE transactions SET category = 'Renda'         WHERE category = 'Renda / Serviços';
UPDATE transactions SET category = 'Investimentos' WHERE category = 'Reserva & Investimentos';

-- budget_limits has UNIQUE(account_id, scope, category): OR IGNORE keeps a pre-existing row on collision.
UPDATE OR IGNORE budget_limits SET category = 'Alimentação'   WHERE scope = 'category' AND category = 'Alimentação & Mercado';
UPDATE OR IGNORE budget_limits SET category = 'Moradia'       WHERE scope = 'category' AND category = 'Moradia (Fixo)';
UPDATE OR IGNORE budget_limits SET category = 'Lazer'         WHERE scope = 'category' AND category = 'Lazer & Restaurantes';
UPDATE OR IGNORE budget_limits SET category = 'Serviços'      WHERE scope = 'category' AND category = 'Contas & Serviços';
UPDATE OR IGNORE budget_limits SET category = 'Renda'         WHERE scope = 'category' AND category = 'Renda / Serviços';
UPDATE OR IGNORE budget_limits SET category = 'Investimentos' WHERE scope = 'category' AND category = 'Reserva & Investimentos';
