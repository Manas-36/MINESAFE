import { useEffect, useState } from 'react';
import { actions, getHistory, type History, type HubState, type Repeater, type Worker } from '../api';
import { AlertDialog } from '../components/chrome';
import { Bars, Spark, StatusPill } from '../components/common';
import { IClose, IFocus } from '../components/icons';
import { useStore } from '../store';
import { COLOR, ago, fmt, gasValue, levelColor, mainGases, repeaterLevel, signText } from '../util';

function Head({ title, sub, pill, onFocus }: { title: string; sub?: string; pill?: React.ReactNode; onFocus?: () => void }) {
  const { select } = useStore();
  return (
    <div className="detail-head">
      <div style={{ minWidth: 0 }}>
        <h3>{title}</h3>
        {sub && <div className="muted" style={{ fontSize: 13 }}>{sub}</div>}
        {pill && <div style={{ marginTop: 6 }}>{pill}</div>}
      </div>
      <span className="x" style={{ display: 'flex', gap: 6 }}>
        {onFocus && <button className="btn sm ghost" onClick={onFocus} aria-label="Centre the 3D view on this"><IFocus /></button>}
        <button className="btn sm ghost" onClick={() => select(null)} aria-label="Close details"><IClose /></button>
      </span>
    </div>
  );
}

/* ---------------- worker ---------------- */
export function WorkerDetail({ s, w, onFocus }: { s: HubState; w: Worker; onFocus?: () => void }) {
  const [hist, setHist] = useState<History | null>(null);
  const [dlg, setDlg] = useState(false);
  useEffect(() => {
    let stop = false;
    const load = () => getHistory(w.body_id).then((h) => !stop && setHist(h)).catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => { stop = true; clearInterval(t); };
  }, [w.body_id]);
  const L = w.live;
  const lim = s.limits;
  const pos = s.positions[w.body_id];
  const route = s.routes[w.body_id];
  const tCls = L?.temp == null ? '' : L.temp >= lim.temp_danger_hi ? 'bad' : L.temp >= lim.temp_warn_hi || L.temp <= lim.temp_warn_lo ? 'warn' : '';
  const hCls = L?.hr == null ? '' : L.hr >= lim.hr_danger_hi || L.hr <= lim.hr_danger_lo ? 'bad' : L.hr >= lim.hr_warn_hi || L.hr <= lim.hr_warn_lo ? 'warn' : '';
  const sCls = L?.spo2 == null ? '' : L.spo2 <= lim.spo2_danger ? 'bad' : L.spo2 <= lim.spo2_warn ? 'warn' : '';
  const sig = L ? (L.age >= lim.signal_danger_s ? 'bad' : L.age >= lim.signal_warn_s ? 'warn' : '') : 'bad';
  return (
    <>
      <Head title={w.name || w.body_id} sub={[w.body_id, w.work, w.zone].filter(Boolean).join(' · ')} pill={<StatusPill st={w.status} />} onFocus={onFocus} />
      {w.reasons.length > 0 && (
        <div className="reasons">{w.reasons.map((r) => <span key={r} className={`reason${w.status === 'WARNING' ? ' w' : ''}`}>{r}</span>)}</div>
      )}
      <div className="vitals">
        <div className="vital"><small>Body temp</small><span className={`num ${tCls}`}>{fmt(L?.temp, 1, ' °C')}</span></div>
        <div className="vital"><small>Heart rate</small><span className={`num ${hCls}`}>{L?.hr ? `${L.hr}` : '–'}</span>{L?.hr ? <small>bpm</small> : null}</div>
        <div className="vital"><small>SpO₂</small><span className={`num ${sCls}`}>{L?.spo2 ? `${L.spo2} %` : '–'}</span></div>
        <div className="vital"><small>Last packet</small><span className={`num ${sig}`}>{L ? ago(L.age) : 'never'}</span></div>
      </div>
      <div className="actions">
        <button className="btn redline" onClick={() => setDlg(true)}>Alert this worker</button>
        {w.contact_phone && <a className="btn ghost" href={`tel:${w.contact_phone}`}>Call {w.contact_name || 'contact'}</a>}
      </div>
      {dlg && <AlertDialog target={w.body_id} onClose={() => setDlg(false)} />}

      <div className="card">
        <h3 style={{ marginBottom: 8 }}>Where</h3>
        <dl className="kv">
          <dt>Nearest repeater</dt><dd>{L?.near ? <><span className="mono">{L.near}</span> <Bars rssi={L.near_rssi} /> {L.near_rssi} dBm</> : '–'}</dd>
          <dt>Radio path</dt><dd className="mono" style={{ fontSize: 13 }}>{L?.path?.length ? `${w.body_id} → ${L.path.join(' → ')} → hub` : '–'}</dd>
          <dt>Position</dt><dd>{pos && pos.x !== null ? `x ${fmt(pos.x, 1)} · y ${fmt(pos.y, 1)} m${pos.z ? ` · level ${fmt(pos.z, 1)} m` : ''}` : 'not on the map yet'}</dd>
          <dt>Tracking</dt><dd>{pos?.src ?? '–'}{pos?.fix_rep ? `, last checked at ${pos.fix_rep} ${ago(pos.fix_age)}` : ''}</dd>
          <dt>Walked</dt><dd>{pos ? `${Math.round(pos.walked)} m · ${L?.steps ?? 0} steps` : '–'}</dd>
          <dt>Nearest exit</dt><dd>{route ? <>{route.exit}, {route.dist} m{route.via.length ? ` via ${route.via.join(', ')}` : ''}{route.hazard ? <b style={{ color: COLOR.danger }}> · passes a danger zone</b> : null}</> : s.map.exits.length ? '–' : 'no exits on the map'}</dd>
        </dl>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 8 }}>Last few minutes</h3>
        <div style={{ display: 'grid', gap: 8 }}>
          <div className="chartbox"><small>Body temperature (°C)</small>
            <Spark values={hist?.temp ?? []} warn={lim.temp_warn_hi} danger={lim.temp_danger_hi} color={COLOR.ink} /></div>
          <div className="chartbox"><small>Heart rate (bpm)</small>
            <Spark values={hist?.hr ?? []} warn={lim.hr_warn_hi} danger={lim.hr_danger_hi} color={COLOR.ink} /></div>
          <div className="chartbox"><small>Movement (g) — flat at 1.0 means not moving</small>
            <Spark values={hist?.amag ?? []} color={COLOR.amber} /></div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 8 }}>Medical card</h3>
        <dl className="kv">
          <dt>Blood group</dt><dd><b>{w.blood || '–'}</b></dd>
          <dt>Allergies</dt><dd>{w.allergies || 'none recorded'}</dd>
          <dt>Conditions</dt><dd>{w.conditions || 'none recorded'}</dd>
          <dt>Medication</dt><dd>{w.medication || 'none recorded'}</dd>
          <dt>Emergency contact</dt><dd>{w.contact_name || '–'} {w.contact_phone && <a href={`tel:${w.contact_phone}`}>{w.contact_phone}</a>}</dd>
          <dt>Employee ID</dt><dd>{w.emp_id || '–'}</dd>
          <dt>Entry check</dt><dd>{w.cleared ? `cleared at ${w.cleared.time}${w.cleared.gear?.length ? ` · ${w.cleared.gear.join(', ').toLowerCase()}` : ''}` : 'not cleared today'}</dd>
          {w.notes && <><dt>Notes</dt><dd>{w.notes}</dd></>}
        </dl>
      </div>
    </>
  );
}

