import { DurableObject } from 'cloudflare:workers';
import bcrypt from 'bcryptjs';
import { registrationSchema, financeSchema, fieldErrors, digits } from '../../shared/validation';

interface Bindings {
  DB: D1Database;
  AUTH: DurableObjectNamespace;
  ASSETS: Fetcher;
  ENVIRONMENT: string;
  EMAIL_MODE: string;
  TURNSTILE_SITE_KEY?: string;
  TURNSTILE_SECRET_KEY?: string;
}
interface Account {
  id: string; name: string; email: string; cpf: string; password_hash: string;
  status: 'pending' | 'demo_confirmed' | 'inactive'; city: string; state: string;
  income: number | null; fixed_expenses: number | null; goal: string | null; completed_at: number | null;
}
type Challenge = { code: string; expires: number; attempts: number; sentAt: number; hour: number; sends: number };
const SESSION_SECONDS = 12 * 60 * 60;
const CONFIRM_SECONDS = 10 * 60; // Prototype setting; RF002 limits remain pending approval.
const json = (body: unknown, status = 200, headers: Record<string, string> = {}) => Response.json(body, {
  status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...headers },
});
const digest = async (value: string) => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))), n => n.toString(16).padStart(2, '0')).join('');
const now = () => Math.floor(Date.now() / 1000);
const cookie = (request: Request, value: string, maxAge = SESSION_SECONDS) => `valorai_session=${value}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${maxAge}${new URL(request.url).protocol === 'https:' ? '; Secure' : ''}`;
function publicAccount(a: Account) {
  return { id: a.id, name: a.name, email: a.email, city: a.city, state: a.state, status: a.status,
    finance: a.income === null ? null : { income: a.income / 100, fixedExpenses: (a.fixed_expenses ?? 0) / 100, goal: a.goal },
    completed: !!a.completed_at, emailVerified: false, demoConfirmed: a.status === 'demo_confirmed' };
}
class HttpError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
async function readBody(request: Request): Promise<Record<string, unknown>> {
  if (!request.headers.get('Content-Type')?.includes('application/json')) throw new HttpError(415, 'Envie dados em JSON.');
  const reader = request.body?.getReader();
  if (!reader) throw new HttpError(400, 'Dados ausentes.');
  const chunks: Uint8Array[] = []; let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.length;
    if (total > 16384) { await reader.cancel(); throw new HttpError(413, 'O formulário excedeu o tamanho permitido.'); }
    chunks.push(value);
  }
  const merged = new Uint8Array(total); let offset = 0;
  for (const chunk of chunks) { merged.set(chunk, offset); offset += chunk.length; }
  try {
    const value: unknown = JSON.parse(new TextDecoder().decode(merged));
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error();
    return value as Record<string, unknown>;
  } catch { throw new HttpError(400, 'Não foi possível ler o formulário.'); }
}

/** SQLite Durable Object serializes authentication transitions and runs bcrypt outside the lightweight routing Worker. */
export class AuthCoordinator extends DurableObject<Bindings> {
  async fetch(request: Request) {
    return this.ctx.blockConcurrencyWhile(async () => {
      try { return await this.handle(request); }
      catch (error) {
        if (error instanceof HttpError) return json({ error: error.message }, error.status);
        console.error('authentication_request_failed'); // Never log payloads, credentials, codes or SQL errors.
        return json({ error: 'Não foi possível concluir agora. Tente novamente em instantes.' }, 500);
      }
    });
  }

