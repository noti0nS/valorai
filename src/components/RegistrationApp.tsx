import { useEffect, useRef, useState, type SyntheticEvent, type ReactNode } from 'react';
import { AnimatePresence, motion, MotionConfig } from 'motion/react';
import { ArrowRight, ArrowLeft, Check, Eye, EyeOff, Mail, Wallet, CreditCard, PiggyBank, TrendingUp, X, Info, LoaderCircle, LogOut, CheckCircle2, MapPin, Clock3, CircleAlert, PenLine, FileUp, Camera, BellRing, RotateCcw } from 'lucide-react';
import { CompanyMark, ProductMark } from './BrandMark';
import { ThemeToggle } from './ThemeToggle';
import { personalSchema, accessSchema, financeSchema, fieldErrors, goals, maskCpf, maskPhone, maskPostal, digits, states } from '../../shared/validation';
import DashboardWorkspace, { LightDismissModal, type AccountSummary, type DashboardData, type DashboardLesson, type ProfileData } from './DashboardWorkspace';
import { MarkdownContent } from './MarkdownContent';

type Account = AccountSummary;
type Config = {
  emailMode: string;
  siteKey: string;
  confirmation: { seconds: number; attempts: number; resendSeconds: number };
  aiEnabled?: boolean;
  aiTier?: 'free_prototype' | 'paid';
  aiModel?: string;
};
type Lesson = DashboardLesson;
type Values = { name: string; cpf: string; birthDate: string; phone: string; postalCode: string; state: string; city: string; email: string; password: string; confirmPassword: string; demoConsent: boolean };
const initial: Values = { name: '', cpf: '', birthDate: '', phone: '', postalCode: '', state: '', city: '', email: '', password: '', confirmPassword: '', demoConsent: false };
const stepNames = ['Dados', 'Acesso', 'Confirmação', 'Perfil'];
const currency = (v: number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v);
class ApiError extends Error {
  constructor(message: string, public status: number, public fields?: Record<string, string>) { super(message); }
}
async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/${path}`, { credentials: 'same-origin', method: body === undefined ? 'GET' : 'POST',
    signal: AbortSignal.timeout(15000),
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new ApiError(data.error || 'Tente novamente em instantes.', response.status, data.fields);
  return data as T;
}
type TurnstileApi = { render: (element: HTMLElement, options: Record<string, unknown>) => string; remove: (id: string) => void };
declare global { interface Window { turnstile?: TurnstileApi } }
function BotCheck({ siteKey, onToken, reset }: { siteKey: string; onToken: (token: string) => void; reset: number }) {
  const container = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  const callback = useRef(onToken); callback.current = onToken;
  useEffect(() => {
    if (!siteKey) return;
    setFailed(false);
    let id: string | undefined; let disposed = false;
    const fail = () => { if (!disposed) { callback.current(''); setFailed(true); } };
    const render = () => {
      if (disposed || !container.current || !window.turnstile) return;
      if (id) { window.turnstile.remove(id); id = undefined; }
      if (!id) {
        try {
          id = window.turnstile.render(container.current, {
            sitekey: siteKey, theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light', size: 'flexible',
            callback: (token: string) => { if (!disposed) { setFailed(false); callback.current(token); } },
            'expired-callback': () => callback.current(''),
            'error-callback': fail, 'timeout-callback': fail,
          });
        } catch { fail(); }
      }
    };
    let script = document.querySelector<HTMLScriptElement>('#turnstile-script');
    if (retry > 0 && script && !window.turnstile) { script.remove(); script = null; }
    if (!script) { script = document.createElement('script'); script.id = 'turnstile-script'; script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'; script.async = true; document.head.append(script); }
    const onTheme = () => render();
    script.addEventListener('load', render); script.addEventListener('error', fail); window.addEventListener('valorai-theme', onTheme); render();
    return () => { disposed = true; script?.removeEventListener('load', render); script?.removeEventListener('error', fail); window.removeEventListener('valorai-theme', onTheme); if (id) window.turnstile?.remove(id); callback.current(''); };
  }, [siteKey, reset, retry]);
  return <><div className="bot-check" ref={container} />{failed && <div className="note" role="alert"><Info size={16} /><span>A verificação de segurança não foi concluída. Confira sua conexão. <button type="button" className="link-button" onClick={() => setRetry(v => v + 1)}>Tentar novamente</button></span></div>}</>;
}
function Field({ label, id, error, children, hint, wide = false }: { label: string; id: string; error?: string; children: ReactNode; hint?: string; wide?: boolean }) {
  return <div className={`field ${wide ? 'wide' : ''} ${error ? 'has-error' : ''}`}><label htmlFor={id}>{label}</label>{children}
    {error ? <span className="field-error" id={`${id}-help`}><CircleAlert size={13} />{error}</span> : hint ? <span className="field-hint" id={`${id}-help`}>{hint}</span> : null}</div>;
}
function Modal({ title, children, onClose, wide = false }: { title: string; children: ReactNode; onClose: () => void; wide?: boolean }) {
  return <LightDismissModal title={title} onClose={onClose} wide={wide}>{children}</LightDismissModal>;
}
const channelIcon = { manual: PenLine, import: FileUp, photo: Camera };
const sample = [
  { title: 'Salário', category: 'Renda', channel: 'manual', via: 'manual', value: 3500 },
  { title: 'Supermercado', category: 'Alimentação', channel: 'photo', via: 'foto do comprovante', value: -186.4 },
  { title: 'Conta de luz', category: 'Moradia', channel: 'import', via: 'extrato OFX', value: -142.9 },
  { title: 'Farmácia', category: 'Saúde', channel: 'import', via: 'planilha CSV', value: -38.5 },
] as const;
function ProductPreview() {
  return <aside className="preview" aria-labelledby="preview-title">
    <h2 id="preview-title">Saiba para onde vai cada real.</h2>
    <p>Lançamentos digitados, importados de CSV, Excel ou OFX, ou lidos da foto de um comprovante. Cada um com sua categoria, e limites que avisam você.</p>
    <div className="ledger" role="group" aria-label="Extrato de exemplo">
      <div className="ledger-head"><strong>Outubro</strong><span>Exemplo</span></div>
      <ul>{sample.map(item => { const Icon = channelIcon[item.channel]; return <li key={item.title}><strong>{item.title}</strong>
        <span className={item.value > 0 ? 'income' : ''}>{item.value > 0 ? '+' : '−'} {currency(Math.abs(item.value))}</span>
        <small><span className="category">{item.category}</span><span><Icon size={14} aria-hidden="true" />{item.via}</span></small></li>; })}</ul>
    </div>
    <div className="limit">
      <div className="limit-top"><strong>Limite de Alimentação</strong><span className="num">R$ 612,30 de R$ 600,00</span></div>
      <div className="limit-bar" aria-hidden="true"><span /></div>
      <p><BellRing size={15} aria-hidden="true" /><span>Limite atingido. O alerta avisa; nenhum pagamento é bloqueado.</span></p>
    </div>
    <p className="preview-foot">Ilustração do produto. Este protótipo cobre o cadastro, o perfil financeiro, lançamentos, importação, comprovantes e alertas inteligentes.</p>
  </aside>;
}
export default function RegistrationApp() {
  const [step, setStep] = useState(0);
  const [view, setView] = useState<'register' | 'login' | 'recovery' | 'dashboard' | 'deactivated'>('login');
  const [dashTab, setDashTab] = useState<'overview' | 'transactions' | 'planning' | 'guides'>('overview');
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [values, setValues] = useState<Values>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [loadingSession, setLoadingSession] = useState(true);
  const [config, setConfig] = useState<Config | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [token, setToken] = useState('');
  const [botReset, setBotReset] = useState(0);
  const [code, setCode] = useState('');
  const [resendAt, setResendAt] = useState(0);
  const [time, setTime] = useState(Date.now() / 1000);
  const [modal, setModal] = useState<'about' | 'inbox' | 'deactivate' | 'password' | null>(null);
  const [inbox, setInbox] = useState<{ code: string; to: string; expiresAt: number; subject?: string } | null>(null);
  const [inboxError, setInboxError] = useState('');
  const [income, setIncome] = useState('');
  const [expenses, setExpenses] = useState('');
  const [goal, setGoal] = useState('');
  const [identifier, setIdentifier] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [recoveryStep, setRecoveryStep] = useState<0 | 1>(0);
  const [recoveryEmail, setRecoveryEmail] = useState('');
  const [recoveryCode, setRecoveryCode] = useState('');
  const [recoveryPassword, setRecoveryPassword] = useState('');
  const [recoveryConfirm, setRecoveryConfirm] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [passwordErrors, setPasswordErrors] = useState<Record<string, string>>({});
  const [passwordError, setPasswordError] = useState('');
  const [deactivatePassword, setDeactivatePassword] = useState('');
  const [deactivateError, setDeactivateError] = useState('');
  const [postalStatus, setPostalStatus] = useState('');
  const [cities, setCities] = useState<string[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const postalValue = useRef('');

  function resume(a: Account, nextDashboard?: DashboardData, nextProfile?: ProfileData) {
    setAccount(a);
    if (nextDashboard) {
      setDashboard(nextDashboard);
      if (nextDashboard.lessons?.length) setLessons(nextDashboard.lessons);
    }
    if (nextProfile) setProfile(nextProfile);
    setValues(v => ({ ...v, name: a.name, email: a.email, password: '', confirmPassword: '' }));
    if (a.finance) { setIncome(String(a.finance.income)); setExpenses(String(a.finance.fixedExpenses)); setGoal(a.finance.goal); }
    else { setIncome(''); setExpenses(''); setGoal(''); }
    if (a.status === 'pending') { setStep(2); setView('register'); }
    else if (a.completed) setView('dashboard');
    else { setStep(3); setView('register'); }
  }
  useEffect(() => {
    Promise.allSettled([
      api<Config>('config').then(setConfig).catch(() => setError('Não foi possível conectar. Verifique sua conexão e recarregue a página.')),
      api<{ account: Account }>('session').then(({ account }) => resume(account)),
    ]).finally(() => setLoadingSession(false));
  }, []);
  useEffect(() => {
    if (view !== 'dashboard') return;
    api<{ account: Account; profile: ProfileData; dashboard: DashboardData }>('dashboard')
      .then((res) => {
        setAccount(res.account);
        setProfile(res.profile);
        setDashboard(res.dashboard);
        if (res.dashboard.lessons?.length) setLessons(res.dashboard.lessons);
      })
      .catch(() => {
        api<{ lessons: Lesson[] }>('lessons')
          .then(v => setLessons(v.lessons))
          .catch(() => setNotice('Os materiais estão indisponíveis neste momento.'));
      });
  }, [view]);
  useEffect(() => { if (step !== 2) return; const id = setInterval(() => setTime(Date.now() / 1000), 1000); return () => clearInterval(id); }, [step]);
  useEffect(() => {
    if (!values.state) { setCities([]); return; }
    const controller = new AbortController();
    fetch(`https://servicodados.ibge.gov.br/api/v1/localidades/estados/${values.state}/municipios?orderBy=nome`, { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject()).then((data: { nome: string }[]) => setCities(data.map(c => c.nome))).catch(() => setCities([]));
    return () => controller.abort();
  }, [values.state]);

  function update(key: keyof Values, value: string | boolean) {
    setValues(v => ({ ...v, [key]: value })); setErrors(e => ({ ...e, [key]: '' }));
    if (key === 'postalCode') postalValue.current = String(value);
  }
  function showError(e: unknown) {
    setError(e instanceof Error ? e.message : 'Não foi possível continuar.');
    if (e instanceof ApiError && e.fields) setErrors(e.fields);
    if (e instanceof ApiError && e.status === 401 && view !== 'login') { setAccount(null); setView('login'); }
  }
  function invalid(fields: Record<string, string>) {
    setErrors(fields);
    requestAnimationFrame(() => document.getElementById(Object.keys(fields)[0])?.focus());
  }
  async function lookupPostal() {
    const cep = digits(values.postalCode);
    if (cep.length !== 8) return;
    postalValue.current = values.postalCode;
    setPostalStatus('Buscando sua cidade…');
    try {
      const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`, { signal: AbortSignal.timeout(6000) });
      const data = await response.json();
      if (digits(postalValue.current) !== cep) return;
      if (data.erro || !data.localidade) throw new Error();
      setValues(v => ({ ...v, city: data.localidade, state: data.uf })); setPostalStatus('Cidade encontrada. Confira os dados abaixo.');
    } catch { if (digits(postalValue.current) === cep) setPostalStatus('Você pode selecionar seu estado e preencher a cidade abaixo.'); }
  }
  async function submit(e: SyntheticEvent) {
    e.preventDefault(); setError(''); setNotice('');
    if (step === 0) {
      const parsed = personalSchema.safeParse(values);
      if (!parsed.success) return invalid(fieldErrors(parsed.error));
      setStep(1); return;
    }
    if (step === 1) {
      const parsed = accessSchema.safeParse(values);
      if (!parsed.success) return invalid(fieldErrors(parsed.error));
      setBusy(true);
      try {
        const data = await api<{ account: Account; resendAt: number }>('register', { ...values, turnstileToken: token });
        resume(data.account); setResendAt(data.resendAt);
      } catch (e) { showError(e); setBotReset(v => v + 1); }
      finally { setBusy(false); }
    } else if (step === 2) {
      if (!/^\d{6}$/.test(code)) return invalid({ code: 'Informe os seis dígitos do código.' });
      setBusy(true);
      try { const data = await api<{ account: Account }>('confirm', { code }); resume(data.account); setInbox(null); setCode(''); }
      catch (e) { showError(e); } finally { setBusy(false); }
    } else if (step === 3) {
      const data = { income: income === '' ? NaN : Number(income.replace(',', '.')), fixedExpenses: expenses === '' ? NaN : Number(expenses.replace(',', '.')), goal };
      const parsed = financeSchema.safeParse(data);
      if (!parsed.success) return invalid({ ...fieldErrors(parsed.error), ...(income === '' ? { income: 'Informe sua renda estimada, mesmo que seja zero.' } : {}), ...(expenses === '' ? { fixedExpenses: 'Informe seus gastos fixos estimados.' } : {}) });
      setBusy(true);
      try { const result = await api<{ account: Account; dashboard?: DashboardData }>('finance', data); resume(result.account, result.dashboard); }
      catch (e) { showError(e); } finally { setBusy(false); }
    }
  }
  async function login(e: SyntheticEvent) {
    e.preventDefault(); setError(''); setBusy(true);
    try { const { account } = await api<{ account: Account }>('login', { identifier, password: loginPassword, turnstileToken: token }); setLoginPassword(''); resume(account); }
    catch (e) { showError(e); setBotReset(v => v + 1); } finally { setBusy(false); }
  }
  async function logout() {
    setBusy(true); setError(''); setNotice('');
    try { await api('logout', {}); setAccount(null); setDashboard(null); setProfile(null); setView('login'); setValues(initial); setLessons([]); setInbox(null); }
    catch (e) { showError(e); } finally { setBusy(false); }
  }
  async function openInbox() {
    setModal('inbox'); setInbox(null); setInboxError('');
    try { setInbox(await api('demo-inbox')); } catch (e) { setInboxError(e instanceof Error ? e.message : 'Tente novamente.'); }
  }
  async function resend() {
    setBusy(true); setError('');
    try { const data = await api<{ resendAt: number }>('resend', {}); setResendAt(data.resendAt); setCode(''); setInbox(null); setNotice('Um novo código está na sua caixa de demonstração.'); }
    catch (e) { showError(e); } finally { setBusy(false); }
  }
  async function requestRecovery(e?: SyntheticEvent) {
    e?.preventDefault();
    setBusy(true); setError(''); setErrors({}); setNotice('');
    try {
      const res = await api<{ message: string; resendSeconds: number }>('recovery/request', { email: recoveryEmail, turnstileToken: token });
      setRecoveryStep(1);
      setResendAt(Date.now() / 1000 + (res.resendSeconds || 60));
      setNotice(res.message);
    } catch (err) {
      showError(err); setBotReset(v => v + 1);
    } finally { setBusy(false); }
  }
  async function openRecoveryInbox() {
    setModal('inbox'); setInbox(null); setInboxError('');
    try {
      const data = await api<{ code: string; to: string; expiresAt: number }>('recovery/demo-inbox', { email: recoveryEmail });
      setInbox({ ...data, subject: 'Seu código de recuperação de senha' });
    } catch (e) {
      setInboxError(e instanceof Error ? e.message : 'Tente novamente.');
    }
  }
  async function resetRecoveryPassword(e: SyntheticEvent) {
    e.preventDefault();
    setBusy(true); setError(''); setErrors({}); setNotice('');
    try {
      await api('recovery/reset', {
        email: recoveryEmail,
        code: recoveryCode,
        newPassword: recoveryPassword,
        confirmPassword: recoveryConfirm,
      });
      setRecoveryCode(''); setRecoveryPassword(''); setRecoveryConfirm(''); setRecoveryStep(0);
      setInbox(null); setView('login');
      setNotice('Senha redefinida com sucesso. Entre com sua nova senha.');
    } catch (err) {
      showError(err);
    } finally { setBusy(false); }
  }
  async function changePassword(e: SyntheticEvent) {
    e.preventDefault();
    setBusy(true); setPasswordError(''); setPasswordErrors({});
    try {
      await api('password', { currentPassword, newPassword, confirmPassword: confirmNewPassword });
      setModal(null); setCurrentPassword(''); setNewPassword(''); setConfirmNewPassword('');
      setNotice('Senha alterada com sucesso. Outras sessões foram encerradas.');
    } catch (err) {
      if (err instanceof ApiError) {
        setPasswordError(err.message);
        setPasswordErrors(err.fields || {});
      } else {
        setPasswordError('Não foi possível alterar a senha.');
      }
    } finally { setBusy(false); }
  }
  async function markLessonRead(item: Lesson) {
    try {
      const res = await api<{ dashboard: DashboardData }>('lessons/progress', { lessonId: item.id, progressPercent: 100 });
      setDashboard(res.dashboard);
      if (res.dashboard.lessons?.length) setLessons(res.dashboard.lessons);
      setLesson(prev => prev && prev.id === item.id ? { ...prev, progressPercent: 100 } : prev);
      setNotice(`Guia "${item.title}" marcado como concluído.`);
    } catch (e) {
      showError(e);
    }
  }
  const passwordRules = [values.password.length >= 8 && values.password.length <= 32, /[A-Z]/.test(values.password), /\d/.test(values.password)];
  const input = (key: keyof Values, options: Record<string, unknown> = {}) => ({ id: key, name: key, value: String(values[key]), onChange: (e: React.ChangeEvent<HTMLInputElement>) => update(key, e.target.value), 'aria-invalid': !!errors[key], 'aria-describedby': `${key}-help`, ...options });
  const seconds = Math.max(0, Math.ceil(resendAt - time));
  const editing = step === 3 && !!account?.completed;
  const titles = ['Seus dados', 'Crie seu acesso', 'Confirme seu e-mail', editing ? 'Ajustar perfil financeiro' : 'Seu perfil financeiro'];
  const descriptions = [
    'Usamos estes dados para identificar sua conta. CPF e e-mail não podem estar em outro cadastro.',
    'Você vai entrar com seu CPF ou e-mail e esta senha.',
    'Digite o código de 6 dígitos. Neste protótipo nenhum e-mail é enviado: o código fica na caixa de demonstração.',
    'Valores aproximados bastam. Eles são seu ponto de partida e podem ser ajustados depois.',
  ];
  const goalIcons = [Wallet, CreditCard, PiggyBank, TrendingUp];
  const switchView = (next: 'login' | 'register' | 'recovery') => {
    setView(next); setStep(0); setError(''); setErrors({}); setNotice('');
    if (next === 'recovery') {
      setRecoveryStep(0);
      setRecoveryCode('');
      setRecoveryPassword('');
      setRecoveryConfirm('');
      if (identifier.includes('@') && !recoveryEmail) setRecoveryEmail(identifier);
    }
  };
  const errorAlert = error && <div className="alert alert-error" role="alert"><CircleAlert size={18} /><span>{error}</span><button type="button" aria-label="Fechar aviso" onClick={() => setError('')}><X size={16} /></button></div>;
  const noticeAlert = notice && <div className="alert alert-success" role="status"><CheckCircle2 size={18} /><span>{notice}</span></div>;
  const isDashboard = view === 'dashboard' && !!account;

  return <MotionConfig reducedMotion="user"><div className={`app-shell ${isDashboard ? 'dash-shell' : ''}`}>
    {loadingSession ? (
      <main id="main" className="splash-screen" role="status" aria-live="polite" aria-label="Carregando ValorAI">
        <div className="splash-brand">
          <ProductMark />
          <span>Valor<strong>AI</strong></span>
        </div>
        <div className="splash-track" aria-hidden="true"><span className="splash-bar" /></div>
      </main>
    ) : isDashboard && account ? (
      <DashboardWorkspace
        account={account}
        dashboard={dashboard}
        profile={profile}
        lessons={lessons}
        activeTab={dashTab}
        onSelectTab={setDashTab}
        onEditFinanceProfile={() => { setStep(3); setView('register'); }}
        onOpenChangePassword={() => { setPasswordError(''); setPasswordErrors({}); setCurrentPassword(''); setNewPassword(''); setConfirmNewPassword(''); setModal('password'); }}
        onOpenDeactivate={() => { setDeactivateError(''); setModal('deactivate'); }}
        onOpenAbout={() => setModal('about')}
        onLogout={logout}
        sessionBusy={busy || loadingSession}
        onOpenLesson={(item) => setLesson(item)}
        onRefreshDashboard={(nextDashboard, nextAccount, nextProfile) => {
          setDashboard(nextDashboard);
          if (nextDashboard.lessons?.length) setLessons(nextDashboard.lessons);
          if (nextAccount) setAccount(nextAccount);
          if (nextProfile) setProfile(nextProfile);
        }}
        apiCall={api}
        headingRef={heading}
        errorAlert={errorAlert}
        noticeAlert={noticeAlert}
        setNotice={setNotice}
        setError={setError}
        aiEnabled={config?.aiEnabled ?? false}
        aiTier={config?.aiTier ?? 'free_prototype'}
      />
    ) : (
      <>
        <header className="site-header">
          <a className="brand" href="/" aria-label="ValorAI — início"><ProductMark /></a>
          <span className="tag">Protótipo</span>
          <div className="header-actions">
            <ThemeToggle />
            <button className="button button-ghost button-small header-about" onClick={() => setModal('about')}>Sobre o protótipo</button>
            {account ? <button className="button button-secondary button-small" onClick={logout} disabled={busy || loadingSession}>Sair<LogOut size={16} /></button>
              : view !== 'deactivated' && <button className="button button-secondary button-small" disabled={loadingSession} onClick={() => switchView(view === 'login' ? 'register' : 'login')}>{view === 'login' ? 'Criar conta' : 'Entrar'}</button>}
          </div>
        </header>
        <main id="main" className={view === 'deactivated' ? 'state-page' : 'auth'}>
          <AnimatePresence mode="wait" initial={false}><motion.div key={`${view}-${view === 'register' ? step : ''}`} className={view === 'login' || view === 'register' || view === 'recovery' ? 'auth-form' : undefined} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.18 }} onAnimationComplete={() => heading.current?.focus()}>
            {view === 'register' && <>
              {!editing && <div className="progress"><p className="progress-label" aria-hidden="true">Etapa {step + 1} de 4 · <strong>{stepNames[step]}</strong></p>
                <ol aria-label="Etapas do cadastro">{stepNames.map((label, i) => <li key={label} className={i < step ? 'complete' : i === step ? 'current' : ''} aria-current={i === step ? 'step' : undefined}><span>{label}<span className="sr-only">{i < step ? ' (concluída)' : ''}</span></span></li>)}</ol></div>}
              <div className="page-heading"><h1 tabIndex={-1} ref={heading}>{titles[step]}</h1><p>{descriptions[step]}</p></div>
              {errorAlert}{noticeAlert}
              <form onSubmit={submit} noValidate>
                <fieldset disabled={busy || loadingSession} className="form-fields"><legend className="sr-only">{stepNames[step]}</legend>
                {step === 0 && <div className="fields-grid">
                  <Field label="Nome completo" id="name" error={errors.name} wide><input {...input('name', { autoComplete: 'name', maxLength: 120 })} /></Field>
                  <Field label="CPF" id="cpf" error={errors.cpf}><input {...input('cpf', { inputMode: 'numeric', placeholder: '000.000.000-00', maxLength: 14, onChange: (e: React.ChangeEvent<HTMLInputElement>) => update('cpf', maskCpf(e.target.value)) })} /></Field>
                  <Field label="Data de nascimento" id="birthDate" error={errors.birthDate} hint="É preciso ter 16 anos ou mais."><input {...input('birthDate', { type: 'date', autoComplete: 'bday', min: '1900-01-01', max: new Date().toISOString().slice(0, 10) })} /></Field>
                  <Field label="Celular" id="phone" error={errors.phone}><input {...input('phone', { type: 'tel', autoComplete: 'tel-national', placeholder: '(82) 90000-0000', onChange: (e: React.ChangeEvent<HTMLInputElement>) => update('phone', maskPhone(e.target.value)) })} /></Field>
                  <Field label="CEP" id="postalCode" error={errors.postalCode}><input {...input('postalCode', { inputMode: 'numeric', autoComplete: 'postal-code', placeholder: '00000-000', onBlur: lookupPostal, onChange: (e: React.ChangeEvent<HTMLInputElement>) => update('postalCode', maskPostal(e.target.value)) })} /></Field>
                  {postalStatus && <p className="postal-status wide" role="status"><MapPin size={14} />{postalStatus}</p>}
                  <Field label="Estado" id="state" error={errors.state}><select id="state" value={values.state} onChange={e => { update('state', e.target.value); update('city', ''); }} aria-invalid={!!errors.state} aria-describedby="state-help"><option value="">Selecione</option>{states.map(s => <option key={s}>{s}</option>)}</select></Field>
                  <Field label="Cidade" id="city" error={errors.city}><input {...input('city', { list: 'city-options', autoComplete: 'address-level2', maxLength: 100 })} /><datalist id="city-options">{cities.map(c => <option key={c} value={c} />)}</datalist></Field>
                </div>}
                {step === 1 && <div className="fields-grid">
                  <Field label="Seu e-mail" id="email" error={errors.email} wide hint="Use um endereço fictício: este protótipo não envia e-mails."><input {...input('email', { type: 'email', autoComplete: 'email', placeholder: 'voce@exemplo.com', maxLength: 200 })} /></Field>
                  <Field label="Crie uma senha" id="password" error={errors.password} wide><div className="password-wrap"><input {...input('password', { type: showPassword ? 'text' : 'password', autoComplete: 'new-password', maxLength: 32 })} /><button type="button" className="icon-button" aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'} onClick={() => setShowPassword(v => !v)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></Field>
                  <ul className="password-rules wide" aria-label="Requisitos da senha">{['8 a 32 caracteres', 'Uma letra maiúscula', 'Um número'].map((text, i) => <li key={text} className={passwordRules[i] ? 'valid' : ''}><span aria-hidden="true">{passwordRules[i] && <Check size={11} strokeWidth={3} />}</span>{text}<i className="sr-only">{passwordRules[i] ? ': atendido' : ': pendente'}</i></li>)}</ul>
                  <Field label="Confirme a senha" id="confirmPassword" error={errors.confirmPassword} wide><input {...input('confirmPassword', { type: showPassword ? 'text' : 'password', autoComplete: 'new-password', maxLength: 32 })} /></Field>
                  <div className="wide"><label className="checkbox"><input id="demoConsent" type="checkbox" checked={values.demoConsent} onChange={e => update('demoConsent', e.target.checked)} aria-describedby="demoConsent-help" /><span>Entendo que este é um ambiente de demonstração e vou usar dados fictícios e uma senha exclusiva para teste.</span></label>{errors.demoConsent && <span className="field-error" id="demoConsent-help"><CircleAlert size={14} />{errors.demoConsent}</span>}</div>
                  {config?.siteKey && <div className="wide"><BotCheck siteKey={config.siteKey} onToken={setToken} reset={botReset} /></div>}
                </div>}
                {step === 2 && <div>
                  <div className="otp-field"><Field label={`Código enviado para ${account?.email ?? 'seu e-mail'}`} id="code" error={errors.code}><input id="code" className="otp-input" type="text" inputMode="numeric" autoComplete="one-time-code" maxLength={6} placeholder="······" value={code} onChange={e => { setCode(digits(e.target.value).slice(0, 6)); setErrors({}); }} aria-invalid={!!errors.code} aria-describedby="code-help" /></Field></div>
                  <div className="verify-meta"><span><Clock3 size={15} />Expira em 10 minutos</span>
                    <button type="button" className="link-button" onClick={resend} disabled={seconds > 0 || busy}><RotateCcw size={14} />{seconds ? `Reenviar em ${seconds}s` : 'Reenviar código'}</button></div>
                  {config?.emailMode === 'demo'
                    ? <button className="inbox-button" type="button" onClick={openInbox} aria-label="Abrir caixa de demonstração"><Mail size={20} /><span><strong>Abrir caixa de demonstração</strong><small>Mostra a mensagem simulada com o código</small></span><ArrowRight size={18} /></button>
                    : <div className="note"><Mail size={16} /><span>Enviamos um código de 6 dígitos para <strong>{account?.email || values.email}</strong>.</span></div>}
                </div>}
                {step === 3 && <>
                  <div className="fields-grid">
                    <Field label="Renda mensal estimada" id="income" error={errors.income}><div className="money-input"><span>R$</span><input id="income" inputMode="decimal" placeholder="0,00" value={income} onChange={e => { setIncome(e.target.value); setErrors(v => ({ ...v, income: '' })); }} aria-invalid={!!errors.income} aria-describedby="income-help" /></div></Field>
                    <Field label="Gastos fixos estimados" id="fixedExpenses" error={errors.fixedExpenses} hint="Aluguel, contas, mensalidades."><div className="money-input"><span>R$</span><input id="fixedExpenses" inputMode="decimal" placeholder="0,00" value={expenses} onChange={e => { setExpenses(e.target.value); setErrors(v => ({ ...v, fixedExpenses: '' })); }} aria-invalid={!!errors.fixedExpenses} aria-describedby="fixedExpenses-help" /></div></Field>
                  </div>
                  <fieldset className="goals"><legend>Qual é seu principal objetivo agora?</legend><div className="goal-options">{goals.map((g, i) => { const Icon = goalIcons[i]; return <label key={g.id} className={`goal-card ${goal === g.id ? 'selected' : ''}`}><input type="radio" name="goal" id={i === 0 ? 'goal' : undefined} value={g.id} checked={goal === g.id} onChange={() => { setGoal(g.id); setErrors(v => ({ ...v, goal: '' })); }} /><Icon size={20} aria-hidden="true" /><strong>{g.title}</strong><small>{g.description}</small></label>; })}</div>
                    {errors.goal && <span className="field-error goal-error"><CircleAlert size={14} />Escolha um objetivo para continuar.</span>}</fieldset>
                </>}
                </fieldset>
                <div className="form-actions">{(step === 1 || editing) && <button type="button" className="button button-ghost" disabled={busy} onClick={() => { if (account?.completed) setView('dashboard'); else setStep(0); setError(''); }}><ArrowLeft size={18} />Voltar</button>}
                  <button className="button button-primary" type="submit" disabled={busy || loadingSession || (step === 1 && !!config?.siteKey && !token) || (step === 1 && !config)}>{busy || loadingSession ? <><LoaderCircle className="spin" size={18} />{loadingSession ? 'Carregando…' : 'Um instante…'}</> : <>{step === 0 ? 'Continuar' : step === 1 ? 'Criar minha conta' : step === 2 ? 'Confirmar código' : editing ? 'Salvar alterações' : 'Concluir cadastro'}<ArrowRight size={18} /></>}</button></div>
              </form>
              {step === 2 && <div className="note"><Info size={16} /><span>A confirmação é simulada e não comprova que o e-mail pertence a você.</span></div>}
              {step === 3 && <div className="note"><Info size={16} /><span>Estas estimativas não criam lançamentos nem limites de gastos.</span></div>}
              {step === 0 && <p className="form-switch">Já tem conta? <button type="button" className="link-button" onClick={() => switchView('login')}>Entrar</button></p>}
            </>}
            {view === 'login' && <>
              <div className="page-heading"><h1 ref={heading} tabIndex={-1}>Entrar no ValorAI</h1><p>Acesse sua conta de demonstração com CPF ou e-mail.</p></div>
              {noticeAlert}{errorAlert}
              <form onSubmit={login}><div className="fields-grid">
                <Field label="CPF ou e-mail" id="identifier" wide><input id="identifier" autoComplete="username" required disabled={busy || loadingSession} value={identifier} onChange={e => setIdentifier(e.target.value)} /></Field>
                <Field label="Senha" id="loginPassword" wide><div className="password-wrap"><input id="loginPassword" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required disabled={busy || loadingSession} maxLength={32} value={loginPassword} onChange={e => setLoginPassword(e.target.value)} /><button type="button" className="icon-button" aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'} onClick={() => setShowPassword(v => !v)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div><div className="field-forgot"><button type="button" className="link-button" disabled={busy || loadingSession} onClick={() => switchView('recovery')}>Esqueci minha senha</button></div></Field></div>
                {config?.siteKey && <div className="login-bot"><BotCheck siteKey={config.siteKey} onToken={setToken} reset={botReset} /></div>}
                <div className="form-actions"><button className="button button-primary" disabled={busy || loadingSession || !config || (!!config.siteKey && !token)}>{busy || loadingSession ? <><LoaderCircle className="spin" size={18} />{loadingSession ? 'Carregando…' : 'Entrando…'}</> : <>Entrar na minha conta<ArrowRight size={18} /></>}</button></div>
              </form>
              <p className="form-switch">Primeira vez aqui? <button type="button" className="link-button" disabled={busy || loadingSession} onClick={() => switchView('register')}>Criar minha conta</button></p>
            </>}
            {view === 'recovery' && <>
              <div className="page-heading"><h1 ref={heading} tabIndex={-1}>Recuperar senha</h1><p>{recoveryStep === 0 ? 'Informe seu e-mail cadastrado para gerar um código de recuperação.' : 'Digite o código de 6 dígitos (validade de 15 min) e escolha sua nova senha.'}</p></div>
              {noticeAlert}{errorAlert}
              {recoveryStep === 0 ? (
                <form onSubmit={requestRecovery}><div className="fields-grid">
                  <Field label="E-mail cadastrado" id="recoveryEmail" error={errors.email} wide><input id="recoveryEmail" type="email" autoComplete="email" required disabled={busy} maxLength={200} value={recoveryEmail} onChange={e => setRecoveryEmail(e.target.value)} /></Field></div>
                  {config?.siteKey && <div className="login-bot"><BotCheck siteKey={config.siteKey} onToken={setToken} reset={botReset} /></div>}
                  <div className="form-actions"><button type="button" className="button button-ghost" disabled={busy} onClick={() => switchView('login')}><ArrowLeft size={18} />Voltar</button><button className="button button-primary" disabled={busy || !config || (!!config.siteKey && !token)}>{busy ? <><LoaderCircle className="spin" size={18} />Enviando…</> : <>Solicitar código<ArrowRight size={18} /></>}</button></div>
                </form>
              ) : (
                <form onSubmit={resetRecoveryPassword}><div className="fields-grid">
                  {config?.emailMode === 'demo' && <div className="field wide"><button type="button" className="button button-secondary button-block" onClick={openRecoveryInbox}><Mail size={18} />Abrir caixa de demonstração</button></div>}
                  <Field label="Código de 6 dígitos" id="recoveryCode" error={errors.code} wide><input id="recoveryCode" className="code-input" inputMode="numeric" autoComplete="one-time-code" maxLength={6} placeholder="000000" required disabled={busy} value={recoveryCode} onChange={e => setRecoveryCode(digits(e.target.value).slice(0, 6))} /></Field>
                  <Field label="Nova senha" id="recoveryPassword" error={errors.newPassword} wide><div className="password-wrap"><input id="recoveryPassword" type={showPassword ? 'text' : 'password'} autoComplete="new-password" required disabled={busy} maxLength={32} value={recoveryPassword} onChange={e => setRecoveryPassword(e.target.value)} /><button type="button" className="icon-button" aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'} onClick={() => setShowPassword(v => !v)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></Field>
                  <Field label="Confirme a nova senha" id="recoveryConfirm" error={errors.confirmPassword} wide><input id="recoveryConfirm" type={showPassword ? 'text' : 'password'} autoComplete="new-password" required disabled={busy} maxLength={32} value={recoveryConfirm} onChange={e => setRecoveryConfirm(e.target.value)} /></Field></div>
                  <div className="inline-actions"><button type="button" className="link-button" onClick={() => requestRecovery()} disabled={seconds > 0 || busy}><RotateCcw size={14} />{seconds ? `Reenviar em ${seconds}s` : 'Reenviar código'}</button></div>
                  <div className="form-actions"><button type="button" className="button button-ghost" disabled={busy} onClick={() => setRecoveryStep(0)}><ArrowLeft size={18} />Voltar</button><button className="button button-primary" disabled={busy}>{busy ? <><LoaderCircle className="spin" size={18} />Redefinindo…</> : <>Redefinir senha<ArrowRight size={18} /></>}</button></div>
                </form>
              )}
              <p className="form-switch"><button type="button" className="link-button" disabled={busy} onClick={() => switchView('login')}>Voltar para o login</button></p>
            </>}
            {view === 'deactivated' && <><div className="page-heading"><h1 ref={heading} tabIndex={-1}>Conta desativada</h1><p>Suas sessões foram encerradas. O cadastro e o perfil financeiro foram preservados (exclusão lógica).</p><p>Reativação e exclusão definitiva ainda não estão disponíveis.</p></div>
              <button className="button button-primary button-block" onClick={() => { setView('login'); setStep(0); setValues(initial); }}>Voltar ao início<ArrowRight size={18} /></button></>}
          </motion.div></AnimatePresence>
          {(view === 'login' || view === 'register' || view === 'recovery') && <ProductPreview />}
          <div className="sr-only" aria-live="polite">{view === 'register' ? `Etapa ${step + 1} de 4: ${stepNames[step]}` : ''}</div>
        </main>
        <footer className="site-footer"><div><span>Uma iniciativa</span><CompanyMark /></div><button className="link-button" onClick={() => setModal('about')}>Sobre o protótipo</button></footer>
      </>
    )}
    {modal === 'about' && <Modal title="Sobre este protótipo" onClose={() => setModal(null)}><div className="modal-body">
      <p>Este ambiente demonstra o cadastro (RF001), a confirmação simulada (RF002), a manutenção do perfil cadastral (RF003), o perfil financeiro (RF004), os 3 canais de lançamentos, importação, leitura de comprovantes por IA, limites e metas.</p>
      <div className="note"><Info size={16} /><span>Use dados fictícios e uma senha exclusiva para teste. Os dados ficam na Cloudflare. Não há envio de e-mail nem verificação real de titularidade.</span></div>
      <p>A confirmação usa, provisoriamente, 10 minutos de validade, cinco tentativas e até três envios por hora, com intervalo de 60 segundos. Esses parâmetros ainda dependem de validação nos requisitos.</p>
      <p>Os alertas de limites avisam você ao atingir ou superar o teto configurado sem bloquear nenhum lançamento. O protótipo não declara conformidade com a LGPD.</p>
      <button className="button button-primary button-block" onClick={() => setModal(null)}>Entendi</button></div></Modal>}
    {modal === 'inbox' && <Modal title="Caixa de demonstração" onClose={() => setModal(null)}><div className="modal-body">{inboxError ? <p role="alert">{inboxError}</p> : inbox ? <>
      <dl className="mail-meta"><dt>De</dt><dd>ValorAI (simulado)</dd><dt>Para</dt><dd>{inbox.to}</dd><dt>Assunto</dt><dd>{inbox.subject || 'Seu código de confirmação'}</dd></dl>
      <p>Use este código para continuar:</p><div className="inbox-code">{inbox.code}</div><p className="field-hint">Uso único. Nenhum e-mail foi enviado.</p>
      <button className="button button-primary button-block" onClick={() => { if (view === 'recovery') setRecoveryCode(inbox.code); else setCode(inbox.code); setModal(null); }}>Usar este código<ArrowRight size={18} /></button></> : <p role="status">Abrindo mensagem…</p>}</div></Modal>}
    {modal === 'password' && <Modal title="Alterar senha" onClose={() => setModal(null)}><form className="modal-body" onSubmit={changePassword}>
      {passwordError && <div className="alert alert-error" role="alert"><CircleAlert size={18} /><span>{passwordError}</span></div>}
      <p>Ao alterar sua senha, todas as outras sessões ativas serão encerradas.</p>
      <Field id="currentPassword" label="Senha atual" error={passwordErrors.currentPassword}><input id="currentPassword" type="password" autoComplete="current-password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} required maxLength={32} /></Field>
      <Field id="newPassword" label="Nova senha" error={passwordErrors.newPassword} hint="8 a 32 caracteres, 1 letra maiúscula e 1 número."><input id="newPassword" type="password" autoComplete="new-password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required maxLength={32} /></Field>
      <Field id="confirmNewPassword" label="Confirme a nova senha" error={passwordErrors.confirmPassword}><input id="confirmNewPassword" type="password" autoComplete="new-password" value={confirmNewPassword} onChange={e => setConfirmNewPassword(e.target.value)} required maxLength={32} /></Field>
      <button className="button button-primary button-block" disabled={busy}>{busy ? 'Salvando…' : 'Salvar nova senha'}</button>
    </form></Modal>}
    {modal === 'deactivate' && <Modal title="Desativar sua conta?" onClose={() => { setModal(null); setDeactivatePassword(''); }}><form className="modal-body" onSubmit={async e => { e.preventDefault(); setBusy(true); setDeactivateError(''); try { await api('deactivate', { password: deactivatePassword }); setModal(null); setAccount(null); setDashboard(null); setProfile(null); setView('deactivated'); setDeactivatePassword(''); } catch (e) { setDeactivateError(e instanceof Error ? e.message : 'Tente novamente.'); } finally { setBusy(false); } }}><p>O acesso será encerrado em todos os dispositivos. Seu cadastro e suas estimativas serão preservados; nada é apagado.</p><Field id="deactivatePassword" label="Confirme sua senha" error={deactivateError}><input id="deactivatePassword" type="password" autoComplete="current-password" value={deactivatePassword} onChange={e => setDeactivatePassword(e.target.value)} required maxLength={32} /></Field><button className="button button-danger button-block" disabled={busy}>{busy ? 'Desativando…' : 'Confirmar desativação'}</button></form></Modal>}
    {lesson && <Modal title={lesson.title} onClose={() => setLesson(null)} wide><div className="modal-body lesson-body">
      <div className="lesson-modal-meta">{lesson.category && <span className="guide-category-tag">{lesson.category}</span>}<span className="tag"><Clock3 size={13} />{lesson.minutes} min de leitura</span>{lesson.progressPercent === 100 && <span className="pill-badge pill-success"><Check size={12} />Leitura concluída</span>}</div>
      <MarkdownContent content={lesson.body} />
      <div className="modal-actions-row">
        {lesson.progressPercent !== 100 && <button type="button" className="button button-secondary" onClick={() => markLessonRead(lesson)}><Check size={16} />Marcar como concluído</button>}
        <button type="button" className="button button-primary" onClick={() => setLesson(null)}>Fechar guia</button>
      </div>
    </div></Modal>}
  </div></MotionConfig>;
}