/* ---------------- repeater ---------------- */
export function RepeaterDetail({ s, id, r, onFocus }: { s: HubState; id: string; r: Repeater | undefined; onFocus?: () => void }) {
  const { toast } = useStore();
  const pos = s.map.repeaters[id];
  const lvl = r ? repeaterLevel(r) : -1;
  const guide = s.evac.guide[id];
  const sign = guide && s.evac.active ? signText(guide.code, guide.dist) : null;
  const hearing = s.workers.filter((w) => w.live?.near === id);
  const mark = async () => {
    if (!pos) return;
    const res = await actions.addHazard(pos.x, pos.y, s.evac.cfg.radius_m, `marked at ${id}`);
    toast(res.ok ? `Danger zone added at ${id} — routes now avoid it` : `Not added: ${res.error}`, !res.ok);
  };
  return (
    <>
      <Head title={id} sub={r ? (r.gateway ? 'Main repeater · Wi-Fi to the hub' : `${r.hop} hop${r.hop === 1 ? '' : 's'} from the main repeater`) : 'Placed on the map, never heard'}
        pill={r ? <StatusPill st={!r.online ? 'OFF' : lvl >= 2 ? 'DANGER' : lvl === 1 ? 'WARNING' : 'SAFE'}>{!r.online ? `Offline · ${ago(r.age)}` : lvl >= 2 ? 'Danger' : lvl === 1 ? 'Warning' : 'Normal'}</StatusPill> : <StatusPill st="OFF">Not heard</StatusPill>}
        onFocus={onFocus} />
      {r && [...r.gas_why, ...r.air_why].length > 0 && (
        <div className="reasons">{[...r.gas_why, ...r.air_why].map((x) => <span key={x} className={`reason${lvl < 2 ? ' w' : ''}`}>{x}</span>)}</div>
      )}
      {r?.sos && <div className="reasons"><span className="reason">SOS button pressed at this repeater</span></div>}
      <div className="actions">
        <button className="btn redline" onClick={mark}>Mark danger zone here</button>
      </div>
      {r && <GasCard r={r} />}
      <div className="card">
        <h3 style={{ marginBottom: 8 }}>Exit sign and buzzer</h3>
        <dl className="kv">
          <dt>Sign shows</dt><dd>{sign ? <b style={{ color: '#FF9F1A' }}>{`${sign.arrow} ${sign.text}`.trim()}</b> : s.evac.active ? 'no instruction yet' : 'its name (normal)'}</dd>
          <dt>Sign confirmed</dt><dd>{r ? (r.disp ? (s.evac.active ? (r.gid ? 'yes, showing the latest route' : 'not yet') : 'display fitted') : 'no display fitted') : '–'}</dd>
          <dt>Buzzer</dt><dd>{r?.buzzing ? <b style={{ color: COLOR.danger }}>sounding</b> : 'quiet'}</dd>
        </dl>
      </div>
      <div className="card">
        <h3 style={{ marginBottom: 8 }}>Radio</h3>
        <dl className="kv">
          <dt>Route to hub</dt><dd className="mono" style={{ fontSize: 13 }}>{r?.path?.length ? `${r.path.join(' → ')} → hub` : '–'}</dd>
          <dt>Link</dt><dd>{r?.gateway ? <>Wi-Fi <Bars rssi={r.rssi} /> {r.rssi} dBm</> : r?.prssi != null ? <>to {r.parent} <Bars rssi={r.prssi} /> {r.prssi} dBm</> : '–'}</dd>
          <dt>Neighbours</dt><dd>{r?.nbrs ?? '–'}</dd>
          <dt>Last report</dt><dd>{r ? ago(r.age) : 'never'}</dd>
          <dt>Workers near</dt><dd>{hearing.length ? hearing.map((w) => w.name).join(', ') : 'none'}</dd>
        </dl>
      </div>
    </>
  );
}