  async session(request: Request, confirmed = false) {
    const token = request.headers.get('Cookie')?.match(/(?:^|;\s*)valorai_session=([a-f0-9]{64})(?:;|$)/)?.[1];
    if (!token) throw new HttpError(401, 'Entre na sua conta para continuar.');
    const hash = await digest(token);
    const session = await this.env.DB.prepare('SELECT account_id, expires_at, last_seen FROM sessions WHERE token_hash = ?').bind(hash).first<{ account_id: string; expires_at: number; last_seen: number }>();
    if (!session || session.expires_at <= now() || session.last_seen <= now() - 1800) {
      if (session) await this.env.DB.prepare('DELETE FROM sessions WHERE token_hash = ?').bind(hash).run();
      throw new HttpError(401, 'Sua sessão expirou. Entre novamente para continuar.');
    }
    const account = await this.env.DB.prepare('SELECT * FROM accounts WHERE id = ?').bind(session.account_id).first<Account>();
    if (!account || account.status === 'inactive') throw new HttpError(401, 'Entre na sua conta para continuar.');
    if (confirmed && account.status !== 'demo_confirmed') throw new HttpError(403, 'Conclua a confirmação de demonstração primeiro.');
    // Deliberate authenticated API activity renews the idle timeout; no browser polling.
    await this.env.DB.prepare('UPDATE sessions SET last_seen = ? WHERE token_hash = ?').bind(now(), hash).run();
    return { account, hash };
  }
  async newSession(id: string, request: Request) {
    const token = crypto.randomUUID().replaceAll('-', '') + crypto.randomUUID().replaceAll('-', '');
    await this.env.DB.prepare('INSERT INTO sessions VALUES (?, ?, ?, ?, ?)').bind(await digest(token), id, now(), now(), now() + SESSION_SECONDS).run();
    return cookie(request, token);
  }
  async audit(id: string | null, event: string, request: Request) {
    await this.env.DB.prepare('INSERT INTO audit_events(account_id, event, ip_hash, created_at) VALUES (?, ?, ?, ?)')
      .bind(id, event, await digest(request.headers.get('CF-Connecting-IP') ?? 'local'), now()).run();
  }
  async throttle(request: Request) {
    const key = `rate:${await digest(request.headers.get('CF-Connecting-IP') ?? 'local')}`;
    const record = await this.ctx.storage.get<{ count: number; until: number }>(key);
    const next = !record || record.until <= now() ? { count: 1, until: now() + 60 } : { ...record, count: record.count + 1 };
    if (next.count > 30) throw new HttpError(429, 'Muitas tentativas. Aguarde um minuto.');
    await this.ctx.storage.put(key, next);
    if (!await this.ctx.storage.getAlarm()) await this.ctx.storage.setAlarm(Date.now() + 3600000);
  }
  async issueCode(id: string) {
    const previous = await this.ctx.storage.get<Challenge>(`code:${id}`);
    if (previous && previous.sentAt + 60 > now()) throw new HttpError(429, 'Aguarde 60 segundos entre envios.');
    const sameHour = previous && previous.hour + 3600 > now();
    if (sameHour && previous.sends >= 3) throw new HttpError(429, 'Limite de três envios por hora atingido.');
    const random = crypto.getRandomValues(new Uint32Array(1))[0];
    const challenge: Challenge = { code: String(random % 1000000).padStart(6, '0'), expires: now() + CONFIRM_SECONDS,
      attempts: 0, sentAt: now(), hour: sameHour ? previous.hour : now(), sends: sameHour ? previous.sends + 1 : 1 };
    await this.ctx.storage.put(`code:${id}`, challenge);
    return { expiresAt: challenge.expires, resendAt: challenge.sentAt + 60 };
  }
  async checkBot(request: Request, body: Record<string, unknown>) {
    if (this.env.ENVIRONMENT === 'development') return;
    if (!this.env.TURNSTILE_SECRET_KEY) throw new HttpError(503, 'A proteção do protótipo está sendo configurada.');
    const token = typeof body.turnstileToken === 'string' ? body.turnstileToken : '';
    const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', { method: 'POST', body: new URLSearchParams({
      secret: this.env.TURNSTILE_SECRET_KEY, response: token, remoteip: request.headers.get('CF-Connecting-IP') ?? '',
    }) });
    const result = await response.json() as { success: boolean; hostname?: string };
    if (!result.success || result.hostname !== new URL(request.url).hostname) throw new HttpError(400, 'Confirme a verificação de segurança e tente novamente.');
  }
  async handle(request: Request): Promise<Response> {
    const path = new URL(request.url).pathname;
    if (request.method === 'GET' && path === '/api/config') return json({ emailMode: 'demo', siteKey: this.env.TURNSTILE_SITE_KEY ?? '', confirmation: { seconds: CONFIRM_SECONDS, attempts: 5, resendSeconds: 60 }, prototype: true });
    if (request.method === 'GET' && path === '/api/session') {
      const { account } = await this.session(request);
      return json({ account: publicAccount(account) });
    }
    if (request.method === 'GET' && path === '/api/lessons') {
      await this.session(request, true);
      return json({ lessons: (await this.env.DB.prepare('SELECT * FROM lessons ORDER BY id').all()).results });
    }
    if (request.method === 'GET' && path === '/api/demo-inbox') {
      if (this.env.EMAIL_MODE !== 'demo') throw new HttpError(404, 'Indisponível.');
      const { account } = await this.session(request);
      if (account.status !== 'pending') throw new HttpError(409, 'Essa etapa já foi concluída.');
      const challenge = await this.ctx.storage.get<Challenge>(`code:${account.id}`);
      if (!challenge || challenge.expires <= now() || challenge.attempts >= 5) throw new HttpError(410, 'Código expirado. Solicite outro código.');
      return json({ code: challenge.code, to: account.email, expiresAt: challenge.expires, simulated: true });
    }
    if (request.method !== 'POST') throw new HttpError(404, 'Página não encontrada.');
    await this.throttle(request);
    const body = await readBody(request);
    if (path === '/api/register') {
      const parsed = registrationSchema.safeParse(body);
      if (!parsed.success) return json({ error: 'Confira os campos destacados.', fields: fieldErrors(parsed.error) }, 422);
      await this.checkBot(request, body);
      const data = parsed.data;
      const existing = await this.env.DB.prepare('SELECT id FROM accounts WHERE cpf = ? OR email = ?').bind(data.cpf, data.email).first();
      if (existing) throw new HttpError(409, 'Não foi possível criar uma nova conta com esses dados. Tente entrar na conta existente.');
      const id = crypto.randomUUID();
      const hash = bcrypt.hashSync(data.password, 10);
      await this.env.DB.prepare('INSERT INTO accounts(id, name, cpf, email, birth_date, phone, postal_code, state, city, password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
        .bind(id, data.name, data.cpf, data.email, data.birthDate, data.phone, data.postalCode, data.state, data.city, hash, now()).run();
      const timing = await this.issueCode(id);
      const sessionCookie = await this.newSession(id, request);
      await this.audit(id, 'registration_created', request);
      const account = await this.env.DB.prepare('SELECT * FROM accounts WHERE id = ?').bind(id).first<Account>();
      return json({ account: publicAccount(account!), ...timing }, 201, { 'Set-Cookie': sessionCookie });
    }
    if (path === '/api/login') {
      await this.checkBot(request, body);
      const identifier = typeof body.identifier === 'string' ? body.identifier.trim().toLowerCase().slice(0, 200) : '';
      const password = typeof body.password === 'string' ? body.password : '';
      if (password.length > 32 || new TextEncoder().encode(password).length > 72) throw new HttpError(401, 'Identificador ou senha inválidos.');
      const account = await this.env.DB.prepare('SELECT * FROM accounts WHERE email = ? OR cpf = ?').bind(identifier, digits(identifier)).first<Account>();
      const key = `login:${account?.id ?? await digest(identifier)}`;
      const failure = await this.ctx.storage.get<{ count: number; window: number; blockedUntil: number }>(key);
      if (failure && failure.blockedUntil > now()) throw new HttpError(401, 'Identificador ou senha inválidos. Se houve várias tentativas, aguarde cinco minutos.');
      const matches = account ? bcrypt.compareSync(password, account.password_hash) : (bcrypt.hashSync(password || 'invalid', 10), false);
      if (!account || !matches || account.status === 'inactive') {
        const expired = !failure || (failure.blockedUntil > 0 && failure.blockedUntil <= now()) || failure.window + 900 <= now();
        const count = expired ? 1 : failure.count + 1;
        await this.ctx.storage.put(key, { count, window: expired ? now() : failure.window, blockedUntil: count >= 5 ? now() + 300 : 0 });
        await this.audit(account?.id ?? null, 'login_failed', request);
        throw new HttpError(401, 'Identificador ou senha inválidos.');
      }
      await this.ctx.storage.delete(key);
      await this.audit(account.id, 'login_succeeded', request);
      return json({ account: publicAccount(account) }, 200, { 'Set-Cookie': await this.newSession(account.id, request) });
    }
    const { account, hash } = await this.session(request);
    if (path === '/api/logout') {
      await this.env.DB.prepare('DELETE FROM sessions WHERE token_hash = ?').bind(hash).run();
      return json({ ok: true }, 200, { 'Set-Cookie': cookie(request, '', 0) });
    }
    if (path === '/api/resend') {
      if (account.status !== 'pending') throw new HttpError(409, 'Essa etapa já foi concluída.');
      return json(await this.issueCode(account.id));
    }
    if (path === '/api/confirm') {
      if (account.status !== 'pending') throw new HttpError(409, 'Essa etapa já foi concluída.');
      const challenge = await this.ctx.storage.get<Challenge>(`code:${account.id}`);
      if (!challenge || challenge.expires <= now() || challenge.attempts >= 5) throw new HttpError(410, 'Código expirado ou bloqueado. Solicite outro.');
      if (typeof body.code !== 'string' || !/^\d{6}$/.test(body.code) || body.code !== challenge.code) {
        challenge.attempts++;
        await this.ctx.storage.put(`code:${account.id}`, challenge);
        throw new HttpError(400, challenge.attempts >= 5 ? 'Limite de tentativas atingido. Solicite outro código.' : 'Código incorreto. Confira os seis dígitos.');
      }
      // Deliberately not an email_verified flag: the inbox is a demonstration.
      await this.env.DB.prepare("UPDATE accounts SET status = 'demo_confirmed' WHERE id = ? AND status = 'pending'").bind(account.id).run();
      await this.ctx.storage.delete(`code:${account.id}`);
      await this.env.DB.prepare('DELETE FROM sessions WHERE account_id = ?').bind(account.id).run();
      await this.audit(account.id, 'demo_confirmation_completed', request);
      return json({ account: publicAccount({ ...account, status: 'demo_confirmed' }) }, 200, { 'Set-Cookie': await this.newSession(account.id, request) });
    }
    if (account.status !== 'demo_confirmed') throw new HttpError(403, 'Conclua a confirmação de demonstração primeiro.');
    if (path === '/api/finance') {
      const parsed = financeSchema.safeParse(body);
      if (!parsed.success) return json({ error: 'Confira os valores e selecione um objetivo.', fields: fieldErrors(parsed.error) }, 422);
      const data = parsed.data;
      const updated = await this.env.DB.prepare('UPDATE accounts SET income = ?, fixed_expenses = ?, goal = ?, completed_at = ? WHERE id = ? RETURNING *')
        .bind(Math.round(data.income * 100), Math.round(data.fixedExpenses * 100), data.goal, now(), account.id).first<Account>();
      await this.audit(account.id, 'financial_profile_updated', request);
      return json({ account: publicAccount(updated!) });
    }
    if (path === '/api/deactivate') {
      const password = typeof body.password === 'string' ? body.password : '';
      if (password.length > 32 || !bcrypt.compareSync(password, account.password_hash)) throw new HttpError(400, 'Confira sua senha para confirmar a desativação.');
      await this.env.DB.batch([
        this.env.DB.prepare("UPDATE accounts SET status = 'inactive' WHERE id = ?").bind(account.id),
        this.env.DB.prepare('DELETE FROM sessions WHERE account_id = ?').bind(account.id),
      ]);
      await this.ctx.storage.delete(`code:${account.id}`);
      await this.audit(account.id, 'account_deactivated', request);
      return json({ ok: true }, 200, { 'Set-Cookie': cookie(request, '', 0) });
    }
    throw new HttpError(404, 'Operação não encontrada.');
  }
  async alarm() {
    const records = await this.ctx.storage.list<Record<string, number>>();
    for (const [key, value] of records) {
      if ((key.startsWith('rate:') && value.until <= now()) || (key.startsWith('code:') && value.hour + 3600 <= now()) || (key.startsWith('login:') && value.window + 900 <= now() && value.blockedUntil <= now())) await this.ctx.storage.delete(key);
    }
    await this.env.DB.prepare('DELETE FROM sessions WHERE expires_at <= ?').bind(now()).run();
    if ((await this.ctx.storage.list({ limit: 1 })).size) await this.ctx.storage.setAlarm(Date.now() + 3600000);
  }
}

export default {
  async fetch(request: Request, env: Bindings): Promise<Response> {
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(request);
    if (request.method === 'POST' && request.headers.get('Origin') !== url.origin) return json({ error: 'Origem não autorizada.' }, 403);
    if (!['GET','POST'].includes(request.method)) return json({ error: 'Método não permitido.' }, 405);
    try { return await env.AUTH.get(env.AUTH.idFromName('accounts-v1')).fetch(request); }
    catch { return json({ error: 'Serviço temporariamente indisponível. Tente novamente.' }, 503); }
  },
} satisfies ExportedHandler<Bindings>;
