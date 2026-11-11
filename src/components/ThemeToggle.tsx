import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

export type Theme = 'light' | 'dark';
export const THEME_KEY = 'valorai-theme';
const THEME_EVENT = 'valorai-theme';

const themeColor = { light: '#f5f5f1', dark: '#242830' } as const;

export function readTheme(): Theme {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
}

export function applyTheme(theme: Theme, persist: boolean) {
  document.documentElement.setAttribute('data-theme', theme);
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', themeColor[theme]);
  if (persist) localStorage.setItem(THEME_KEY, theme);
  window.dispatchEvent(new CustomEvent(THEME_EVENT, { detail: theme }));
}

function storedTheme(): Theme | null {
  const value = localStorage.getItem(THEME_KEY);
  return value === 'light' || value === 'dark' ? value : null;
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    const sync = () => setTheme(readTheme());
    sync();
    const onTheme = () => sync();
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const onMedia = () => {
      if (storedTheme()) return;
      applyTheme(media.matches ? 'dark' : 'light', false);
    };
    window.addEventListener(THEME_EVENT, onTheme);
    media.addEventListener('change', onMedia);
    return () => {
      window.removeEventListener(THEME_EVENT, onTheme);
      media.removeEventListener('change', onMedia);
    };
  }, []);

  const dark = theme === 'dark';
  return (
    <button
      type="button"
      className="icon-button theme-toggle"
      aria-pressed={dark}
      aria-label={theme === null ? 'Alternar tema' : dark ? 'Ativar tema claro' : 'Ativar tema escuro'}
      onClick={() => applyTheme(readTheme() === 'dark' ? 'light' : 'dark', true)}
    >
      <Moon className="theme-icon theme-icon-moon" size={18} aria-hidden="true" />
      <Sun className="theme-icon theme-icon-sun" size={18} aria-hidden="true" />
    </button>
  );
}