export function GasCard({ r, bare }: { r: Repeater; bare?: boolean }) {
  const gases = mainGases(r);
  return (
    <div className={bare ? '' : 'card'}>
      {!bare && <h3 style={{ marginBottom: 6 }}>Gas and air</h3>}
      {r.gas_missing && <div className="muted">No gas sensor reading.</div>}
      {r.gas_warm && <div className="muted">Gas sensors warming up — readings settle in about a minute.</div>}
      {gases.map((g) => {
        const pct = g.ppm == null ? 0 : Math.min(100, (g.ppm / (g.danger * 1.25)) * 100);
        const wPct = (g.warn / (g.danger * 1.25)) * 100, dPct = 80;
        const col = levelColor(g.level);
        return (
          <div className="gasrow" key={`${g.ch}-${g.key}`}>
            <span>{g.name} <span className="muted" style={{ fontSize: 12 }}>{g.model}</span></span>
            <b className="num" style={{ color: g.level ? col : COLOR.ink, fontSize: 17 }}>{gasValue(g.ppm, g.unit)}</b>
            <span className="bar" aria-hidden><i style={{ width: `${pct}%`, background: col }} /><em style={{ left: `${wPct}%` }} /><em style={{ left: `${dPct}%`, background: '#FF4D4FAA' }} /></span>
            <small className="muted" style={{ gridColumn: '1 / -1', fontSize: 12 }}>warning {gasValue(g.warn, g.unit)} · danger {gasValue(g.danger, g.unit)}</small>
          </div>
        );
      })}
      {!r.air_missing && (
        <div className="air">
          <div><small>Air</small><span className="num" style={{ fontSize: 18 }}>{fmt(r.air_t, 1, ' °C')}</span></div>
          <div><small>Humidity</small><span className="num" style={{ fontSize: 18 }}>{fmt(r.air_h, 0, ' %')}</span></div>
          <div><small>Wet-bulb</small><span className="num" style={{ fontSize: 18, color: r.air_level ? levelColor(r.air_level) : undefined }}>{fmt(r.air_wb, 1, ' °C')}</span></div>
        </div>
      )}
    </div>
  );
}

export function ExitDetail({ s, name }: { s: HubState; name: string }) {
  const e = s.map.exits.find((x) => x.name === name);
  const using = Object.entries(s.routes).filter(([, r]) => r.exit === name);
  return (
    <>
      <Head title={name} sub="Exit" />
      <dl className="kv">
        <dt>Position</dt><dd>{e ? `x ${e.x} · y ${e.y} m` : '–'}</dd>
        <dt>Nearest exit for</dt><dd>{using.length ? using.map(([b, r]) => `${s.workers.find((w) => w.body_id === b)?.name ?? b} (${r.dist} m)`).join(', ') : 'nobody right now'}</dd>
      </dl>
    </>
  );
}

export function HazardDetail({ s, i }: { s: HubState; i: number }) {
  const { toast, select } = useStore();
  const h = s.evac.hazards[i];
  if (!h) return null;
  return (
    <>
      <Head title="Danger zone" sub={h.why} />
      <dl className="kv"><dt>Centre</dt><dd>x {fmt(h.x, 0)} · y {fmt(h.y, 0)} m</dd><dt>Radius</dt><dd>{h.r} m</dd></dl>
      <div className="actions">
        <button className="btn" onClick={async () => {
          const r = await actions.removeHazard(i);
          toast(r.ok ? 'Danger zone removed' : `Not removed: ${r.error}`, !r.ok);
          if (r.ok) select(null);
        }}>Remove danger zone</button>
      </div>
    </>
  );
}
