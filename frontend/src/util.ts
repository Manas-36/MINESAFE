import type { HubState, Repeater, Status, Worker } from './api';

export const COLOR = {
  bg: '#12171A',
  panel: '#192024',
  line: '#2E3A40',
  ink: '#F3F0E8',
  muted: '#9DA7AD',
  amber: '#F2A900',
  safe: '#35C47C',
  warn: '#F0B429',
  danger: '#FF4D4F',
  info: '#4C9BF0',
  nodata: '#6B7A80',
};

export const statusColor = (st: Status | string) =>
  st === 'DANGER' ? COLOR.danger : st === 'WARNING' ? COLOR.warn : st === 'SAFE' ? COLOR.safe : COLOR.nodata;

export const statusWord = (st: Status | string) =>
  st === 'DANGER' ? 'Danger' : st === 'WARNING' ? 'Warning' : st === 'SAFE' ? 'Safe' : 'No data';

export const STATUS_ORDER: Record<string, number> = { DANGER: 0, WARNING: 1, 'NO DATA': 2, SAFE: 3 };
export const byStatus = (a: Worker, b: Worker) =>
  (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9) || a.name.localeCompare(b.name);

/** level 0 ok, 1 warning, 2 danger, -1 no data */
export function repeaterLevel(r: Repeater): number {
  if (!r.online) return -1;
  return Math.max(r.gas_level || 0, r.air_level || 0, r.sos ? 2 : 0);
}
export const levelColor = (l: number) => (l >= 2 ? COLOR.danger : l === 1 ? COLOR.warn : l === 0 ? COLOR.safe : COLOR.nodata);

export const G = { NONE: 0, LEFT: 1, RIGHT: 2, UP: 3, HERE: 4, NOWAY: 5, DANGER: 0x10 };
export function signText(code: number, dist: number) {
  if (code & G.DANGER) return { arrow: '!', text: 'DANGER' };
  switch (code & 0x0f) {
    case G.LEFT: return { arrow: '◀', text: `${dist} m` };
    case G.RIGHT: return { arrow: '▶', text: `${dist} m` };
    case G.UP: return { arrow: '▲', text: `${dist} m` };
    case G.HERE: return { arrow: '', text: 'EXIT' };
    case G.NOWAY: return { arrow: '✕', text: 'NO GO' };
    default: return { arrow: '', text: '' };
  }
}

export const fmt = (v: number | null | undefined, d = 0, unit = '') =>
  v === null || v === undefined || Number.isNaN(v) ? '–' : `${v.toFixed(d)}${unit}`;

export function ago(sec: number | null | undefined) {
  if (sec === null || sec === undefined) return '–';
  if (sec < 2) return 'now';
  if (sec < 60) return `${Math.round(sec)} s ago`;
  if (sec < 3600) return `${Math.round(sec / 60)} min ago`;
  return `${Math.round(sec / 3600)} h ago`;
}

export const workerById = (s: HubState, id: string) => s.workers.find((w) => w.body_id === id);
export const repeaterById = (s: HubState, id: string) => s.repeaters.find((r) => r.id === id);

/** main gas readings of a repeater, highest level first */
export function mainGases(r: Repeater) {
  const out: { ch: number; model: string; key: string; name: string; ppm: number | null; unit: string; warn: number; danger: number; level: number }[] = [];
  for (const c of r.gas_chs || []) {
    if (!c.ana || c.missing) continue;
    for (const g of c.ana.gases) if (g.main) out.push({ ch: c.ch, model: c.ana.model, ...g });
  }
  return out;
}

export function gasValue(ppm: number | null, unit: string) {
  if (ppm === null || ppm === undefined) return '–';
  if (unit === '%') return `${ppm.toFixed(2)} %`;
  return ppm >= 100 ? `${Math.round(ppm)} ppm` : `${ppm.toFixed(1)} ppm`;
}

export const rssiBars = (rssi: number | null | undefined) =>
  rssi === null || rssi === undefined || rssi <= -127 ? 0 : rssi > -60 ? 4 : rssi > -70 ? 3 : rssi > -80 ? 2 : 1;

/** gear code → readable name (falls back to 'Pants' for 'PANTS') */
export const gearName = (names: Record<string, string>, g: string) =>
  names[g] ?? g.charAt(0) + g.slice(1).toLowerCase().replace(/_/g, ' ');
