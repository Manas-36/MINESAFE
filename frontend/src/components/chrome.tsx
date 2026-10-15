import { useState, type JSX } from 'react';
import { actions } from '../api';
import { useStore, type Page } from '../store';
import { COLOR, byStatus } from '../util';
import { Modal } from './common';
import { IBell, IEntry, IExit, IGas, ILog, IMine, INetwork, ISetup, IWorkers } from './icons';

const LOGO = `${import.meta.env.BASE_URL}logo_icon.png`;

export function Brand() {
  return (
    <a className="brand" href="#/mine" aria-label="MineSafe control, home">
      <span className="badge"><img src={LOGO} alt="" /></span>
      <span>
        <span className="brand-name">Mine<span>Safe</span></span>
        <span className="brand-sub" style={{ display: 'block' }}>Control room</span>
      </span>
    </a>
  );
}

export function TopBar() {
  const { s, staleMs, error } = useStore();
  const [dlg, setDlg] = useState<'alert' | 'evac' | 'endEvac' | null>(null);
  const live = staleMs < 3500;
  const sum = s?.summary;
  const evac = s?.evac.active;
  return (
    <header className="top">
      <Brand />
      {sum && (
        <div className="counts" aria-label="Workers by status">
          <span className="count"><i className="dot" style={{ background: COLOR.danger }} /> <b>{sum.DANGER}</b> danger</span>
          <span className="count"><i className="dot" style={{ background: COLOR.warn }} /> <b>{sum.WARNING}</b> warning</span>
          <span className="count"><i className="dot" style={{ background: COLOR.safe }} /> <b>{sum.SAFE}</b> safe</span>
          <span className="count c-nodata"><i className="dot" style={{ background: COLOR.nodata }} /> <b>{sum['NO DATA']}</b> no data</span>
        </div>
      )}
      <span className="spacer" />
      <span className={`conn${live ? '' : ' bad'}`} title={error ?? ''}>
        <i className="dot" style={{ background: live ? COLOR.safe : COLOR.danger }} />
        <span className="t">{live ? `Hub live · ${s?.clock ?? ''}` : 'Hub not answering'}</span>
      </span>
      <button className="btn redline" onClick={() => setDlg('alert')} disabled={!s}><IBell /><span className="lbl">Alert</span></button>
      {evac
        ? <button className="btn" onClick={() => setDlg('endEvac')}><IExit /><span className="lbl">End evacuation</span></button>
        : <button className="btn red" onClick={() => setDlg('evac')} disabled={!s}><IExit /><span className="lbl">Evacuate</span></button>}
      {dlg === 'alert' && <AlertDialog onClose={() => setDlg(null)} />}
      {dlg === 'evac' && <EvacDialog onClose={() => setDlg(null)} />}
      {dlg === 'endEvac' && <EndEvacDialog onClose={() => setDlg(null)} />}
    </header>
  );
}

export function AlertDialog({ onClose, target: t0 = '*' }: { onClose: () => void; target?: string }) {
  const { s, toast } = useStore();
  const [target, setTarget] = useState(t0);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const send = async () => {
    setBusy(true);
    const r = await actions.alert(target, msg.trim());
    setBusy(false);
    if (r.ok) { toast(target === '*' ? 'Alert sent to every worker' : `Alert sent to ${target}`); onClose(); }
    else toast(`Alert not sent: ${r.error}`, true);
  };
  return (
    <Modal title="Send an alert" onClose={onClose} danger>
      <p>Every repeater buzzer sounds and the body unit LED, screen and vibration come on. Workers see it within about a second.</p>
      <label className="f">Who
        <select className="input" value={target} onChange={(e) => setTarget(e.target.value)}>
          <option value="*">All workers</option>
          {[...(s?.workers ?? [])].sort(byStatus).map((w) => <option key={w.body_id} value={w.body_id}>{w.name} ({w.body_id})</option>)}
        </select>
      </label>
      <label className="f">Message for the log (optional)
        <input className="input" value={msg} maxLength={80} placeholder="e.g. Gas at REP-03, leave the area" onChange={(e) => setMsg(e.target.value)} />
      </label>
      <div className="actions">
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn red" onClick={send} disabled={busy}><IBell />{busy ? 'Sending…' : 'Send alert'}</button>
      </div>
    </Modal>
  );
}

