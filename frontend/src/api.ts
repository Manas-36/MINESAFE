// Everything the app reads comes from the admin hub's GET /api/state (polled every second).
// Everything it changes goes through the hub's own POST endpoints, so the buzzers, LED exit
// signs and body units react exactly as they do from the classic admin page.

export type Status = 'SAFE' | 'WARNING' | 'DANGER' | 'NO DATA';

export interface Live {
  age: number;
  temp: number | null;
  amb: number | null;
  hr: number | null;
  spo2: number | null;
  steps: number;
  amag: number;
  gmag: number;
  fl: number;
  flags: string[];
  near: string | null;
  near_rssi: number;
  rssi: number;
  hops: number;
  path: string[];
  heard_by: Record<string, number>;
  loss: number;
  mock: boolean;
  repeater: string | null;
  al: number | null;
  up: number;
}

export interface Worker {
  body_id: string;
  name: string;
  emp_id: string;
  work: string;
  zone: string;
  blood: string;
  allergies: string;
  conditions: string;
  medication: string;
  contact_name: string;
  contact_phone: string;
  notes: string;
  status: Status;
  reasons: string[];
  live: Live | null;
  cleared: { worker: string; worker_id: string; gear: string[]; time: string; photo: string } | null;
}

export interface GasReading {
  key: string;
  name: string;
  ppm: number | null;
  unit: string;
  warn: number;
  danger: number;
  level: number;
  main: boolean;
}

export interface GasChannel {
  ch: number;
  mv: number | null;
  missing: boolean;
  warm: boolean;
  local: boolean;
  spark: number[];
  ana: { model: string; note: string; gases: GasReading[]; ratio: number | null; warming: boolean } | null;
}

export interface Repeater {
  id: string;
  online: boolean;
  age: number;
  gateway: boolean;
  hop: number;
  parent: string;
  path: string[];
  rssi: number | null;
  prssi: number | null;
  nbrs: number;
  buzzing: boolean;
  sos: boolean;
  disp: boolean;
  gcode: number;
  gid: number;
  ip: string;
  uptime: number;
  gas_level: number;
  gas_why: string[];
  gas_missing: boolean;
  gas_warm: boolean;
  gas_chs: GasChannel[];
  air_t: number | null;
  air_h: number | null;
  air_wb: number | null;
  air_level: number;
  air_why: string[];
  air_missing: boolean;
  air_spark: [number, number][];
  via_mesh: boolean;
}

export interface MapCfg {
  image: string | null;
  img_w: number;
  img_h: number;
  ox: number;
  oy: number;
  ppm: number;
  rev: number;
  repeaters: Record<string, { x: number; y: number; z: number; face: number | null }>;
  tunnels: [number, number][][];
  exits: { name: string; x: number; y: number }[];
}

export interface Position {
  x: number | null;
  y: number | null;
  z: number | null;
  acc: number | null;
  pdr: boolean;
  src: string;
  fix_rep: string | null;
  fix_age: number | null;
  walked: number;
  trail: [number, number][];
}

export interface Hazard { x: number; y: number; r: number; why: string; t?: number }

export interface Evac {
  active: boolean;
  by: string;
  msg: string;
  since_clock: string | null;
  hazards: Hazard[];
  guide: Record<string, { code: number; dist: number }>;
  cfg: { auto_gas: boolean; radius_m: number };
}

export interface Route { dist: number; exit: string; hazard: boolean; path: [number, number][]; via: string[] }

export interface Verification {
  id: string;
  time: string;
  photo: string;
  body_id: string;
  worker_id: string;
  worker: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  source: string;
  gear_ok: string[];
  scans: { gear: string; uid: string; check: string; time?: string }[];
  worker_status?: string;
  ai: { ok: boolean; verdict?: string; missing?: string[]; complete?: boolean; note?: string; error?: string;
        items?: Record<string, { found: boolean }> } | null;
}

export interface Incident { time: string; body_id: string; name: string; from: Status; to: Status; why: string; t: number }
export interface AlertLog { time: string; action: string; target: string; msg: string }

export interface HubState {
  clock: string;
  now: number;
  summary: Record<Status, number>;
  workers: Worker[];
  repeaters: Repeater[];
  positions: Record<string, Position>;
  routes: Record<string, Route>;
  map: MapCfg;
  map_start: number;
  evac: Evac;
  alert: { id: number; level: number; target: string; msg: string; time: number | null };
  alert_log: AlertLog[];
  incidents: Incident[];
  verifications: Verification[];
  cleared: Record<string, { worker: string; worker_id: string; gear: string[]; time: string; photo: string }>;
  gear_list: string[];
  kit_names: Record<string, string>;
  pending_scans: number;
  unknown: { body_id: string; status: Status; reasons: string[]; live: Live | null }[];
  limits: Record<string, number>;
  gas_limits: Record<string, { name: string; warn: number; danger: number; unit: string; src: string }>;
  events: { time: string; station: string; event: string; gear?: string; uid?: string; check?: string }[];
  ai: { state: string; detail: string };
}

/** Where the hub is. Same address as the page by default (the hub serves this app);
 *  for a separately hosted dashboard set ?hub=https://your-server or VITE_HUB_URL. */
function hubBase(): string {
  const q = new URLSearchParams(location.search).get('hub');
  if (q) {
    try { localStorage.setItem('minesafe.hub', q); } catch { /* private mode */ }
    return q.replace(/\/$/, '');
  }
  try {
    const saved = localStorage.getItem('minesafe.hub');
    if (saved) return saved.replace(/\/$/, '');
  } catch { /* ignore */ }
  return (import.meta.env.VITE_HUB_URL ?? '').replace(/\/$/, '');
}
export const HUB = hubBase();
export const hubUrl = (p: string) => `${HUB}${p}`;

export async function getState(signal?: AbortSignal): Promise<HubState> {
  const r = await fetch(hubUrl('/api/state'), { cache: 'no-store', signal });
  if (!r.ok) throw new Error(`Hub answered ${r.status}`);
  return r.json();
}

export interface History { t: number[]; temp: (number | null)[]; hr: (number | null)[]; amag: number[]; gmag: number[] }
export async function getHistory(bid: string): Promise<History> {
  const r = await fetch(hubUrl(`/api/worker/${encodeURIComponent(bid)}/history?n=300`), { cache: 'no-store' });
  if (!r.ok) throw new Error(`Hub answered ${r.status}`);
  return r.json();
}

export async function post(path: string, body: unknown = {}): Promise<{ ok: boolean; error?: string }> {
  try {
    const r = await fetch(hubUrl(path), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok || j.ok === false) return { ok: false, error: j.error ?? `Hub answered ${r.status}` };
    return { ok: true };
  } catch (e) {
    return { ok: false, error: `Can't reach the hub (${(e as Error).message})` };
  }
}

export const actions = {
  alert: (target: string, msg: string) => post('/api/alert', { target, msg }),
  clearAlert: () => post('/api/alert/clear'),
  startEvac: (msg: string) => post('/api/evac', { action: 'start', msg }),
  stopEvac: () => post('/api/evac', { action: 'stop' }),
  addHazard: (x: number, y: number, r: number, why: string) => post('/api/evac', { action: 'hazard', x, y, r, why }),
  removeHazard: (i: number) => post('/api/evac', { action: 'remove_hazard', i }),
  verify: (id: string, action: 'approve' | 'reject', worker: string, worker_id: string, body_id: string, gear: string[]) =>
    post(`/api/verify/${id}`, { action, worker, worker_id, body_id, gear }),
  revoke: (bid: string) => post(`/api/revoke/${encodeURIComponent(bid)}`),
};
