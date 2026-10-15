import { useEffect, useRef, type ReactNode } from 'react';
import type { Status } from '../api';
import { useStore } from '../store';
import { COLOR, rssiBars, statusColor, statusWord } from '../util';

export function StatusPill({ st, children }: { st: Status | 'OFF' | 'INFO'; children?: ReactNode }) {
  const cls = st.replace(' ', '');
  const col = st === 'OFF' ? COLOR.nodata : st === 'INFO' ? COLOR.info : statusColor(st);
  return (
    <span className={`pill s-${cls}`}>
      <i className="dot" style={{ background: col }} />
      {children ?? statusWord(st)}
    </span>
  );
}

export function Bars({ rssi }: { rssi: number | null | undefined }) {
  const n = rssiBars(rssi);
  return (
    <svg width="20" height="14" viewBox="0 0 20 14" aria-label={`signal ${n} of 4`} role="img">
      {[0, 1, 2, 3].map((i) => (
        <rect key={i} x={i * 5} y={12 - (i + 1) * 3} width="3.4" height={(i + 1) * 3}
          rx="1" fill={i < n ? (n <= 1 ? COLOR.warn : COLOR.ink) : '#3A464D'} />
      ))}
    </svg>
  );
}

/** small line chart with optional warning / danger lines */
export function Spark({ values, warn, danger, color = COLOR.ink, min, max, height = 56 }: {
  values: (number | null)[]; warn?: number; danger?: number; color?: string; min?: number; max?: number; height?: number;
}) {
  const v = values.map((x) => (x === null || x === undefined || Number.isNaN(x) ? null : x));
  const nums = v.filter((x): x is number => x !== null);
  if (nums.length < 2) return <div className="spark muted" style={{ height, display: 'grid', placeItems: 'center', fontSize: 13 }}>Not enough data yet</div>;
  let lo = min ?? Math.min(...nums), hi = max ?? Math.max(...nums);
  if (warn !== undefined) { lo = Math.min(lo, warn); hi = Math.max(hi, warn); }
  if (danger !== undefined && danger < hi * 1.6) hi = Math.max(hi, danger);
  if (hi - lo < 1e-6) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.08;
  lo -= pad; hi += pad;
  const W = 300, H = height;
  const X = (i: number) => (i / (v.length - 1)) * W;
  const Y = (y: number) => H - ((y - lo) / (hi - lo)) * H;
  let d = '';
  v.forEach((y, i) => { if (y === null) return; d += `${d && v[i - 1] !== null ? 'L' : 'M'}${X(i).toFixed(1)},${Y(y).toFixed(1)}`; });
  return (
    <svg className="spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ height }}>
      {warn !== undefined && warn > lo && warn < hi && <line x1="0" x2={W} y1={Y(warn)} y2={Y(warn)} stroke={COLOR.warn} strokeDasharray="4 4" strokeWidth="1" vectorEffect="non-scaling-stroke" />}
      {danger !== undefined && danger > lo && danger < hi && <line x1="0" x2={W} y1={Y(danger)} y2={Y(danger)} stroke={COLOR.danger} strokeDasharray="4 4" strokeWidth="1" vectorEffect="non-scaling-stroke" />}
      <path d={d} fill="none" stroke={color} strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  );
}

export function Modal({ title, children, onClose, danger }: { title: string; children: ReactNode; onClose: () => void; danger?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', k);
    ref.current?.querySelector<HTMLElement>('input, textarea, select, button')?.focus();
    return () => window.removeEventListener('keydown', k);
  }, [onClose]);
  return (
    <div className="scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal${danger ? ' danger' : ''}`} role="dialog" aria-modal="true" aria-label={title} ref={ref}>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  );
}

export function Toasts() {
  const { toasts } = useStore();
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((t) => <div key={t.id} className={`toast${t.bad ? ' bad' : ''}`}>{t.msg}</div>)}
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return <div className="empty"><b>{title}</b>{children}</div>;
}
