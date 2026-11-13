import { useState, useRef, useEffect, useId, type SyntheticEvent, type ReactNode } from 'react';
import NumberFlow from '@number-flow/react';
import {
  Plus, PenLine, Camera, FileUp, ShoppingCart, Home, Car, BookOpen,
  Utensils, HeartPulse, Zap, ArrowDownLeft, PiggyBank, Tags, TrendingUp, Clock3,
  BellRing, ArrowRight, Trash2, Sparkles,
  Search, CircleAlert, X, Target,
  LayoutGrid, ReceiptText, ScanLine, ChevronDown, UserRound,
  SlidersHorizontal, Info, LogOut, UserX, Check
} from 'lucide-react';
import { CompanyMark, ProductMark } from './BrandMark';
import { ThemeToggle } from './ThemeToggle';
import {
  goals, standardCategories, transactionKinds, paymentMethods, suggestCategory,
  states, maskPhone, maskPostal, profileUpdateSchema, fieldErrors, type Finance
} from '../../shared/validation';

export type DashboardTab = 'overview' | 'transactions' | 'planning' | 'guides';

export type DashboardTransaction = {
  id: string;
  title: string;
  amount: number;
  kind: 'income' | 'fixed_expense' | 'variable_expense';
  category: string;
  channel: 'manual' | 'import' | 'photo';
  occurredOn: string;
  status: 'paid' | 'pending';
  paymentMethod: 'pix' | 'credit' | 'debit' | 'cash' | 'boleto' | 'transfer';
  merchantDoc?: string | null;
  confidence?: number | null;
  validated: boolean;
  notes?: string | null;
  createdAt: number;
};

export type DashboardLimit = {
  id: string;
  scope: 'category' | 'daily' | 'card_share';
  category: string;
  limit: number;
  spent: number;
  percent: number;
  warnPercent: number;
  status: 'ok' | 'warning' | 'reached' | 'exceeded';
  advisory: string;
  lessonId: string;
  title?: string;
  actionLabel?: string;
};

export type DashboardLesson = {
  id: string;
  title: string;
  description: string;
  body: string;
  minutes: number;
  category?: string;
  progressPercent?: number;
};

export type AiSummaryData = {
  headline: string;
  summary: string;
  recommendations: string[];
  tone: 'ok' | 'warning' | 'alert';
  states: string[];
  source: 'ai' | 'fallback';
  cached?: boolean;
};

export type DashboardData = {
  cycle: { label: string; code: string; today: string };
  summary: {
    baseIncome: number;
    baseFixedExpenses: number;
    ledgerIncome: number;
    ledgerFixedExpenses: number;
    ledgerVariableExpenses: number;
    pendingBills: number;
    effectiveIncome: number;
    effectiveFixed: number;
    variableExpenses: number;
    freeBalance: number;
    totalExpenses: number;
    fixedShare: number;
    variableShare: number;
    reserveShare: number;
    dailyAverage: number;
    dailySeries: Array<{ label: string; amount: number }>;
    statusBadge: string;
    statusTone: 'balanced' | 'warning' | 'over';
    insight: { title: string; message: string; liquidityRecommended: number };
  };
  goal: {
    id: string;
    title: string;
    target: number;
    current: number;
    monthly: number;
    percent: number;
    monthsRemaining: number;
  };
  transactions: DashboardTransaction[];
  limits: DashboardLimit[];
  alerts: DashboardLimit[];
  categories: string[];
  categoryBreakdown: Array<{ category: string; spent: number }>;
  lessons: DashboardLesson[];
  aiSummary?: AiSummaryData;
  aiSummaryNeedsRefresh?: boolean;
};

export type ProfileData = {
  name: string;
  cpf: string;
  email: string;
  birthDate: string;
  phone: string;
  postalCode: string;
  state: string;
  city: string;
  avatar?: string | null;
  history: Array<{ id: number; changedFields: string[]; createdAt: number }>;
};

export type AccountSummary = {
  id: string;
  name: string;
  email: string;
  city: string;
  state: string;
  status: 'pending' | 'demo_confirmed' | 'inactive';
  completed: boolean;
  finance: Finance | null;
  avatar?: string | null;
};

type ImportPreviewItem = {
  title: string;
  amount: number;
  kind: 'income' | 'fixed_expense' | 'variable_expense';
  category: string;
  occurredOn: string;
  merchantDoc: string;
  paymentMethod: DashboardTransaction['paymentMethod'];
  externalRef: string;
  isDuplicate: boolean;
};

const SAMPLE_OFX = `OFXHEADER:100
<OFX>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <STMTRS>
        <BANKTRANLIST>
          <STMTTRN>
            <TRNTYPE>DEBIT
            <DTPOSTED>20261105081500
            <TRNAMT>-2400.00
            <FITID>OFX-202611-001
            <MEMO>Aluguel e Condominio Residencial
          </STMTTRN>
          <STMTTRN>
            <TRNTYPE>DEBIT
            <DTPOSTED>20261106143200
            <TRNAMT>-342.80
            <FITID>OFX-202611-002
            <MEMO>Pao de Acucar Supermercado
          </STMTTRN>
          <STMTTRN>
            <TRNTYPE>CREDIT
            <DTPOSTED>20261101110000
            <TRNAMT>1200.00
            <FITID>OFX-202611-003
            <MEMO>Consultoria e Servicos Recebidos
          </STMTTRN>
        </BANKTRANLIST>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>`;

const SAMPLE_CSV = `Data;Descrição;Valor;Categoria;Tipo
06/11/2026;Pão de Açúcar;-342,80;Alimentação;Variável
04/11/2026;Uber do Brasil;-42,90;Transporte;Variável
03/11/2026;Restaurante & Bistrô;-550,00;Lazer;Variável
02/11/2026;Livraria Cultura;-119,00;Educação;Variável
01/11/2026;Consultoria & Serviços;+1200,00;Renda;Receita`;

const currency = (v: number) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v);
const moneyFormat = { style: 'currency', currency: 'BRL' } as const;

function formatShortDate(iso: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso;
  const [, m, d] = iso.split('-');
  const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
  return `${d} ${months[Number(m) - 1] ?? m}`;
}

function categoryIcon(category: string, kind: string) {
  if (kind === 'income') return ArrowDownLeft;
  const lower = category.toLowerCase();
  if (lower.includes('alimenta') || lower.includes('mercado')) return ShoppingCart;
  if (lower.includes('moradia') || lower.includes('habita')) return Home;
  if (lower.includes('transporte')) return Car;
  if (lower.includes('educa')) return BookOpen;
  if (lower.includes('lazer') || lower.includes('restaurante')) return Utensils;
  if (lower.includes('saúde') || lower.includes('saude')) return HeartPulse;
  if (lower.includes('conta') || lower.includes('serviço')) return Zap;
  if (lower.includes('reserva') || lower.includes('invest')) return PiggyBank;
  return Tags;
}

function buildSparklinePaths(series: Array<{ label: string; amount: number }>) {
  const pts = series.length >= 2 ? series : [
    { label: 'Dia 01', amount: 60 },
    { label: 'Dia 10', amount: 90 },
    { label: 'Dia 20', amount: 75 },
    { label: 'Hoje', amount: 84 },
  ];
  const maxVal = Math.max(...pts.map((p) => p.amount), 10);
  const minVal = Math.min(...pts.map((p) => p.amount), 0);
  const span = Math.max(maxVal - minVal, 10);
  const coords = pts.map((pt, idx) => {
    const x = Math.round((idx / (pts.length - 1)) * 300);
    const y = Math.round(52 - ((pt.amount - minVal) / span) * 38);
    return { x, y, ...pt };
  });
  let line = `M ${coords[0].x},${coords[0].y}`;
  for (let i = 1; i < coords.length; i++) {
    const prev = coords[i - 1];
    const curr = coords[i];
    const midX = Math.round((prev.x + curr.x) / 2);
    line += ` C ${midX},${prev.y} ${midX},${curr.y} ${curr.x},${curr.y}`;
  }
  const area = `${line} L 300,64 L 0,64 Z`;
  const last = coords[coords.length - 1];
  return { line, area, last };
}

async function extractXlsxText(file: File): Promise<string> {
  try {
    const buffer = await file.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    const view = new DataView(buffer);
    const decoder = new TextDecoder('utf-8');
    const files: Record<string, string> = {};
    let offset = 0;
    while (offset + 30 <= bytes.length) {
      const sig = view.getUint32(offset, true);
      if (sig !== 0x04034b50) break;
      const compression = view.getUint16(offset + 8, true);
      const compSize = view.getUint32(offset + 18, true);
      const nameLen = view.getUint16(offset + 26, true);
      const extraLen = view.getUint16(offset + 28, true);
      const name = decoder.decode(bytes.subarray(offset + 30, offset + 30 + nameLen));
      const dataStart = offset + 30 + nameLen + extraLen;
      const compData = bytes.subarray(dataStart, dataStart + compSize);
      if (name === 'xl/sharedStrings.xml' || name.startsWith('xl/worksheets/sheet')) {
        if (compression === 0) {
          files[name] = decoder.decode(compData);
        } else if (compression === 8 && typeof DecompressionStream !== 'undefined') {
          const ds = new DecompressionStream('deflate-raw');
          const writer = ds.writable.getWriter();
          writer.write(compData);
          writer.close();
          const decompressed = await new Response(ds.readable).arrayBuffer();
          files[name] = decoder.decode(decompressed);
        }
      }
      offset = dataStart + compSize;
    }
    const sharedXml = files['xl/sharedStrings.xml'] || '';
    const sharedStrings = Array.from(sharedXml.matchAll(/<t[^>]*>(.*?)<\/t>/gs)).map((m) => m[1]);
    const sheetKey = Object.keys(files).find((k) => k.startsWith('xl/worksheets/sheet'));
    if (!sheetKey) return await file.text();
    const sheetXml = files[sheetKey];
    const rows: string[] = [];
    for (const rowMatch of sheetXml.matchAll(/<row[^>]*>(.*?)<\/row>/gs)) {
      const cells: string[] = [];
      for (const cellMatch of rowMatch[1].matchAll(/<c([^>]*)>(.*?)<\/c>/gs)) {
        const attrs = cellMatch[1];
        const inner = cellMatch[2];
        const isShared = /t="s"/.test(attrs);
        const inlineMatch = inner.match(/<t[^>]*>(.*?)<\/t>/s);
        const valMatch = inner.match(/<v[^>]*>(.*?)<\/v>/s);
        if (inlineMatch) cells.push(inlineMatch[1].trim());
        else if (valMatch) {
          const rawVal = valMatch[1].trim();
          cells.push(isShared ? (sharedStrings[Number(rawVal)] ?? rawVal) : rawVal);
        }
      }
      if (cells.length) rows.push(cells.join(';'));
    }
    return rows.join('\n');
  } catch {
    return await file.text();
  }
}

/** Center-crops an image file to a 256px square JPEG data URL (keeps avatars small and undistorted). */
async function squareAvatar(file: File, size = 256): Promise<string> {
  const bitmap = await createImageBitmap(file);
  try {
    const side = Math.min(bitmap.width, bitmap.height);
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('canvas');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, size, size);
    ctx.drawImage(bitmap, (bitmap.width - side) / 2, (bitmap.height - side) / 2, side, side, 0, 0, size, size);
    return canvas.toDataURL('image/jpeg', 0.88);
  } finally {
    bitmap.close();
  }
}