export function EvacDialog({ onClose }: { onClose: () => void }) {
  const { s, toast } = useStore();
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const exits = s?.map.exits.length ?? 0;
  const go = async () => {
    setBusy(true);
    const r = await actions.startEvac(msg.trim());
    setBusy(false);
    if (r.ok) { toast('Evacuation started'); onClose(); } else toast(`Evacuation not started: ${r.error}`, true);
  };
  return (
    <Modal title="Start evacuation" onClose={onClose} danger>
      <p>All workers are alerted. Every exit sign switches to the direction and distance of the safest exit, avoiding the danger zones on the map.</p>
      {exits === 0 && <p style={{ color: COLOR.warn }}>No exits are marked on the map yet, so the signs can't point anywhere. Add exits on the setup page (Map tab).</p>}
      <label className="f">Reason (shown in the banner and log)
        <input className="input" value={msg} maxLength={60} placeholder="e.g. Methane leak near REP-03" onChange={(e) => setMsg(e.target.value)} />
      </label>
      <div className="actions">
        <button className="btn ghost" onClick={onClose}>Cancel</button>
        <button className="btn red" onClick={go} disabled={busy}><IExit />{busy ? 'Starting…' : 'Start evacuation'}</button>
      </div>
    </Modal>
  );
}

export function EndEvacDialog({ onClose }: { onClose: () => void }) {
  const { toast } = useStore();
  const [busy, setBusy] = useState(false);
  const go = async () => {
    setBusy(true);
    const r = await actions.stopEvac();
    setBusy(false);
    if (r.ok) { toast('Evacuation ended'); onClose(); } else toast(`Couldn't end the evacuation: ${r.error}`, true);
  };
  return (
    <Modal title="End evacuation?" onClose={onClose}>
      <p>The alert clears, buzzers stop and the exit signs go back to normal. Danger zones stay on the map until you remove them.</p>
      <div className="actions">
        <button className="btn ghost" onClick={onClose}>Keep evacuating</button>
        <button className="btn amber" onClick={go} disabled={busy}>{busy ? 'Ending…' : 'End evacuation'}</button>
      </div>
    </Modal>
  );
}

export function Banners() {
  const { s, staleMs, error, toast } = useStore();
  const [busy, setBusy] = useState(false);
  const [endDlg, setEndDlg] = useState(false);
  if (!s) return <div className="banners" />;
  const out = [];
  if (staleMs > 3500) {
    out.push(
      <div className="banner offline" key="off">
        <span className="what" style={{ background: 'transparent', textShadow: 'none' }}>Hub not answering</span>
        <span>{error ?? 'No data'} · showing the last data received. Check that admin_hub.py is running and this device is on the same network.</span>
      </div>,
    );
  }
  if (s.evac.active) {
    const reps = Object.keys(s.map.repeaters).length;
    const lit = s.repeaters.filter((r) => r.online && r.gid && r.gcode).length;
    out.push(
      <div className="banner evac" key="evac" role="alert">
        <span className="what">Evacuation in progress</span>
        <span className="detail">{s.evac.msg || 'Follow the exit signs'}{s.evac.since_clock ? ` · since ${s.evac.since_clock}` : ''}</span>
        <span className="detail">Exit signs updated {lit}/{reps} · danger zones {s.evac.hazards.length}</span>
        <button className="btn" onClick={() => setEndDlg(true)}>End evacuation</button>
        {endDlg && <EndEvacDialog onClose={() => setEndDlg(false)} />}
      </div>,
    );
  } else if (s.alert.level) {
    const buzz = s.repeaters.filter((r) => r.online && r.buzzing).length;
    const online = s.repeaters.filter((r) => r.online).length;
    const leds = s.workers.filter((w) => w.live && (w.live.fl & 64)).length;
    const who = s.alert.target === '*' ? 'All workers' : s.alert.target;
    out.push(
      <div className="banner alert" key="alert" role="alert">
        <span className="what">Alert active</span>
        <span className="detail">{who}{s.alert.msg ? ` · ${s.alert.msg}` : ''}</span>
        <span className="detail">Buzzers {buzz}/{online} · body units confirmed {leds}</span>
        <button className="btn" disabled={busy} onClick={async () => {
          setBusy(true);
          const r = await actions.clearAlert();
          setBusy(false);
          toast(r.ok ? 'Alert cleared' : `Couldn't clear: ${r.error}`, !r.ok);
        }}>Clear alert</button>
      </div>,
    );
  }
  return <div className="banners">{out}</div>;
}

const NAV: { p: Page; label: string; icon: () => JSX.Element }[] = [
  { p: 'mine', label: 'Mine', icon: IMine },
  { p: 'workers', label: 'Workers', icon: IWorkers },
  { p: 'gas', label: 'Gas & air', icon: IGas },
  { p: 'network', label: 'Network', icon: INetwork },
  { p: 'entry', label: 'Entry', icon: IEntry },
  { p: 'log', label: 'Log', icon: ILog },
];

export function Rail() {
  const { s, page, go } = useStore();
  const pips: Partial<Record<Page, { n: number; warn?: boolean }>> = {};
  if (s) {
    const d = s.summary.DANGER, w = s.summary.WARNING;
    if (d || w) pips.workers = { n: d || w, warn: !d };
    const g = s.repeaters.filter((r) => r.online && Math.max(r.gas_level, r.air_level) > 0);
    if (g.length) pips.gas = { n: g.length, warn: !g.some((r) => Math.max(r.gas_level, r.air_level) >= 2) };
    const off = s.repeaters.filter((r) => !r.online).length;
    if (off) pips.network = { n: off, warn: true };
    const pend = s.verifications.filter((v) => v.status === 'PENDING').length;
    if (pend) pips.entry = { n: pend, warn: true };
  }
  return (
    <nav className="rail" aria-label="Pages">
      {NAV.map(({ p, label, icon: I }) => (
        <button key={p} className={page === p ? 'on' : ''} onClick={() => go(p)} aria-current={page === p ? 'page' : undefined}>
          <I />{label}
          {pips[p] && <span className={`pip${pips[p]!.warn ? ' warn' : ''}`}>{pips[p]!.n}</span>}
        </button>
      ))}
      <a className="setup" href="/" title="Register workers, draw the map, set limits, calibrate sensors"><ISetup />Setup</a>
    </nav>
  );
}

