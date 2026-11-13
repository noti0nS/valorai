import { useEffect, useState } from 'react';

interface InstallEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

const DISMISS_KEY = 'valorai-install-dismissed';

export function PwaInstall() {
  const [event, setEvent] = useState<InstallEvent | null>(null);

  useEffect(() => {
    // Production builds only: a cache-first worker would serve stale modules under Astro HMR.
    if (import.meta.env.PROD && 'serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    }
    let dismissed = false;
    try { dismissed = localStorage.getItem(DISMISS_KEY) === '1'; } catch { /* ignore */ }
    const onPrompt = (e: Event) => {
      e.preventDefault();
      if (!dismissed) setEvent(e as InstallEvent);
    };
    const onInstalled = () => setEvent(null);
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  if (!event) return null;

  const dismiss = () => {
    try { localStorage.setItem(DISMISS_KEY, '1'); } catch { /* ignore */ }
    setEvent(null);
  };
  const install = async () => {
    await event.prompt();
    await event.userChoice.catch(() => null);
    setEvent(null);
  };

  return (
    <div
      role="region"
      aria-label="Instalar aplicativo"
      style={{
        position: 'fixed', left: 16, right: 16, bottom: 16, zIndex: 50, maxWidth: 420, marginInline: 'auto',
        display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px',
        background: 'var(--surface)', color: 'var(--ink)', border: '1px solid var(--line)',
        borderRadius: 'var(--radius)', boxShadow: '0 8px 24px rgba(0,0,0,.18)',
      }}
    >
      <span style={{ flex: 1, fontSize: 14 }}>Instale o ValorAI no seu dispositivo para abrir como aplicativo.</span>
      <button type="button" className="button button-secondary" onClick={dismiss}>Agora não</button>
      <button type="button" className="button button-primary" onClick={install}>Instalar</button>
    </div>
  );
}