export function LightDismissModal({ title, children, onClose, wide = false }: { title: string; children: ReactNode; onClose: () => void; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  const backdropPointerDownRef = useRef(false);

  const isOutsideDialogBox = (dialog: HTMLDialogElement, clientX: number, clientY: number) => {
    if (clientX === 0 && clientY === 0) return false;
    const rect = dialog.getBoundingClientRect();
    return (
      clientY < rect.top ||
      clientY > rect.top + rect.height ||
      clientX < rect.left ||
      clientX > rect.left + rect.width
    );
  };

  return (
    <dialog
      ref={(node) => {
        ref.current = node;
        if (node && !node.open) {
          try { node.showModal(); } catch { /* already open */ }
        }
      }}
      className={wide ? 'modal modal-wide' : 'modal'}
      onCancel={(event) => {
        // Ignore bubbling `cancel` events dispatched by child controls
        // such as <input type="file">, <input type="date">, or <select>.
        if (event.target !== event.currentTarget) {
          event.stopPropagation();
          return;
        }
        event.preventDefault();
        onClose();
      }}
      onClose={(event) => {
        if (event.target !== event.currentTarget) return;
        onClose();
      }}
      onPointerDown={(event) => {
        const dialog = ref.current;
        backdropPointerDownRef.current = Boolean(
          dialog && event.target === dialog && isOutsideDialogBox(dialog, event.clientX, event.clientY),
        );
      }}
      onClick={(event) => {
        const dialog = ref.current;
        const startedOnBackdrop = backdropPointerDownRef.current;
        backdropPointerDownRef.current = false;
        if (!dialog || !startedOnBackdrop || event.target !== dialog || event.detail === 0) return;
        if (isOutsideDialogBox(dialog, event.clientX, event.clientY)) {
          onClose();
        }
      }}
      aria-labelledby="dialog-modal-title"
    >
      <div className="modal-header">
        <h2 id="dialog-modal-title">{title}</h2>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Fechar">
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

export function Dropdown({
  className,
  triggerClassName,
  triggerLabel,
  triggerContent,
  panelLabel,
  panelClassName,
  children,
}: {
  className?: string;
  triggerClassName: string;
  triggerLabel?: string;
  triggerContent: ReactNode;
  panelLabel: string;
  panelClassName?: string;
  children: (run: (action: () => void) => void) => ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const run = (action: () => void) => {
    setOpen(false);
    action();
  };

  return (
    <div ref={wrapRef} className={`dropdown-wrap ${className ?? ''}`}>
      <button
        ref={triggerRef}
        type="button"
        className={triggerClassName}
        aria-label={triggerLabel}
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((v) => !v)}
      >
        {triggerContent}
      </button>
      {open && (
        <div
          id={panelId}
          role="group"
          aria-label={panelLabel}
          className={`dropdown-panel ${panelClassName ?? ''}`}
        >
          {children(run)}
        </div>
      )}
    </div>
  );
}

async function compressReceiptImage(file: File): Promise<string> {
  const maxDimension = 1280;
  const maxChars = 480_000; // ~350 KB binary
  const objectUrl = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = () => reject(new Error('Não foi possível carregar a imagem selecionada.'));
      el.src = objectUrl;
    });
    const scale = Math.min(1, maxDimension / Math.max(img.width || 1, img.height || 1));
    const width = Math.max(1, Math.round(img.width * scale));
    const height = Math.max(1, Math.round(img.height * scale));
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas indisponível neste navegador.');
    ctx.drawImage(img, 0, 0, width, height);

    let dataUrl = canvas.toDataURL('image/jpeg', 0.78);
    if (dataUrl.length > maxChars) {
      dataUrl = canvas.toDataURL('image/jpeg', 0.62);
    }
    return dataUrl;
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

export default function DashboardWorkspace({
  account,
  dashboard,
  profile,
  lessons,
  activeTab,
  onSelectTab,
  onEditFinanceProfile,
  onOpenDeactivate,
  onOpenAbout,
  onLogout,
  sessionBusy,
  onOpenLesson,
  onRefreshDashboard,
  apiCall,
  headingRef,
  errorAlert,
  noticeAlert,
  setNotice,
  setError,
  aiEnabled = false,
  aiTier = 'free_prototype',
}: {
  account: AccountSummary;
  dashboard: DashboardData | null;
  profile: ProfileData | null;
  lessons: DashboardLesson[];
  activeTab: DashboardTab;
  onSelectTab: (tab: DashboardTab) => void;
  onEditFinanceProfile: () => void;
  onOpenDeactivate: () => void;
  onOpenAbout: () => void;
  onLogout: () => void;
  sessionBusy?: boolean;
  onOpenLesson: (lesson: DashboardLesson) => void;
  onRefreshDashboard: (nextDashboard: DashboardData, nextAccount?: AccountSummary, nextProfile?: ProfileData) => void;
  apiCall: <T>(path: string, body?: unknown) => Promise<T>;
  headingRef: React.RefObject<HTMLHeadingElement | null>;
  errorAlert: ReactNode;
  noticeAlert: ReactNode;
  setNotice: (msg: string) => void;
  setError: (msg: string) => void;
  aiEnabled?: boolean;
  aiTier?: 'free_prototype' | 'paid';
}) {
  const [ledgerFilter, setLedgerFilter] = useState<'all' | 'fixed' | 'variable' | 'income'>('all');
  const [channelFilter, setChannelFilter] = useState<'all' | 'manual' | 'import' | 'photo'>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeModal, setActiveModal] = useState<
    null | 'manual' | 'receipt' | 'import' | 'limit' | 'goal' | 'profile'
  >(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [modalError, setModalError] = useState('');
  const [fieldErrs, setFieldErrs] = useState<Record<string, string>>({});
  const [guideSearch, setGuideSearch] = useState('');
  const [guideCategory, setGuideCategory] = useState('all');

  // Manual Transaction Form State
  const [editingTxId, setEditingTxId] = useState<string | null>(null);
  const [txTitle, setTxTitle] = useState('');
  const [txAmount, setTxAmount] = useState('');
  const [txKind, setTxKind] = useState<'income' | 'fixed_expense' | 'variable_expense'>('variable_expense');
  const [txCategory, setTxCategory] = useState('Alimentação');
  const [txAutoCategory, setTxAutoCategory] = useState(true);
  const [txDate, setTxDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [txStatus, setTxStatus] = useState<'paid' | 'pending'>('paid');
  const [txMethod, setTxMethod] = useState<'pix' | 'credit' | 'debit' | 'cash' | 'boleto' | 'transfer'>('debit');
  const [txDoc, setTxDoc] = useState('');
  const [txNotes, setTxNotes] = useState('');

  // Receipt AI / OCR State
  const [receiptFileName, setReceiptFileName] = useState('');
  const [receiptHint, setReceiptHint] = useState('');
  const [extractedReceipt, setExtractedReceipt] = useState<{
    title: string;
    amount: number;
    kind: 'income' | 'fixed_expense' | 'variable_expense';
    category: string;
    occurredOn: string;
    paymentMethod: 'pix' | 'credit' | 'debit' | 'cash' | 'boleto' | 'transfer';
    merchantDoc: string;
    confidence: number;
    source?: 'ai' | 'fallback';
    fallbackReason?: string;
  } | null>(null);
  const [receiptConfirmedCheck, setReceiptConfirmedCheck] = useState(true);

  // Home AI Summary State
  const [aiSummaryOverride, setAiSummaryOverride] = useState<AiSummaryData | null>(null);
  const [aiSummaryBusy, setAiSummaryBusy] = useState(false);

  const activeAiSummary = aiSummaryOverride ?? dashboard?.aiSummary ?? null;

  useEffect(() => {
    setAiSummaryOverride(null);
  }, [dashboard?.aiSummary]);

  useEffect(() => {
    if (!aiEnabled || !dashboard?.aiSummaryNeedsRefresh || aiSummaryBusy) return;
    let cancelled = false;
    setAiSummaryBusy(true);
    apiCall<{ aiSummary: AiSummaryData }>('ai/summary', { force: false })
      .then((res) => {
        if (!cancelled && res.aiSummary) setAiSummaryOverride(res.aiSummary);
      })
      .catch(() => {
        // Keep deterministic fallback already rendered in dashboard.aiSummary
      })
      .finally(() => {
        if (!cancelled) setAiSummaryBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [aiEnabled, dashboard?.aiSummaryNeedsRefresh]);

  // Import OFX / CSV / Excel State
  const [importFileName, setImportFileName] = useState('');
  const [importFormat, setImportFormat] = useState<'auto' | 'ofx' | 'csv'>('auto');
  const [importContent, setImportContent] = useState('');
  const [importPreviewItems, setImportPreviewItems] = useState<ImportPreviewItem[] | null>(null);

  // Budget Limit State
  const [limitScope, setLimitScope] = useState<'category' | 'daily' | 'card_share'>('category');
  const [limitCategory, setLimitCategory] = useState('Lazer');
  const [limitValue, setLimitValue] = useState('600');
  const [limitWarn, setLimitWarn] = useState('80');

  // Goal Progress State
  const [goalTarget, setGoalTarget] = useState('5000');
  const [goalCurrent, setGoalCurrent] = useState('2000');
  const [goalMonthly, setGoalMonthly] = useState('750');
  const [goalContribution, setGoalContribution] = useState('');

  // RF003 Personal Profile State
  const [profName, setProfName] = useState(profile?.name ?? account.name);
  const [profBirth, setProfBirth] = useState(profile?.birthDate ?? '1995-06-15');
  const [profPhone, setProfPhone] = useState(profile?.phone ?? '');
  const [profPostal, setProfPostal] = useState(profile?.postalCode ?? '');
  const [profState, setProfState] = useState(profile?.state ?? account.state);
  const [profCity, setProfCity] = useState(profile?.city ?? account.city);
  const [profAvatar, setProfAvatar] = useState<string | null | undefined>(profile?.avatar ?? account.avatar);

  const baseIncome = account.finance?.income ?? 0;
  const baseFixed = account.finance?.fixedExpenses ?? 0;
  const effectiveIncome = dashboard?.summary.effectiveIncome ?? baseIncome;
  const effectiveFixed = dashboard?.summary.effectiveFixed ?? baseFixed;
  const freeBalance = dashboard?.summary.freeBalance ?? (baseIncome - baseFixed);
  const fixedShare = dashboard?.summary.fixedShare ?? (baseIncome > 0 ? Math.min(100, Math.round((baseFixed / baseIncome) * 100)) : baseFixed > 0 ? 100 : 0);
  const variableShare = dashboard?.summary.variableShare ?? 0;
  const reserveShare = dashboard?.summary.reserveShare ?? Math.max(0, 100 - fixedShare - variableShare);
  const dailyAverage = dashboard?.summary.dailyAverage ?? Math.round(effectiveFixed / 30);
  const dailySeries = dashboard?.summary.dailySeries ?? [];
  const sparkline = buildSparklinePaths(dailySeries);

  const transactions = dashboard?.transactions ?? [];
  const filteredTransactions = transactions.filter((tx) => {
    if (ledgerFilter === 'fixed' && tx.kind !== 'fixed_expense') return false;
    if (ledgerFilter === 'variable' && tx.kind !== 'variable_expense') return false;
    if (ledgerFilter === 'income' && tx.kind !== 'income') return false;
    if (channelFilter !== 'all' && tx.channel !== channelFilter) return false;
    if (categoryFilter !== 'all' && tx.category !== categoryFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      if (!tx.title.toLowerCase().includes(q) && !tx.category.toLowerCase().includes(q) && !(tx.merchantDoc ?? '').toLowerCase().includes(q)) {
        return false;
      }
    }
    return true;
  });

  const allLessons: DashboardLesson[] = (dashboard?.lessons?.length ? dashboard.lessons : lessons).map((item) => ({
    ...item,
    progressPercent: item.progressPercent ?? 0,
  }));

  const activeGoal = dashboard?.goal ?? {
    id: account.finance?.goal ?? 'reserve',
    title: goals.find((g) => g.id === account.finance?.goal)?.title ?? 'Reserva Financeira',
    target: 5000,
    current: 0,
    monthly: 750,
    percent: 0,
    monthsRemaining: 7,
  };

  const limits = dashboard?.limits ?? [];
  const alerts = dashboard?.alerts ?? [];
  const primaryLimit: DashboardLimit | null = alerts[0] ?? limits[0] ?? null;

  function openManualModal(tx?: DashboardTransaction) {
    setModalError('');
    setFieldErrs({});
    if (tx) {
      setEditingTxId(tx.id);
      setTxTitle(tx.title);
      setTxAmount(String(tx.amount));
      setTxKind(tx.kind);
      setTxCategory(tx.category);
      setTxAutoCategory(false);
      setTxDate(tx.occurredOn);
      setTxStatus(tx.status);
      setTxMethod(tx.paymentMethod);
      setTxDoc(tx.merchantDoc ?? '');
      setTxNotes(tx.notes ?? '');
    } else {
      setEditingTxId(null);
      setTxTitle('');
      setTxAmount('');
      setTxKind('variable_expense');
      setTxCategory('Alimentação');
      setTxAutoCategory(true);
      setTxDate(dashboard?.cycle.today ?? new Date().toISOString().slice(0, 10));
      setTxStatus('paid');
      setTxMethod('debit');
      setTxDoc('');
      setTxNotes('');
    }
    setActiveModal('manual');
  }

  function openReceiptModal() {
    setModalError('');
    setFieldErrs({});
    setReceiptFileName('');
    setReceiptHint('');
    setExtractedReceipt(null);
    setReceiptConfirmedCheck(true);
    setActiveModal('receipt');
  }

  function openImportModal() {
    setModalError('');
    setFieldErrs({});
    setImportFileName('');
    setImportFormat('auto');
    setImportContent('');
    setImportPreviewItems(null);
    setActiveModal('import');
  }

  function openLimitModal(lim?: DashboardLimit) {
    setModalError('');
    setFieldErrs({});
    if (lim) {
      setLimitScope(lim.scope);
      setLimitCategory(lim.category);
      setLimitValue(String(lim.limit));
      setLimitWarn(String(lim.warnPercent));
    } else {
      setLimitScope('category');
      setLimitCategory('Lazer');
      setLimitValue('600');
      setLimitWarn('80');
    }
    setActiveModal('limit');
  }

  function openGoalModal() {
    setModalError('');
    setFieldErrs({});
    setGoalTarget(String(activeGoal.target));
    setGoalCurrent(String(activeGoal.current));
    setGoalMonthly(String(activeGoal.monthly));
    setGoalContribution('');
    setActiveModal('goal');
  }

  function openProfileModal() {
    setModalError('');
    setFieldErrs({});
    setProfName(profile?.name ?? account.name);
    setProfBirth(profile?.birthDate ?? '1995-06-15');
    setProfPhone(profile?.phone ?? '');
    setProfPostal(profile?.postalCode ?? '');
    setProfState(profile?.state ?? account.state);
    setProfCity(profile?.city ?? account.city);
    setProfAvatar(profile?.avatar ?? account.avatar ?? null);
    setActiveModal('profile');
  }

  async function handleSaveManual(e: SyntheticEvent) {
    e.preventDefault();
    setModalError('');
    setFieldErrs({});
    const numericAmount = Number(txAmount.replace(',', '.'));
    if (!txTitle.trim() || txTitle.trim().length < 2) {
      setFieldErrs({ title: 'Informe uma descrição entre 2 e 120 caracteres.' });
      return;
    }
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
      setFieldErrs({ amount: 'Informe um valor maior que zero.' });
      return;
    }
    setActionBusy(true);
    try {
      const res = await apiCall<{ dashboard: DashboardData }>('transactions', {
        action: editingTxId ? 'update' : 'create',
        id: editingTxId ?? undefined,
        title: txTitle.trim(),
        amount: numericAmount,
        kind: txKind,
        category: txCategory.trim() || 'Outros',
        occurredOn: txDate,
        status: txStatus,
        paymentMethod: txMethod,
        merchantDoc: txDoc.trim() || undefined,
        notes: txNotes.trim() || undefined,
      });
      onRefreshDashboard(res.dashboard);
      setActiveModal(null);
      setNotice(editingTxId ? 'Lançamento atualizado com sucesso.' : 'Lançamento registrado no livro caixa.');
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Não foi possível salvar o lançamento.');
    } finally {
      setActionBusy(false);
    }
  }

  async function handleDeleteTransaction(id: string) {
    setActionBusy(true);
    setError('');
    try {
      const res = await apiCall<{ dashboard: DashboardData }>('transactions', { action: 'delete', id });
      onRefreshDashboard(res.dashboard);
      setNotice('Lançamento removido.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível excluir.');
    } finally {
      setActionBusy(false);
    }
  }

  async function handleToggleStatus(id: string) {
    setActionBusy(true);
    try {
      const res = await apiCall<{ dashboard: DashboardData }>('transactions', { action: 'toggle_status', id });
      onRefreshDashboard(res.dashboard);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível alterar o status.');
    } finally {
      setActionBusy(false);
    }
  }

  async function handleSeedDemo() {
    setActionBusy(true);
    setError('');
    try {
      const res = await apiCall<{ dashboard: DashboardData }>('transactions', { action: 'seed_demo' });
      onRefreshDashboard(res.dashboard);
      setNotice('Movimentações e limites de demonstração carregados no ciclo atual.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível carregar os exemplos.');
    } finally {
      setActionBusy(false);
    }
  }

  async function handleRefreshAiSummary() {
    setAiSummaryBusy(true);
    try {
      const res = await apiCall<{ aiSummary: AiSummaryData }>('ai/summary', { force: true });
      if (res.aiSummary) setAiSummaryOverride(res.aiSummary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível atualizar a análise agora.');
    } finally {
      setAiSummaryBusy(false);
    }
  }

  async function handleExtractReceipt(preset?: string, customFileName?: string, customHint?: string, customImageData?: string) {
    setModalError('');
    setActionBusy(true);
    try {
      const res = await apiCall<{ extracted: NonNullable<typeof extractedReceipt> }>('transactions/receipt', {
        fileName: customFileName ?? (receiptFileName || 'comprovante-nfce.jpg'),
        textHint: customHint ?? receiptHint,
        imageData: customImageData,
        preset,
        confirm: false,
      });
      setExtractedReceipt(res.extracted);
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Não foi possível ler o comprovante.');
    } finally {
      setActionBusy(false);
    }
  }

  async function handleConfirmReceipt(e: SyntheticEvent) {
    e.preventDefault();
    if (!extractedReceipt) return;
    setModalError('');
    setActionBusy(true);
    try {
      const res = await apiCall<{ dashboard: DashboardData }>('transactions/receipt', {
        confirm: true,
        transaction: {
          ...extractedReceipt,
          validated: receiptConfirmedCheck,
        },
      });
      onRefreshDashboard(res.dashboard);
      setActiveModal(null);
      setNotice('Comprovante extraído via IA e lançado com categoria validada.');
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Não foi possível confirmar o comprovante.');
    } finally {
      setActionBusy(false);
    }
  }

  async function handlePreviewImport(customContent?: string, customFormat?: 'auto' | 'ofx' | 'csv', customName?: string) {
    const contentToUse = customContent ?? importContent;
    if (!contentToUse.trim()) {
      setModalError('Selecione um arquivo ou carregue um modelo de exemplo.');
      return;
    }
    setModalError('');
    setActionBusy(true);
    try {
      const res = await apiCall<{ preview: boolean; items: ImportPreviewItem[] }>('transactions/import', {
        format: customFormat ?? importFormat,
        fileName: customName ?? (importFileName || 'extrato.ofx'),
        content: contentToUse,
        preview: true,
      });
      setImportPreviewItems(res.items);
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Não foi possível analisar o arquivo.');
    } finally {
      setActionBusy(false);
    }
  }

  async function handleConfirmImport() {
    if (!importPreviewItems || !importPreviewItems.length) return;
    setModalError('');
    setActionBusy(true);
    try {
      const res = await apiCall<{
        dashboard: DashboardData;
        importResult: { importedCount: number; duplicateCount: number };
      }>('transactions/import', {
        preview: false,
        items: importPreviewItems,
      });
      onRefreshDashboard(res.dashboard);
      setActiveModal(null);
      setNotice(
        `Importação concluída: ${res.importResult.importedCount} lançamento(s) importado(s)` +
          (res.importResult.duplicateCount ? ` (${res.importResult.duplicateCount} duplicado(s) ignorado(s)).` : '.')
      );
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Não foi possível importar os lançamentos.');
    } finally {
      setActionBusy(false);
    }
  }

  async function handleSaveLimit(e: SyntheticEvent) {
    e.preventDefault();
    setModalError('');
    const numLimit = Number(limitValue.replace(',', '.'));
    if (!Number.isFinite(numLimit) || numLimit <= 0) {
      setModalError('Informe um valor maior que zero para o teto.');
      return;
    }
    setActionBusy(true);
    try {
      const res = await apiCall<{ dashboard: DashboardData }>('limits', {
        action: 'upsert',
        scope: limitScope,
        category: limitScope === 'daily' ? 'Teto Diário' : limitScope === 'card_share' ? 'Supérfluos no Cartão' : limitCategory,
        limit: numLimit,
        warnPercent: Number(limitWarn) || 80,
      });
      onRefreshDashboard(res.dashboard);
      setActiveModal(null);
      setNotice('Limite orçamentário salvo. Alertas informativos atualizados.');
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Não foi possível salvar o limite.');
    } finally {
      setActionBusy(false);
    }
  }

  async function handleDeleteLimit(id: string) {
    setActionBusy(true);
    try {
      const res = await apiCall<{ dashboard: DashboardData }>('limits', { action: 'delete', id });
      onRefreshDashboard(res.dashboard);
      setNotice('Limite removido.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível remover o limite.');
    } finally {
      setActionBusy(false);
    }
  }

  async function handleSaveGoal(e: SyntheticEvent) {
    e.preventDefault();
    setModalError('');
    const targetNum = Number(goalTarget.replace(',', '.'));
    const currentNum = Number(goalCurrent.replace(',', '.'));
    const monthlyNum = Number(goalMonthly.replace(',', '.'));
    const contribNum = goalContribution.trim() ? Number(goalContribution.replace(',', '.')) : 0;
    if (!Number.isFinite(targetNum) || targetNum <= 0) {
      setModalError('Informe uma meta total maior que zero.');
      return;
    }
    setActionBusy(true);
    try {
      const res = await apiCall<{ account: AccountSummary; dashboard: DashboardData }>('goal', {
        target: targetNum,
        current: Number.isFinite(currentNum) && currentNum >= 0 ? currentNum : 0,
        monthly: Number.isFinite(monthlyNum) && monthlyNum >= 0 ? monthlyNum : 0,
        contribution: Number.isFinite(contribNum) && contribNum > 0 ? contribNum : 0,
        recordTransaction: contribNum > 0,
      });
      onRefreshDashboard(res.dashboard, res.account);
      setActiveModal(null);
      setNotice(contribNum > 0 ? `Aporte de ${currency(contribNum)} registrado na sua meta.` : 'Parâmetros da meta prioritária atualizados.');
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Não foi possível atualizar a meta.');
    } finally {
      setActionBusy(false);
    }
  }

  async function handleSaveProfile(e: SyntheticEvent) {
    e.preventDefault();
    setModalError('');
    setFieldErrs({});
    const parsed = profileUpdateSchema.safeParse({
      name: profName,
      birthDate: profBirth,
      phone: profPhone,
      postalCode: profPostal,
      state: profState,
      city: profCity,
    });
    if (!parsed.success) {
      setFieldErrs(fieldErrors(parsed.error));
      return;
    }
    setActionBusy(true);
    try {
      const res = await apiCall<{ account: AccountSummary; profile: ProfileData }>('profile', {
        name: profName.trim(),
        birthDate: profBirth,
        phone: profPhone,
        postalCode: profPostal,
        state: profState,
        city: profCity.trim(),
        avatar: profAvatar ?? '',
      });
      if (dashboard) {
        onRefreshDashboard(dashboard, res.account, res.profile);
      }
      setActiveModal(null);
      setNotice('Dados cadastrais atualizados e registrados no histórico.');
    } catch (err) {
      setModalError(err instanceof Error ? err.message : 'Não foi possível atualizar o perfil.');
    } finally {
      setActionBusy(false);
    }
  }

  async function handleMarkLessonProgress(lessonId: string, progressPercent: number) {
    setActionBusy(true);
    try {
      const res = await apiCall<{ dashboard: DashboardData }>('lessons/progress', { lessonId, progressPercent });
      onRefreshDashboard(res.dashboard);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível salvar o progresso da leitura.');
    } finally {
      setActionBusy(false);
    }
  }

  const firstName = account.name.split(' ')[0] || 'Cliente';
  const displayName = account.name.split(' ').filter(Boolean).slice(0, 2).join(' ') || 'Cliente';
  const initials = account.name.split(' ').filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'VA';
  const avatarSrc = profile?.avatar || account.avatar || null;
  const cycleLabel = dashboard?.cycle.label ?? 'Novembro de 2026';
  const cycleCode = dashboard?.cycle.code ?? '2026.11';
  const goalTitle = goals.find((g) => g.id === account.finance?.goal)?.title;
  const recentTransactions = filteredTransactions.slice(0, 5);
  const tabMeta: Record<DashboardTab, { title: string; subtitle: string }> = {
    overview: {
      title: 'Visão Geral',
      subtitle: transactions.length
        ? `${transactions.length} ${transactions.length === 1 ? 'movimentação registrada' : 'movimentações registradas'}`
        : 'Nenhuma movimentação registrada',
    },
    transactions: { title: 'Transações & Extratos', subtitle: 'Receitas, gastos fixos e despesas do ciclo' },
    planning: { title: 'Planejamento', subtitle: 'Limites de gastos e meta prioritária' },
    guides: { title: 'Guias', subtitle: 'Leituras curtas de educação financeira' },
  };
  const navItems: Array<{ id: DashboardTab; label: string; short: string; Icon: typeof LayoutGrid }> = [
    { id: 'overview', label: 'Visão Geral', short: 'Visão Geral', Icon: LayoutGrid },
    { id: 'transactions', label: 'Transações & Extratos', short: 'Transações', Icon: ReceiptText },
    { id: 'planning', label: 'Planejamento', short: 'Metas', Icon: Target },
    { id: 'guides', label: 'Guias', short: 'Guias', Icon: BookOpen },
  ];

  // Move focus to the page heading when the client changes section, like a page navigation.
  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      headingRef.current?.focus({ preventScroll: true });
      return;
    }
    window.scrollTo({ top: 0 });
    headingRef.current?.focus({ preventScroll: true });
  }, [activeTab, headingRef]);

  const entryOptions = (run: (action: () => void) => void) => (
    <>
      <button type="button" className="dropdown-item" onClick={() => run(() => openManualModal())}>
        <PenLine size={18} aria-hidden="true" />
        <span>Digitação manual</span>
      </button>
      <button type="button" className="dropdown-item" onClick={() => run(openReceiptModal)}>
        <ScanLine size={18} aria-hidden="true" />
        <span>Ler comprovante (OCR)</span>
      </button>
      <button type="button" className="dropdown-item" onClick={() => run(openImportModal)}>
        <FileUp size={18} aria-hidden="true" />
        <span>Importar OFX / CSV</span>
      </button>
    </>
  );

  const avatar = (size: 'sm' | 'lg') => (
    <span className={`user-avatar ${size === 'lg' ? 'user-avatar-lg' : ''}`} aria-hidden="true">
      {avatarSrc ? <img src={avatarSrc} alt="" /> : initials}
    </span>
  );

  return (
    <>
      {/* ===================== HEADER (Stitch: brand, sections, Novo Lançamento, profile) ===================== */}
      <header className="dash-header">
        <div className="dash-header-left">
          <a className="brand" href="/" aria-label="ValorAI — início">
            <ProductMark />
          </a>
          <nav className="header-nav" aria-label="Seções do painel">
            {navItems.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                className={`header-nav-link ${activeTab === id ? 'active' : ''}`}
                aria-current={activeTab === id ? 'page' : undefined}
                onClick={() => onSelectTab(id)}
              >
                {label}
                {id === 'planning' && alerts.length > 0 && (
                  <span className="tab-alert-dot" role="img" aria-label={`${alerts.length} alerta(s) de limite`} />
                )}
              </button>
            ))}
          </nav>
        </div>

        <div className="dash-header-right">
          <Dropdown
            className="new-entry-header"
            triggerClassName="button button-primary button-small new-entry-trigger"
            triggerContent={
              <>
                <Plus size={18} aria-hidden="true" />
                <span>Novo Lançamento</span>
                <ChevronDown size={16} aria-hidden="true" className="dropdown-chevron" />
              </>
            }
            panelLabel="Canais de lançamento"
          >
            {entryOptions}
          </Dropdown>
          <span className="header-divider" aria-hidden="true" />
          <ThemeToggle />
          <Dropdown
            triggerClassName="profile-trigger"
            triggerLabel={`Painel do perfil de ${displayName}`}
            triggerContent={
              <>
                {avatar('sm')}
                <span className="profile-trigger-name">{displayName}</span>
              </>
            }
            panelLabel="Painel do perfil"
            panelClassName="profile-panel"
          >
            {(run) => (
              <>
                <div className="profile-panel-head">
                  {avatar('lg')}
                  <div>
                    <strong>{account.name}</strong>
                    <small>{account.email}</small>
                  </div>
                </div>
                <dl className="profile-facts">
                  <div>
                    <dt>Cidade</dt>
                    <dd>{account.city} · {account.state}</dd>
                  </div>
                  {goalTitle && (
                    <div>
                      <dt>Objetivo</dt>
                      <dd>{goalTitle}</dd>
                    </div>
                  )}
                  <div>
                    <dt>Confirmação</dt>
                    <dd>Demonstração</dd>
                  </div>
                </dl>
                <div className="dropdown-group">
                  <button type="button" className="dropdown-item" onClick={() => run(openProfileModal)}>
                    <UserRound size={18} aria-hidden="true" />
                    <span>Editar cadastro</span>
                  </button>
                  <button type="button" className="dropdown-item" onClick={() => run(onEditFinanceProfile)}>
                    <SlidersHorizontal size={18} aria-hidden="true" />
                    <span>Ajustar perfil financeiro</span>
                  </button>
                  <button type="button" className="dropdown-item" onClick={() => run(onOpenAbout)}>
                    <Info size={18} aria-hidden="true" />
                    <span>Sobre o protótipo</span>
                  </button>
                  <hr className="dropdown-sep" />
                  <button type="button" className="dropdown-item" disabled={sessionBusy} onClick={() => run(onLogout)}>
                    <LogOut size={18} aria-hidden="true" />
                    <span>Sair</span>
                  </button>
                  <button type="button" className="dropdown-item danger" onClick={() => run(onOpenDeactivate)}>
                    <UserX size={18} aria-hidden="true" />
                    <span>Desativar minha conta</span>
                  </button>
                </div>
              </>
            )}
          </Dropdown>
        </div>
      </header>

      <main id="main" className="dashboard stitch-dashboard">
        {/* Compact page heading & cycle status */}
        <div className="dash-page-head">
          <div>
            <h1 ref={headingRef} tabIndex={-1}>{tabMeta[activeTab].title}</h1>
            <p>
              Ciclo atual: <strong>{cycleLabel}</strong> • {tabMeta[activeTab].subtitle}
            </p>
          </div>
          <Dropdown
            className="page-head-entry"
            triggerClassName="button button-primary new-entry-trigger"
            triggerContent={
              <>
                <Plus size={18} aria-hidden="true" />
                <span>Lançamento</span>
              </>
            }
            panelLabel="Canais de lançamento"
          >
            {entryOptions}
          </Dropdown>
        </div>

        {errorAlert}
        {noticeAlert}

        {/* ===================== TAB 1: VISÃO GERAL ===================== */}
        {activeTab === 'overview' && (
          <div className="dash-grid overview-grid">
            <div className="dash-col">
              {/* 1. Saldo livre planejável & resumo financeiro */}
              <section className="card hero-card" aria-labelledby="profile-title">
                <div className="hero-top">
                  <div>
                    <div className="hero-label-row">
                      <h2 id="profile-title" className="eyebrow-label">
                        Saldo Livre Planejável
                      </h2>
                      <span className={`status-pill ${dashboard?.summary.statusTone ?? (freeBalance < 0 ? 'over' : 'balanced')}`}>
                        <i className="status-dot" aria-hidden="true" />
                        {dashboard?.summary.statusBadge ?? (freeBalance < 0 ? 'Acima do planejado' : 'Equilibrado')}
                      </span>
                    </div>
                    <div className={`hero-balance-value ${freeBalance < 0 ? 'negative' : ''}`}>
                      <span className="sr-only">{currency(freeBalance)}</span>
                      <NumberFlow aria-hidden="true" value={freeBalance} locales="pt-BR" format={moneyFormat} />
                    </div>
                  </div>
                </div>

                <div className="metrics-split">
                  <div className="metric-cell">
                    <span className="metric-label">Renda Mensal</span>
                    <strong className="metric-value">
                      <span className="sr-only">{currency(effectiveIncome)}</span>
                      <NumberFlow aria-hidden="true" value={effectiveIncome} locales="pt-BR" format={moneyFormat} />
                    </strong>
                    <small className="metric-sub">Recebimentos fixos e extras</small>
                  </div>
                  <div className="metric-cell">
                    <span className="metric-label">Gastos Fixos</span>
                    <strong className="metric-value">
                      <span className="sr-only">{currency(effectiveFixed)}</span>
                      <NumberFlow aria-hidden="true" value={effectiveFixed} locales="pt-BR" format={moneyFormat} />
                    </strong>
                    <small className="metric-sub">{fixedShare}% da renda alocada</small>
                  </div>
                </div>

                <div className="distribution-block">
                  <div className={`distribution-bar ${freeBalance < 0 ? 'over' : ''}`} aria-hidden="true">
                    <span className="seg-fixed" style={{ width: `${fixedShare}%` }} title={`Fixos (${fixedShare}%)`} />
                    {variableShare > 0 && (
                      <span className="seg-variable" style={{ width: `${variableShare}%` }} title={`Variáveis (${variableShare}%)`} />
                    )}
                    {reserveShare > 0 && (
                      <span className="seg-reserve" style={{ width: `${reserveShare}%` }} title={`Reserva (${reserveShare}%)`} />
                    )}
                  </div>
                  <div className="distribution-legend">
                    <div className="legend-items">
                      <span><i className="dot-fixed" />{fixedShare}% Fixos</span>
                      <span><i className="dot-variable" />{variableShare}% Variáveis</span>
                      <span><i className="dot-reserve" />{reserveShare}% Reserva</span>
                    </div>
                  </div>
                </div>

                <div className="ai-insight">
                  <div className="ai-insight-icon" aria-hidden="true">
                    <Sparkles size={17} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                      <strong>
                        {activeAiSummary?.headline ?? 'Previsão ValorAI'}
                      </strong>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className="tx-badge ia">
                          {activeAiSummary?.source === 'ai' ? 'IA' : 'Resumo local'}
                        </span>
                        {aiEnabled && (
                          <button
                            type="button"
                            className="button button-secondary button-small"
                            onClick={handleRefreshAiSummary}
                            disabled={aiSummaryBusy}
                          >
                            {aiSummaryBusy ? 'Atualizando…' : 'Atualizar'}
                          </button>
                        )}
                      </div>
                    </div>
                    <p>
                      {activeAiSummary?.summary ??
                        dashboard?.summary.insight.message ??
                        `Seus gastos fixos comprometem ${fixedShare}% da renda mensal. Registre seus lançamentos para acompanhar o ritmo diário.`}
                    </p>
                    {activeAiSummary && activeAiSummary.recommendations.length > 0 && (
                      <ul style={{ margin: '8px 0 0', paddingLeft: 18, fontSize: '0.88rem' }}>
                        {activeAiSummary.recommendations.map((rec, idx) => (
                          <li key={idx}>{rec}</li>
                        ))}
                      </ul>
                    )}
                    {aiEnabled && aiTier === 'free_prototype' && (
                      <small className="field-hint" style={{ display: 'block', marginTop: 6 }}>
                        Ambiente de protótipo (Free Tier): métricas resumidas sem dados pessoais.
                      </small>
                    )}
                  </div>
                </div>
              </section>

              {/* 2. Últimas movimentações */}
              <section className="card ledger-card" aria-labelledby="ledger-title">
                <div className="ledger-card-header">
                  <div>
                    <div className="ledger-title-row">
                      <h2 id="ledger-title">Últimas Movimentações</h2>
                    </div>
                  </div>
                  <div className="segment-pills" role="group" aria-label="Filtrar movimentações">
                    {([
                      ['all', 'Todas'],
                      ['fixed', 'Fixas'],
                      ['variable', 'Variáveis'],
                    ] as const).map(([id, label]) => (
                      <button
                        key={id}
                        type="button"
                        className={ledgerFilter === id ? 'active' : ''}
                        aria-pressed={ledgerFilter === id}
                        onClick={() => setLedgerFilter(id)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {recentTransactions.length > 0 ? (
                  <ul className="tx-list" aria-label="Movimentações recentes">
                    {recentTransactions.map((tx) => {
                      const Icon = categoryIcon(tx.category, tx.kind);
                      const isIncome = tx.kind === 'income';
                      const kindClass = isIncome ? 'income' : tx.kind === 'fixed_expense' ? 'fixed' : 'variable';
                      return (
                        <li key={tx.id} className="tx-row">
                          <div className="tx-main">
                            <div className={`tx-icon ${kindClass}`}>
                              <Icon size={19} aria-hidden="true" />
                            </div>
                            <div className="tx-info">
                              <p className="tx-title">{tx.title}</p>
                              <p className={`tx-sub ${isIncome ? 'income' : ''}`}>
                                {tx.category}
                                {tx.kind === 'fixed_expense' && !tx.category.toLowerCase().includes('fixo') ? ' (Fixo)' : ''}
                                {tx.status === 'pending' ? ' · A vencer' : ''}
                              </p>
                            </div>
                          </div>
                          <span className={`tx-amount num ${isIncome ? 'positive' : ''}`}>
                            {isIncome ? '+' : '-'} {currency(tx.amount)}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                ) : (
                  <div className="tx-empty">
                    <p>
                      <strong>{transactions.length ? 'Nenhuma movimentação neste filtro.' : 'Nenhuma movimentação registrada neste ciclo.'}</strong>{' '}
                      Use <strong>Novo Lançamento</strong> para digitar, ler um comprovante ou importar seu extrato.
                    </p>
                    {!transactions.length && (
                      <div className="tx-empty-actions">
                        <button type="button" className="button button-secondary button-small" onClick={handleSeedDemo} disabled={actionBusy}>
                          <Sparkles size={16} aria-hidden="true" /> Carregar exemplo do ciclo
                        </button>
                      </div>
                    )}
                  </div>
                )}

                <div className="ledger-card-footer">
                  <span>
                    {recentTransactions.length} de {transactions.length} movimentações
                  </span>
                  <button type="button" className="text-link" onClick={() => onSelectTab('transactions')}>
                    <span>Ver extrato completo</span>
                    <ArrowRight size={16} aria-hidden="true" />
                  </button>
                </div>
              </section>
            </div>

            <div className="dash-col">
              {/* 3. Ritmo diário de despesas */}
              <section className="card side-card sparkline-card" aria-labelledby="sparkline-title">
                <div className="sparkline-head">
                  <div className="sparkline-title-wrap">
                    <TrendingUp size={18} aria-hidden="true" />
                    <h2 id="sparkline-title">Ritmo Diário de Despesas</h2>
                  </div>
                  <span className="avg-pill num">Média: {currency(dailyAverage)}/dia</span>
                </div>
                <div className="sparkline-Wrap">
                  <svg className="sparkline-svg" viewBox="0 0 300 64" preserveAspectRatio="none" aria-hidden="true">
                    <defs>
                      <linearGradient id="valoraiSparkGrad" x1="0" x2="0" y1="0" y2="1">
                        <stop offset="0%" stopColor="var(--chart)" stopOpacity="0.18" />
                        <stop offset="100%" stopColor="var(--chart)" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <path d={sparkline.area} fill="url(#valoraiSparkGrad)" />
                    <path
                      d={sparkline.line}
                      fill="none"
                      stroke="var(--chart)"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      vectorEffect="non-scaling-stroke"
                    />
                    <circle cx={sparkline.last.x} cy={sparkline.last.y} r="3.5" fill="var(--chart)" />
                  </svg>
                  <div className="sparkline-axis">
                    <span>DIA 01</span>
                    <span>DIA 10</span>
                    <span>DIA 20</span>
                    <span>HOJE</span>
                  </div>
                </div>
              </section>

              {/* 4. Objetivo em foco */}
              <section className="card side-card goal-focus-card" aria-labelledby="goal-focus-title">
                <div className="goal-focus-head">
                  <div className="goal-focus-Identity">
                    <div className="goal-focus-icon">
                      <PiggyBank size={18} aria-hidden="true" />
                    </div>
                    <div>
                      <h2 id="goal-focus-title">{activeGoal.title}</h2>
                      <span className="goal-focus-sub">Meta Prioritária</span>
                    </div>
                  </div>
                  <span className={`status-pill ${activeGoal.monthsRemaining === 0 ? 'balanced' : 'balanced'}`}>
                    <i className="status-dot" aria-hidden="true" />
                    {activeGoal.monthsRemaining === 0 ? 'Concluída' : 'Em dia'}
                  </span>
                </div>

                <div className="goal-progress-block">
                  <div className="goal-progress-numbers">
                    <span className="num">
                      <strong>{currency(activeGoal.current)}</strong>{' '}
                      <small>/ {currency(activeGoal.target)}</small>
                    </span>
                    <span className="goal-pct num">{activeGoal.percent}% acumulado</span>
                  </div>
                  <progress
                    className="styled-progress"
                    max={100}
                    value={activeGoal.percent}
                    aria-label={`Progresso da meta ${activeGoal.title}`}
                  />
                </div>

                <div className="goal-schedule-note">
                  <Clock3 size={16} aria-hidden="true" />
                  <p>
                    {activeGoal.monthsRemaining === 0 ? (
                      <strong>Meta concluída! Parabéns pela disciplina financeira.</strong>
                    ) : (
                      <>
                        No ritmo planejado ({currency(activeGoal.monthly)}/mês), sua meta estará completa em{' '}
                        <strong>{activeGoal.monthsRemaining} {activeGoal.monthsRemaining === 1 ? 'mês' : 'meses'}</strong>.
                      </>
                    )}
                  </p>
                </div>
              </section>

              {/* 5. Alerta informativo de limite */}
              <section className="card side-card limit-alert-card" aria-labelledby="limit-card-title">
                {primaryLimit ? (
                  <>
                    <div className="limit-card-head">
                      <div className="limit-card-title-group">
                        <div className={`limit-icon-tile ${primaryLimit.status === 'ok' ? 'ok' : 'alert'}`}>
                          <ReceiptText size={17} aria-hidden="true" />
                        </div>
                        <h2 id="limit-card-title">{primaryLimit.category}</h2>
                      </div>
                      <span className={`limit-pct-badge num ${primaryLimit.status}`}>
                        {primaryLimit.percent}%{primaryLimit.status === 'reached' ? ' · Atingido' : primaryLimit.status === 'exceeded' ? ' · Excedido' : ''}
                      </span>
                    </div>
                    <div className="limit-progress-wrap">
                      <progress
                        className={`styled-progress slim ${primaryLimit.status !== 'ok' ? 'terracotta' : ''}`}
                        max={100}
                        value={Math.min(100, primaryLimit.percent)}
                        aria-label={`Consumo do limite ${primaryLimit.category}`}
                      />
                      <div className="limit-numbers num">
                        <span>
                          {primaryLimit.scope === 'card_share'
                            ? `${primaryLimit.spent}% consumidos`
                            : `${currency(primaryLimit.spent)} gastos`}
                        </span>
                        <span>
                          Teto estimado:{' '}
                          {primaryLimit.scope === 'card_share'
                            ? `${primaryLimit.limit}%`
                            : currency(primaryLimit.limit)}
                        </span>
                      </div>
                    </div>
                    <p className="limit-advisory">{primaryLimit.advisory}</p>
                  </>
                ) : (
                  <>
                    <div className="limit-card-head">
                      <div className="limit-card-title-group">
                        <div className="limit-icon-tile ok">
                          <BellRing size={17} aria-hidden="true" />
                        </div>
                        <h2 id="limit-card-title">Limites &amp; Alertas</h2>
                      </div>
                    </div>
                    <p className="limit-advisory">
                      Nenhum teto definido. O alerta avisa ao atingir o limite, sem bloquear gastos.
                    </p>
                    <button type="button" className="text-link limit-setup-link" onClick={() => openLimitModal()}>
                      <span>Configurar teto de gastos</span>
                      <ArrowRight size={16} aria-hidden="true" />
                    </button>
                  </>
                )}
              </section>

              {/* 6. Guias práticos */}
              <section className="card side-card guides-mini-card" aria-labelledby="guides-title">
                <div className="guide-links-head">
                  <h2 id="guides-title">Guias Práticos</h2>
                  <button type="button" className="text-link" onClick={() => onSelectTab('guides')}>
                    Ver todos
                  </button>
                </div>
                {allLessons.length ? (
                  <ul className="guide-links">
                    {allLessons.slice(0, 3).map((item) => (
                      <li key={item.id}>
                        <button type="button" onClick={() => onOpenLesson(item)}>
                          <span>{item.title}</span>
                          {(item.progressPercent ?? 0) >= 100 ? (
                            <Check size={16} aria-label="Concluído" className="guide-done" />
                          ) : (
                            <ArrowRight size={16} aria-hidden="true" />
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="fine-print">Carregando guias…</p>
                )}
              </section>
            </div>
          </div>
        )}

        {/* ===================== TAB 2: TRANSAÇÕES & EXTRATOS ===================== */}
        {activeTab === 'transactions' && (
          <section className="card full-section-card" aria-labelledby="full-ledger-heading">
            <div className="full-ledger-top">
              <div>
                <h2 id="full-ledger-heading">Extrato &amp; Conciliação de Movimentações</h2>
                <p className="card-sub">
                  Todas as receitas, custos fixos e despesas pontuais categorizadas por canal de entrada
                </p>
              </div>
            </div>

            <div className="ledger-filters-bar">
              <div className="search-box">
                <Search size={16} aria-hidden="true" />
                <input
                  type="search"
                  placeholder="Buscar por descrição, categoria ou documento…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  aria-label="Buscar movimentações"
                />
              </div>
              <select
                value={ledgerFilter}
                onChange={(e) => setLedgerFilter(e.target.value as typeof ledgerFilter)}
                aria-label="Filtrar por natureza"
              >
                <option value="all">Todas as naturezas</option>
                <option value="variable">Despesas variáveis</option>
                <option value="fixed">Gastos fixos</option>
                <option value="income">Receitas / entradas</option>
              </select>
              <select
                value={channelFilter}
                onChange={(e) => setChannelFilter(e.target.value as typeof channelFilter)}
                aria-label="Filtrar por canal de entrada"
              >
                <option value="all">Todos os canais</option>
                <option value="manual">Digitação manual</option>
                <option value="import">Importação OFX/CSV/Excel</option>
                <option value="photo">Comprovante IA (Foto)</option>
              </select>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                aria-label="Filtrar por categoria"
              >
                <option value="all">Todas as categorias</option>
                {standardCategories.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>

            {filteredTransactions.length > 0 ? (
              <ul className="tx-list" aria-label="Extrato completo">
                {filteredTransactions.map((tx) => {
                  const Icon = categoryIcon(tx.category, tx.kind);
                  const isIncome = tx.kind === 'income';
                  return (
                    <li key={tx.id} className="tx-row">
                      <div className="tx-main">
                        <div className={`tx-icon ${isIncome ? 'income' : tx.kind === 'fixed_expense' ? 'fixed' : 'variable'}`}>
                          <Icon size={18} aria-hidden="true" />
                        </div>
                        <div className="tx-info">
                          <div className="tx-title-line">
                            <strong className="tx-title">{tx.title}</strong>
                            <span className={`tx-badge ${tx.channel === 'photo' ? 'ia' : tx.channel === 'import' ? 'ofx' : ''}`}>
                              {tx.channel === 'photo'
                                ? `Extraído via IA${tx.confidence ? ` • ${tx.confidence}%` : ''}`
                                : tx.channel === 'import'
                                  ? 'Extrato OFX/CSV'
                                  : 'Manual'}
                            </span>
                            <button
                              type="button"
                              className={`tx-status-pill ${tx.status}`}
                              onClick={() => handleToggleStatus(tx.id)}
                              title="Alternar entre Liquidado e A vencer"
                            >
                              {tx.status === 'paid' ? 'Liquidado' : 'A pagar / Pendente'}
                            </button>
                          </div>
                          <div className="tx-meta">
                            <span>{formatShortDate(tx.occurredOn)}</span>
                            <span>•</span>
                            <span className="tx-cat-chip">{tx.category}</span>
                            {tx.merchantDoc && (
                              <>
                                <span>•</span>
                                <span className="tx-doc">{tx.merchantDoc}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="tx-right">
                        <span className={`tx-amount num ${isIncome ? 'positive' : ''}`}>
                          {isIncome ? '+' : '−'} {currency(tx.amount)}
                        </span>
                        <div className="tx-row-actions">
                          <button
                            type="button"
                            className="icon-button-xs"
                            aria-label={`Editar ${tx.title}`}
                            onClick={() => openManualModal(tx)}
                          >
                            <PenLine size={14} />
                          </button>
                          <button
                            type="button"
                            className="icon-button-xs danger"
                            aria-label={`Excluir ${tx.title}`}
                            onClick={() => handleDeleteTransaction(tx.id)}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <div className="tx-empty">
                <p>
                  {transactions.length
                    ? 'Nenhum lançamento corresponde aos filtros selecionados.'
                    : 'Nenhuma movimentação registrada. Use Novo Lançamento para começar.'}
                </p>
                {!transactions.length && (
                  <div className="tx-empty-actions">
                    <button type="button" className="button button-secondary button-small" onClick={handleSeedDemo} disabled={actionBusy}>
                      <Sparkles size={16} aria-hidden="true" /> Carregar exemplo do ciclo
                    </button>
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {/* ===================== TAB 3: PLANEJAMENTO ===================== */}
        {activeTab === 'planning' && (
          <div className="dash-grid">
            <div className="dash-col">
              <section className="card" aria-labelledby="planning-limits-title">
                <div className="card-head">
                  <div>
                    <h2 id="planning-limits-title">Metas &amp; Limites Orçamentários</h2>
                    <p>Tetos configuráveis por categoria, consumo diário e cartão (alertas sem bloqueio)</p>
                  </div>
                  <button type="button" className="button button-primary button-small" onClick={() => openLimitModal()}>
                    <Plus size={16} aria-hidden="true" /> Novo limite
                  </button>
                </div>

                {limits.length > 0 ? (
                  <div className="limits-stack">
                    {limits.map((lim) => (
                      <div key={lim.id} className={`limit-item-box ${lim.status}`}>
                        <div className="limit-card-head">
                          <div>
                            <strong>{lim.category}</strong>
                            <small className="block-sub">
                              {lim.scope === 'daily'
                                ? 'Teto de consumo diário'
                                : lim.scope === 'card_share'
                                  ? 'Limite percentual no cartão'
                                  : 'Limite mensal da categoria'}
                            </small>
                          </div>
                          <div className="limit-item-right">
                            <span className={`limit-pct-badge num ${lim.status}`}>{lim.percent}%{lim.status === 'reached' ? ' · Atingido' : lim.status === 'exceeded' ? ' · Excedido' : ''}</span>
                            <button
                              type="button"
                              className="icon-button-xs"
                              aria-label={`Editar limite ${lim.category}`}
                              onClick={() => openLimitModal(lim)}
                            >
                              <PenLine size={14} />
                            </button>
                            <button
                              type="button"
                              className="icon-button-xs danger"
                              aria-label={`Remover limite ${lim.category}`}
                              onClick={() => handleDeleteLimit(lim.id)}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                        <progress
                          className={`styled-progress ${lim.status !== 'ok' ? 'terracotta' : ''}`}
                          max={100}
                          value={Math.min(100, lim.percent)}
                          aria-label={`Consumo do limite ${lim.category}`}
                        />
                        <div className="limit-numbers num">
                          <span>
                            Consumido:{' '}
                            {lim.scope === 'card_share' ? `${lim.spent}%` : currency(lim.spent)}
                          </span>
                          <span>
                            Teto:{' '}
                            {lim.scope === 'card_share' ? `${lim.limit}%` : currency(lim.limit)} (alerta em {lim.warnPercent}%)
                          </span>
                        </div>
                        <p className="limit-advisory">{lim.advisory}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="tx-empty">
                    <p>Nenhum limite configurado ainda. Crie um teto para receber avisos preventivos.</p>
                  </div>
                )}
              </section>
            </div>

            <div className="dash-col">
              <section className="card" aria-labelledby="planning-goal-title">
                <div className="card-head">
                  <div>
                    <h2 id="planning-goal-title">Objetivo Prioritário: {activeGoal.title}</h2>
                    <p>Acompanhamento de reserva e aportes mensais</p>
                  </div>
                </div>
                <div className="goal-progress-block">
                  <div className="goal-progress-numbers">
                    <span className="num">
                      <strong>{currency(activeGoal.current)}</strong> <small>/ {currency(activeGoal.target)}</small>
                    </span>
                    <span className="goal-pct num">{activeGoal.percent}%</span>
                  </div>
                  <progress
                    className="styled-progress"
                    max={100}
                    value={activeGoal.percent}
                    aria-label={`Progresso da meta ${activeGoal.title}`}
                  />
                </div>
                <p className="fine-print">
                  Aporte mensal planejado: <strong>{currency(activeGoal.monthly)}</strong> • Previsão:{' '}
                  <strong>{activeGoal.monthsRemaining} {activeGoal.monthsRemaining === 1 ? 'mês' : 'meses'}</strong>.
                </p>
                <div className="card-inline-actions">
                  <button type="button" className="button button-primary button-small" onClick={openGoalModal}>
                    Registrar aporte / Ajustar meta
                  </button>
                </div>
              </section>
            </div>
          </div>
        )}

        {/* ===================== TAB 4: GUIAS ===================== */}
        {activeTab === 'guides' && (() => {
          const normalizeSearch = (value: string) =>
            value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
          const categoryCounts = new Map<string, number>();
          for (const item of allLessons) {
            const cat = item.category?.trim() || 'Geral';
            categoryCounts.set(cat, (categoryCounts.get(cat) ?? 0) + 1);
          }
          const categories = Array.from(categoryCounts.entries());
          const normalizedQuery = normalizeSearch(guideSearch.trim());
          const filteredLessons = allLessons.filter((item) => {
            const cat = item.category?.trim() || 'Geral';
            if (guideCategory !== 'all' && cat !== guideCategory) return false;
            if (!normalizedQuery) return true;
            const haystack = normalizeSearch(`${item.title} ${item.description} ${cat} ${item.body}`);
            return haystack.includes(normalizedQuery);
          });

          return (
          <section className="card full-section-card" aria-labelledby="guides-library-title">
            <div className="card-head">
              <div>
                <h2 id="guides-library-title">Biblioteca de Educação Financeira</h2>
                <p>Guias práticos pré-carregados para apoiar suas decisões e metas</p>
              </div>
              <span className="tag">{filteredLessons.length} de {allLessons.length} guias</span>
            </div>

            <div className="guides-toolbar">
              <div className="search-box">
                <Search size={16} aria-hidden="true" />
                <input
                  type="search"
                  placeholder="Buscar guias por título, tema ou conteúdo…"
                  value={guideSearch}
                  onChange={(e) => setGuideSearch(e.target.value)}
                  aria-label="Buscar guias financeiros"
                />
              </div>
              <div className="guide-category-pills" role="group" aria-label="Filtrar guias por categoria">
                <button
                  type="button"
                  className={`guide-cat-pill ${guideCategory === 'all' ? 'active' : ''}`}
                  aria-pressed={guideCategory === 'all'}
                  onClick={() => setGuideCategory('all')}
                >
                  Todos ({allLessons.length})
                </button>
                {categories.map(([cat, count]) => (
                  <button
                    key={cat}
                    type="button"
                    className={`guide-cat-pill ${guideCategory === cat ? 'active' : ''}`}
                    aria-pressed={guideCategory === cat}
                    onClick={() => setGuideCategory(cat)}
                  >
                    {cat} ({count})
                  </button>
                ))}
              </div>
            </div>

            {filteredLessons.length > 0 ? (
              <div className="guides-cards-grid">
                {filteredLessons.map((item) => {
                  const pct = item.progressPercent ?? 0;
                  return (
                    <article key={item.id} className="guide-editorial-card">
                      <div className="guide-editorial-top">
                        <span className="guide-icon">
                          <BookOpen size={20} aria-hidden="true" />
                        </span>
                        <span className="tag">
                          <Clock3 size={13} aria-hidden="true" /> {item.minutes} min de leitura
                        </span>
                      </div>
                      {item.category && (
                        <span className="guide-category-tag">{item.category}</span>
                      )}
                      <h3>{item.title}</h3>
                      <p>{item.description}</p>
                      <div className="guide-progress-row">
                        <progress className="styled-progress" max={100} value={pct} aria-label={`Progresso de leitura: ${item.title}`} />
                        <div className="guide-progress-meta">
                          <span>{pct >= 100 ? 'Concluído' : pct > 0 ? `Em leitura (${pct}%)` : 'Não iniciado'}</span>
                          <div className="guide-card-btns">
                            <button
                              type="button"
                              className="link-button"
                              onClick={() => onOpenLesson(item)}
                            >
                              Ler guia
                            </button>
                            {pct < 100 && (
                              <button
                                type="button"
                                className="button button-secondary button-small"
                                onClick={() => handleMarkLessonProgress(item.id, 100)}
                                disabled={actionBusy}
                              >
                                Marcar concluído
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="guides-empty-state">
                <p>Nenhum guia encontrado para os filtros selecionados.</p>
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={() => { setGuideSearch(''); setGuideCategory('all'); }}
                >
                  Limpar filtros
                </button>
              </div>
            )}
          </section>
          );
        })()}
      </main>

      <footer className="site-footer dash-footer">
        <div>
          <span>Uma iniciativa</span>
          <CompanyMark />
        </div>
        <div className="dash-footer-meta">
          <button type="button" className="text-link muted" onClick={onOpenAbout}>Sobre o protótipo</button>
          <span aria-hidden="true">•</span>
          <span>Ciclo ativo {cycleCode}</span>
        </div>
      </footer>

      {/* ===================== MOBILE BOTTOM BAR ===================== */}
      <nav className="mobile-bottom-nav" aria-label="Navegação móvel">
        {navItems.map(({ id, short, Icon }) => (
          <button
            key={id}
            type="button"
            className={activeTab === id ? 'active' : ''}
            aria-current={activeTab === id ? 'page' : undefined}
            onClick={() => onSelectTab(id)}
          >
            <Icon size={20} aria-hidden="true" />
            <span>{short}</span>
          </button>
        ))}
      </nav>

      {/* Greeting kept for screen readers that land on the workspace. */}
      <p className="sr-only" aria-live="polite">{`Painel de ${firstName}: ${tabMeta[activeTab].title}`}</p>

      {/* ===================== MODALS ===================== */}

      {/* 1. Manual Transaction Modal */}
      {activeModal === 'manual' && (
        <LightDismissModal
          title={editingTxId ? 'Editar lançamento' : 'Novo lançamento manual'}
          onClose={() => setActiveModal(null)}
        >
          <form className="modal-body" onSubmit={handleSaveManual} noValidate>
            {modalError && <div className="alert alert-error" role="alert"><CircleAlert size={16} /><span>{modalError}</span></div>}
            <div className="fields-grid">
              <div className={`field wide ${fieldErrs.title ? 'has-error' : ''}`}>
                <label htmlFor="txTitle">Descrição / Estabelecimento</label>
                <input
                  id="txTitle"
                  value={txTitle}
                  placeholder="Ex.: Pão de Açúcar, Aluguel, Consultoria"
                  maxLength={120}
                  onChange={(e) => {
                    const val = e.target.value;
                    setTxTitle(val);
                    if (txAutoCategory && val.trim().length >= 3) {
                      const suggested = suggestCategory(val);
                      setTxCategory(suggested.category);
                      setTxKind(suggested.kind);
                    }
                  }}
                />
                {fieldErrs.title && <span className="field-error"><CircleAlert size={13} />{fieldErrs.title}</span>}
              </div>

              <div className={`field ${fieldErrs.amount ? 'has-error' : ''}`}>
                <label htmlFor="txAmount">Valor (R$)</label>
                <div className="money-input">
                  <span>R$</span>
                  <input
                    id="txAmount"
                    inputMode="decimal"
                    placeholder="0,00"
                    value={txAmount}
                    onChange={(e) => setTxAmount(e.target.value)}
                  />
                </div>
                {fieldErrs.amount && <span className="field-error"><CircleAlert size={13} />{fieldErrs.amount}</span>}
              </div>

              <div className="field">
                <label htmlFor="txKind">Natureza</label>
                <select
                  id="txKind"
                  value={txKind}
                  onChange={(e) => {
                    const nextKind = e.target.value as typeof txKind;
                    setTxKind(nextKind);
                    if (txAutoCategory) {
                      setTxCategory(suggestCategory(txTitle, nextKind).category);
                    }
                  }}
                >
                  {transactionKinds.map((k) => (
                    <option key={k.id} value={k.id}>{k.label}</option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label htmlFor="txCategory">Categoria (obrigatória)</label>
                <select
                  id="txCategory"
                  value={txCategory}
                  onChange={(e) => {
                    setTxCategory(e.target.value);
                    setTxAutoCategory(false);
                  }}
                >
                  {standardCategories.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label htmlFor="txDate">Data de competência / vencimento</label>
                <input
                  id="txDate"
                  type="date"
                  value={txDate}
                  onChange={(e) => setTxDate(e.target.value)}
                />
              </div>

              <div className="field">
                <label htmlFor="txMethod">Meio de pagamento</label>
                <select
                  id="txMethod"
                  value={txMethod}
                  onChange={(e) => setTxMethod(e.target.value as typeof txMethod)}
                >
                  {paymentMethods.map((pm) => (
                    <option key={pm.id} value={pm.id}>{pm.label}</option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label htmlFor="txStatus">Situação</label>
                <select
                  id="txStatus"
                  value={txStatus}
                  onChange={(e) => setTxStatus(e.target.value as 'paid' | 'pending')}
                >
                  <option value="paid">Liquidado / Pago</option>
                  <option value="pending">A pagar / A receber</option>
                </select>
              </div>
            </div>
            <div className="form-actions">
              <button type="button" className="button button-ghost" onClick={() => setActiveModal(null)}>
                Cancelar
              </button>
              <button type="submit" className="button button-primary" disabled={actionBusy}>
                {actionBusy ? 'Salvando…' : editingTxId ? 'Salvar alterações' : 'Registrar lançamento'}
              </button>
            </div>
          </form>
        </LightDismissModal>
      )}

      {/* 2. Receipt AI / OCR Modal */}
      {activeModal === 'receipt' && (
        <LightDismissModal title="Leitura de Comprovante por IA" onClose={() => setActiveModal(null)}>
          <div className="modal-body">
            {modalError && <div className="alert alert-error" role="alert"><CircleAlert size={16} /><span>{modalError}</span></div>}
            <p>
              Envie a foto ou print de qualquer comprovante (cupom fiscal NFC-e/SAT, PIX, boleto, fatura de cartão ou maquininha). O motor identifica o valor pago, data e sugere a categoria para sua confirmação.
            </p>
            {aiEnabled && aiTier === 'free_prototype' && (
              <p className="field-hint">
                Protótipo Free Tier: utilize comprovantes de teste ou sem dados bancários sensíveis reais.
              </p>
            )}

            <div className="upload-dropzone">
              <input
                id="receiptFileInput"
                type="file"
                accept="image/*,.pdf"
                capture="environment"
                className="sr-only"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  setReceiptFileName(file.name);
                  if (file.type.startsWith('image/')) {
                    try {
                      const compressed = await compressReceiptImage(file);
                      await handleExtractReceipt(undefined, file.name, receiptHint, compressed);
                      return;
                    } catch {
                      // Fallback to filename/hint extraction if browser fails to decode image
                    }
                  }
                  await handleExtractReceipt(undefined, file.name, receiptHint);
                }}
              />
              <label htmlFor="receiptFileInput" className="upload-dropzone-label">
                <Camera size={24} aria-hidden="true" />
                <strong>{receiptFileName || 'Selecionar foto do comprovante ou PDF'}</strong>
                <small>JPG, PNG, WebP ou PDF • Redimensionamento automático para economizar dados</small>
              </label>
            </div>

            <div className="sample-presets">
              <span className="field-hint">Ou teste a extração com um comprovante de exemplo:</span>
              <div className="preset-buttons">
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={() => handleExtractReceipt('supermarket', 'cupom-pao-de-acucar.jpg')}
                  disabled={actionBusy}
                >
                  NFC-e Supermercado (R$ 342,80)
                </button>
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={() => handleExtractReceipt('uber', 'recibo-uber.pdf')}
                  disabled={actionBusy}
                >
                  Recibo Uber PDF (R$ 42,90)
                </button>
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={() => handleExtractReceipt('restaurant', 'nota-restaurante.jpg')}
                  disabled={actionBusy}
                >
                  Nota Bistrô (R$ 128,50)
                </button>
              </div>
            </div>

            {extractedReceipt && (
              <form className="extracted-preview-box" onSubmit={handleConfirmReceipt}>
                <div className="extracted-head">
                  <strong>Dados extraídos do comprovante</strong>
                  <span className="tx-badge ia">
                    {extractedReceipt.source === 'fallback'
                      ? `Fallback • ${extractedReceipt.confidence}%`
                      : `Confiança IA: ${extractedReceipt.confidence}%`}
                  </span>
                </div>
                <div className="fields-grid">
                  <div className="field wide">
                    <label htmlFor="recTitle">Estabelecimento identificado</label>
                    <input
                      id="recTitle"
                      value={extractedReceipt.title}
                      onChange={(e) => setExtractedReceipt({ ...extractedReceipt, title: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="recAmount">Valor extraído (R$)</label>
                    <input
                      id="recAmount"
                      type="number"
                      step="0.01"
                      value={extractedReceipt.amount}
                      onChange={(e) => setExtractedReceipt({ ...extractedReceipt, amount: Number(e.target.value) })}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="recCategory">Categoria sugerida pela IA</label>
                    <select
                      id="recCategory"
                      value={extractedReceipt.category}
                      onChange={(e) => setExtractedReceipt({ ...extractedReceipt, category: e.target.value })}
                    >
                      {standardCategories.map((cat) => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="recDate">Data da nota</label>
                    <input
                      id="recDate"
                      type="date"
                      value={extractedReceipt.occurredOn}
                      onChange={(e) => setExtractedReceipt({ ...extractedReceipt, occurredOn: e.target.value })}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="recDoc">CNPJ / Referência NFC-e</label>
                    <input
                      id="recDoc"
                      value={extractedReceipt.merchantDoc}
                      onChange={(e) => setExtractedReceipt({ ...extractedReceipt, merchantDoc: e.target.value })}
                    />
                  </div>
                </div>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={receiptConfirmedCheck}
                    onChange={(e) => setReceiptConfirmedCheck(e.target.checked)}
                  />
                  <span>Confirmo que conferi o valor e a categoria sugerida pela leitura inteligente.</span>
                </label>
                <button type="submit" className="button button-primary button-block" disabled={actionBusy}>
                  {actionBusy ? 'Lançando…' : 'Confirmar e lançar comprovante'}
                </button>
              </form>
            )}
          </div>
        </LightDismissModal>
      )}

      {/* 3. Batch Import (OFX / CSV / Excel) Modal */}
      {activeModal === 'import' && (
        <LightDismissModal title="Importar Extrato (OFX, CSV ou Excel)" onClose={() => setActiveModal(null)}>
          <div className="modal-body">
            {modalError && <div className="alert alert-error" role="alert"><CircleAlert size={16} /><span>{modalError}</span></div>}
            <p>
              Importe extratos bancários <strong>.OFX</strong> ou planilhas <strong>.CSV / .XLSX</strong>. O sistema classifica as categorias automaticamente e evita lançamentos duplicados.
            </p>

            <div className="upload-dropzone">
              <input
                id="importFileInput"
                type="file"
                accept=".ofx,.csv,.txt,.tsv,.xlsx,.xls,.xml"
                className="sr-only"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  setImportFileName(file.name);
                  const lower = file.name.toLowerCase();
                  const text = lower.endsWith('.xlsx') ? await extractXlsxText(file) : await file.text();
                  setImportContent(text);
                  const fmt = lower.endsWith('.ofx') ? 'ofx' : 'csv';
                  setImportFormat(fmt);
                  await handlePreviewImport(text, fmt, file.name);
                }}
              />
              <label htmlFor="importFileInput" className="upload-dropzone-label">
                <FileUp size={24} aria-hidden="true" />
                <strong>{importFileName || 'Selecionar arquivo .OFX, .CSV ou .XLSX'}</strong>
                <small>Compatível com extratos bancários brasileiros e planilhas de controle</small>
              </label>
            </div>

            <div className="sample-presets">
              <span className="field-hint">Ou carregue um arquivo demonstrativo para testar a conciliação:</span>
              <div className="preset-buttons">
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={() => {
                    setImportFileName('extrato-novembro.ofx');
                    setImportFormat('ofx');
                    setImportContent(SAMPLE_OFX);
                    handlePreviewImport(SAMPLE_OFX, 'ofx', 'extrato-novembro.ofx');
                  }}
                  disabled={actionBusy}
                >
                  Testar Extrato OFX Bancário
                </button>
                <button
                  type="button"
                  className="button button-secondary button-small"
                  onClick={() => {
                    setImportFileName('planilha-gastos.csv');
                    setImportFormat('csv');
                    setImportContent(SAMPLE_CSV);
                    handlePreviewImport(SAMPLE_CSV, 'csv', 'planilha-gastos.csv');
                  }}
                  disabled={actionBusy}
                >
                  Testar Planilha CSV / Excel
                </button>
              </div>
            </div>

            {importPreviewItems && (
              <div className="import-preview-block">
                <div className="extracted-head">
                  <strong>{importPreviewItems.length} lançamento(s) identificado(s)</strong>
                  <span className="tag">Revise as categorias antes de importar</span>
                </div>
                <ul className="import-preview-list">
                  {importPreviewItems.map((item, idx) => (
                    <li key={item.externalRef + idx} className={item.isDuplicate ? 'dup' : ''}>
                      <div className="import-item-info">
                        <strong>{item.title}</strong>
                        <small>{item.occurredOn} • {currency(item.amount)}</small>
                        {item.isDuplicate && <span className="tx-badge pending">Duplicado (será ignorado)</span>}
                      </div>
                      <select
                        value={item.category}
                        aria-label={`Categoria para ${item.title}`}
                        onChange={(e) => {
                          const next = [...importPreviewItems];
                          next[idx] = { ...item, category: e.target.value };
                          setImportPreviewItems(next);
                        }}
                      >
                        {standardCategories.map((cat) => (
                          <option key={cat} value={cat}>{cat}</option>
                        ))}
                      </select>
                    </li>
                  ))}
                </ul>
                <button
                  type="button"
                  className="button button-primary button-block"
                  onClick={handleConfirmImport}
                  disabled={actionBusy}
                >
                  {actionBusy ? 'Importando…' : 'Confirmar importação em lote'}
                </button>
              </div>
            )}
          </div>
        </LightDismissModal>
      )}

      {/* 4. Budget Limit Modal */}
      {activeModal === 'limit' && (
        <LightDismissModal title="Configurar Teto e Alerta Orçamentário" onClose={() => setActiveModal(null)}>
          <form className="modal-body" onSubmit={handleSaveLimit}>
            {modalError && <div className="alert alert-error" role="alert"><CircleAlert size={16} /><span>{modalError}</span></div>}
            <p>
              Defina um teto para acompanhar o ritmo dos seus gastos. Os alertas funcionam como referência educativa e nunca bloqueiam pagamentos ou salvamento de transações.
            </p>
            <div className="fields-grid">
              <div className="field wide">
                <label htmlFor="limitScope">Tipo de regra</label>
                <select
                  id="limitScope"
                  value={limitScope}
                  onChange={(e) => setLimitScope(e.target.value as typeof limitScope)}
                >
                  <option value="category">Limite mensal por categoria (R$)</option>
                  <option value="daily">Teto de consumo diário (ex.: R$ 100,00/dia)</option>
                  <option value="card_share">Limite percentual no cartão em variáveis (%)</option>
                </select>
              </div>

              {limitScope === 'category' && (
                <div className="field wide">
                  <label htmlFor="limitCategory">Categoria monitorada</label>
                  <select
                    id="limitCategory"
                    value={limitCategory}
                    onChange={(e) => setLimitCategory(e.target.value)}
                  >
                    {standardCategories.filter((c) => c !== 'Renda').map((cat) => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
              )}

              <div className="field">
                <label htmlFor="limitValue">
                  {limitScope === 'card_share' ? 'Percentual máximo (%)' : 'Valor do teto (R$)'}
                </label>
                <input
                  id="limitValue"
                  inputMode="decimal"
                  value={limitValue}
                  onChange={(e) => setLimitValue(e.target.value)}
                />
              </div>

              <div className="field">
                <label htmlFor="limitWarn">Aviso preventivo em (%)</label>
                <input
                  id="limitWarn"
                  type="number"
                  min={10}
                  max={100}
                  value={limitWarn}
                  onChange={(e) => setLimitWarn(e.target.value)}
                />
              </div>
            </div>
            <div className="form-actions">
              <button type="button" className="button button-ghost" onClick={() => setActiveModal(null)}>
                Cancelar
              </button>
              <button type="submit" className="button button-primary" disabled={actionBusy}>
                {actionBusy ? 'Salvando…' : 'Salvar teto'}
              </button>
            </div>
          </form>
        </LightDismissModal>
      )}

      {/* 5. Priority Goal & Reserve Modal */}
      {activeModal === 'goal' && (
        <LightDismissModal title={`Meta Prioritária: ${activeGoal.title}`} onClose={() => setActiveModal(null)}>
          <form className="modal-body" onSubmit={handleSaveGoal}>
            {modalError && <div className="alert alert-error" role="alert"><CircleAlert size={16} /><span>{modalError}</span></div>}
            <div className="fields-grid">
              <div className="field">
                <label htmlFor="goalTarget">Meta total desejada (R$)</label>
                <input
                  id="goalTarget"
                  inputMode="decimal"
                  value={goalTarget}
                  onChange={(e) => setGoalTarget(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="goalCurrent">Saldo já acumulado (R$)</label>
                <input
                  id="goalCurrent"
                  inputMode="decimal"
                  value={goalCurrent}
                  onChange={(e) => setGoalCurrent(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="goalMonthly">Aporte mensal planejado (R$)</label>
                <input
                  id="goalMonthly"
                  inputMode="decimal"
                  value={goalMonthly}
                  onChange={(e) => setGoalMonthly(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="goalContribution">Novo aporte hoje (opcional R$)</label>
                <input
                  id="goalContribution"
                  inputMode="decimal"
                  placeholder="0,00"
                  value={goalContribution}
                  onChange={(e) => setGoalContribution(e.target.value)}
                />
              </div>
            </div>
            <div className="form-actions">
              <button type="button" className="button button-ghost" onClick={() => setActiveModal(null)}>
                Cancelar
              </button>
              <button type="submit" className="button button-primary" disabled={actionBusy}>
                {actionBusy ? 'Salvando…' : 'Salvar evolução da meta'}
              </button>
            </div>
          </form>
        </LightDismissModal>
      )}

      {/* 6. RF003 Personal Profile Maintenance Modal */}
      {activeModal === 'profile' && (
        <LightDismissModal title="Manter Perfil Cadastral (RF003)" onClose={() => setActiveModal(null)}>
          <form className="modal-body" onSubmit={handleSaveProfile} noValidate>
            {modalError && <div className="alert alert-error" role="alert"><CircleAlert size={16} /><span>{modalError}</span></div>}
            <div className="avatar-picker">
              <span className="avatar-preview" aria-hidden="true">
                {profAvatar ? <img src={profAvatar} alt="" /> : initials}
              </span>
              <div className="avatar-picker-body">
                <strong>Foto de perfil</strong>
                <small>JPG, PNG ou WebP até 2 MB. Ela será recortada em formato quadrado.</small>
                <div className="avatar-picker-actions">
                  <label className="button button-secondary button-small" htmlFor="profAvatar">
                    {profAvatar ? 'Trocar foto' : 'Escolher foto'}
                  </label>
                  {profAvatar && (
                    <button type="button" className="button button-ghost button-small" onClick={() => setProfAvatar(null)}>
                      Remover
                    </button>
                  )}
                </div>
                <input
                  id="profAvatar"
                  className="sr-only"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={async (e) => {
                    const input = e.currentTarget;
                    const file = input.files?.[0];
                    input.value = '';
                    if (!file) return;
                    if (file.size > 2 * 1024 * 1024) {
                      setModalError('O avatar deve ter no máximo 2 MB.');
                      return;
                    }
                    try {
                      setModalError('');
                      setProfAvatar(await squareAvatar(file));
                    } catch {
                      setModalError('Não foi possível ler a imagem do avatar.');
                    }
                  }}
                />
              </div>
            </div>
            <div className="fields-grid">
              <div className={`field wide ${fieldErrs.name ? 'has-error' : ''}`}>
                <label htmlFor="profName">Nome completo</label>
                <input
                  id="profName"
                  value={profName}
                  maxLength={120}
                  onChange={(e) => setProfName(e.target.value)}
                />
                {fieldErrs.name && <span className="field-error"><CircleAlert size={13} />{fieldErrs.name}</span>}
              </div>

              <div className="field">
                <label htmlFor="profCpf">CPF (inalterável)</label>
                <input id="profCpf" value={profile?.cpf ?? '***.***.***-**'} disabled readOnly />
              </div>

              <div className={`field ${fieldErrs.birthDate ? 'has-error' : ''}`}>
                <label htmlFor="profBirth">Data de nascimento</label>
                <input
                  id="profBirth"
                  type="date"
                  value={profBirth}
                  onChange={(e) => setProfBirth(e.target.value)}
                />
                {fieldErrs.birthDate && <span className="field-error"><CircleAlert size={13} />{fieldErrs.birthDate}</span>}
              </div>

              <div className={`field ${fieldErrs.phone ? 'has-error' : ''}`}>
                <label htmlFor="profPhone">Celular / WhatsApp</label>
                <input
                  id="profPhone"
                  value={profPhone}
                  onChange={(e) => setProfPhone(maskPhone(e.target.value))}
                />
                {fieldErrs.phone && <span className="field-error"><CircleAlert size={13} />{fieldErrs.phone}</span>}
              </div>

              <div className={`field ${fieldErrs.postalCode ? 'has-error' : ''}`}>
                <label htmlFor="profPostal">CEP</label>
                <input
                  id="profPostal"
                  value={profPostal}
                  onChange={(e) => setProfPostal(maskPostal(e.target.value))}
                />
                {fieldErrs.postalCode && <span className="field-error"><CircleAlert size={13} />{fieldErrs.postalCode}</span>}
              </div>

              <div className={`field ${fieldErrs.state ? 'has-error' : ''}`}>
                <label htmlFor="profState">Estado (UF)</label>
                <select id="profState" value={profState} onChange={(e) => setProfState(e.target.value)}>
                  {states.map((st) => (
                    <option key={st} value={st}>{st}</option>
                  ))}
                </select>
              </div>

              <div className={`field ${fieldErrs.city ? 'has-error' : ''}`}>
                <label htmlFor="profCity">Cidade</label>
                <input
                  id="profCity"
                  value={profCity}
                  maxLength={100}
                  onChange={(e) => setProfCity(e.target.value)}
                />
                {fieldErrs.city && <span className="field-error"><CircleAlert size={13} />{fieldErrs.city}</span>}
              </div>

            </div>

            {profile?.history && profile.history.length > 0 && (
              <div className="profile-history-note">
                <strong>Histórico recente de alterações:</strong>
                <ul>
                  {profile.history.slice(0, 3).map((h) => (
                    <li key={h.id}>
                      Campos atualizados: {h.changedFields.join(', ')}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="form-actions">
              <button type="button" className="button button-ghost" onClick={() => setActiveModal(null)}>
                Cancelar
              </button>
              <button type="submit" className="button button-primary" disabled={actionBusy}>
                {actionBusy ? 'Salvando…' : 'Salvar dados cadastrais'}
              </button>
            </div>
          </form>
        </LightDismissModal>
      )}
    </>
  );
}
