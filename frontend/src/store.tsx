import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { getState, type HubState } from './api';

export type Page = 'mine' | 'workers' | 'gas' | 'network' | 'entry' | 'log';
export type Selection = { kind: 'worker' | 'repeater' | 'exit' | 'hazard'; id: string } | null;

interface Store {
  s: HubState | null;
  /** ms since the last good answer from the hub (Infinity before the first one) */
  staleMs: number;
  error: string | null;
  page: Page;
  go: (p: Page, sel?: Selection) => void;
  sel: Selection;
  select: (s: Selection) => void;
  toast: (msg: string, bad?: boolean) => void;
  toasts: { id: number; msg: string; bad: boolean }[];
  refresh: () => void;
}

const Ctx = createContext<Store | null>(null);
export const useStore = () => {
  const c = useContext(Ctx);
  if (!c) throw new Error('no store');
  return c;
};

const PAGES: Page[] = ['mine', 'workers', 'gas', 'network', 'entry', 'log'];
function pageFromHash(): Page {
  const h = location.hash.replace(/^#\/?/, '').split('?')[0] as Page;
  return PAGES.includes(h) ? h : 'mine';
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [s, setS] = useState<HubState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastOk, setLastOk] = useState(0);
  const [now, setNow] = useState(Date.now());
  const [page, setPage] = useState<Page>(pageFromHash());
  const [sel, select] = useState<Selection>(null);
  const [toasts, setToasts] = useState<Store['toasts']>([]);
  const busy = useRef(false);

  const poll = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 4000);
    try {
      const st = await getState(ac.signal);
      setS(st);
      setLastOk(Date.now());
      setError(null);
    } catch (e) {
      setError((e as Error).name === 'AbortError' ? 'The hub did not answer in 4 s' : (e as Error).message);
    } finally {
      clearTimeout(t);
      busy.current = false;
    }
  }, []);

  useEffect(() => {
    poll();
    const a = setInterval(poll, 1000);
    const b = setInterval(() => setNow(Date.now()), 500);
    const onHash = () => setPage(pageFromHash());
    window.addEventListener('hashchange', onHash);
    return () => { clearInterval(a); clearInterval(b); window.removeEventListener('hashchange', onHash); };
  }, [poll]);

  const go = useCallback((p: Page, nextSel: Selection = null) => {
    select(nextSel);                       // a new page starts with nothing selected
    location.hash = '/' + p;
    setPage(p);
  }, []);

  const toast = useCallback((msg: string, bad = false) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, msg, bad }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), bad ? 7000 : 4000);
  }, []);

  const value = useMemo<Store>(() => ({
    s, error, page, go, sel, select, toast, toasts, refresh: poll,
    staleMs: lastOk ? now - lastOk : Infinity,
  }), [s, error, page, go, sel, toast, toasts, poll, lastOk, now]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
