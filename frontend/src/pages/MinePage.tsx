import { lazy, Suspense, useMemo, useState } from 'react';
import type { HubState } from '../api';
import { StatusPill } from '../components/common';
import { ICheck } from '../components/icons';
import { ExitDetail, HazardDetail, RepeaterDetail, WorkerDetail } from '../panels/Details';
import { useStore } from '../store';
import { COLOR, byStatus, gasValue, mainGases, repeaterLevel } from '../util';
import type { SceneOpts, View } from '../scene/Mine3D';

const Mine3D = lazy(() => import('../scene/Mine3D'));

function load<T>(k: string, d: T): T {
  try { const v = localStorage.getItem(k); return v ? { ...d, ...JSON.parse(v) } : d; } catch { return d; }
}

export default function MinePage() {
  const { s, sel } = useStore();
  const [view, setView] = useState<View>('iso');
  const [fitKey, setFitKey] = useState(0);
  const [opts, setOpts] = useState<SceneOpts>(() => load('minesafe.scene', { labels: window.innerWidth > 820, plan: true, routes: true, trails: true }));
  const [focus, setFocus] = useState<[number, number] | null>(null);
  const toggle = (k: keyof SceneOpts) => setOpts((o) => {
    const n = { ...o, [k]: !o[k] };
    try { localStorage.setItem('minesafe.scene', JSON.stringify(n)); } catch { /* ignore */ }
    return n;
  });
  if (!s) return null;
  const hasMap = s.map.tunnels.length > 0 || Object.keys(s.map.repeaters).length > 0;
  const focusOn = (x: number | null | undefined, y: number | null | undefined) => () => { if (x != null && y != null) setFocus([x + Math.random() * 1e-6, y]); };

  return (
    <div className="mine">
      <div className="stage">
        {hasMap ? (
          <Suspense fallback={<div className="nomap"><div className="muted">Building the 3D mine…</div></div>}>
            <Mine3D s={s} view={view} fitKey={fitKey} opts={opts} focus={focus} />
          </Suspense>
        ) : (
          <div className="nomap"><div>
            <h2>No mine map yet</h2>
            <p className="muted">Draw the tunnels, place the repeaters and mark the exits on the setup page (Map tab). The 3D mine is built from that map and appears here straight away.</p>
            <a className="btn amber" href="/#map">Open map setup</a>
          </div></div>
        )}
        <Kpis s={s} />
        {hasMap && (
          <div className="overlay-bl">
            <div className="seg" role="group" aria-label="Camera">
              <button className={view === 'iso' ? 'on' : ''} onClick={() => { setView('iso'); setFitKey((k) => k + 1); }}>3D</button>
              <button className={view === 'top' ? 'on' : ''} onClick={() => { setView('top'); setFitKey((k) => k + 1); }}>Top</button>
              <button onClick={() => setFitKey((k) => k + 1)}>Fit</button>
            </div>
            <div className="seg" role="group" aria-label="Show on the map">
              {([['labels', 'Names'], ['plan', 'Plan'], ['routes', 'Routes'], ['trails', 'Trails']] as const).map(([k, l]) => (
                <button key={k} className={opts[k] ? 'on' : ''} aria-pressed={opts[k]} onClick={() => toggle(k)}>{l}</button>
              ))}
            </div>
          </div>
        )}
        {hasMap && (
          <div className="legend" aria-label="Legend">
            <span><i className="dot" style={{ background: COLOR.safe }} />Safe</span>
            <span><i className="dot" style={{ background: COLOR.warn }} />Warning</span>
            <span><i className="dot" style={{ background: COLOR.danger }} />Danger</span>
            <span><i className="dot" style={{ background: COLOR.nodata }} />No data / offline</span>
            <span><i style={{ width: 14, height: 3, background: COLOR.safe, display: 'inline-block' }} />Route to exit</span>
          </div>
        )}
      </div>
      <aside className="side" aria-label={sel ? 'Details' : 'Needs attention'}>
        <div className="side-in">
          {sel ? <Selected s={s} focus={focusOn} /> : <Attention s={s} />}
        </div>
      </aside>
    </div>
  );
}

function Kpis({ s }: { s: HubState }) {
  const total = s.workers.length;
  const onMap = s.workers.filter((w) => w.live && w.live.age < 60).length;
  const online = s.repeaters.filter((r) => r.online).length;
  const placed = Object.keys(s.map.repeaters).length;
  let worst: { name: string; v: string; at: string; level: number } | null = null;
  for (const r of s.repeaters) {
    if (!r.online) continue;
    for (const g of mainGases(r)) {
      const frac = g.ppm == null ? 0 : g.ppm / g.danger;
      if (!worst || g.level > worst.level || (g.level === worst.level && frac > (worst as unknown as { f: number }).f)) {
        worst = Object.assign({ name: g.key, v: gasValue(g.ppm, g.unit), at: r.id, level: g.level }, { f: frac });
      }
    }
  }
  return (
    <div className="overlay-tl">
      <div className="chip"><small>Workers sending data</small><span className="num">{onMap}</span><span className="muted"> / {total}</span></div>
      <div className="chip"><small>Repeaters online</small><span className="num" style={{ color: online < Math.max(placed, s.repeaters.length) ? COLOR.warn : undefined }}>{online}</span><span className="muted"> / {Math.max(placed, s.repeaters.length)}</span></div>
      {worst && (
        <div className="chip"><small>Highest gas · {worst.at}</small><span className="num" style={{ color: worst.level >= 2 ? COLOR.danger : worst.level === 1 ? COLOR.warn : undefined }}>{worst.name} {worst.v}</span></div>
      )}
    </div>
  );
}

function Selected({ s, focus }: { s: HubState; focus: (x: number | null | undefined, y: number | null | undefined) => () => void }) {
  const { sel } = useStore();
  if (!sel) return null;
  if (sel.kind === 'worker') {
    const w = s.workers.find((x) => x.body_id === sel.id);
    const u = s.unknown.find((x) => x.body_id === sel.id);
    const p = s.positions[sel.id];
    if (w) return <WorkerDetail s={s} w={w} onFocus={focus(p?.x, p?.y)} />;
    if (u) return (
      <div className="card"><h3>{u.body_id}</h3><p className="muted">This body unit is sending data but isn't registered to a worker. Register it on the setup page (Register workers) so the control room knows who is wearing it.</p>
        <a className="btn amber" href="/#workers">Register this unit</a></div>
    );
    return <div className="muted">This worker is no longer in the list.</div>;
  }
  if (sel.kind === 'repeater') {
    const p = s.map.repeaters[sel.id];
    return <RepeaterDetail s={s} id={sel.id} r={s.repeaters.find((r) => r.id === sel.id)} onFocus={focus(p?.x, p?.y)} />;
  }
  if (sel.kind === 'exit') return <ExitDetail s={s} name={sel.id} />;
  if (sel.kind === 'hazard') return <HazardDetail s={s} i={+sel.id} />;
  return null;
}

function Attention({ s }: { s: HubState }) {
  const { select, go } = useStore();
  const items = useMemo(() => {
    const out: { key: string; level: number; title: string; why: string; onClick: () => void; st: 'DANGER' | 'WARNING' | 'OFF' | 'INFO' }[] = [];
    for (const w of [...s.workers].sort(byStatus)) {
      if (w.status === 'DANGER' || w.status === 'WARNING') {
        out.push({ key: w.body_id, level: w.status === 'DANGER' ? 2 : 1, st: w.status, title: w.name, why: w.reasons.join(' · ') || w.status, onClick: () => select({ kind: 'worker', id: w.body_id }) });
      }
    }
    s.evac.hazards.forEach((h, i) => out.push({ key: `hz${i}`, level: 2, st: 'DANGER', title: 'Danger zone', why: h.why, onClick: () => select({ kind: 'hazard', id: String(i) }) }));
    for (const r of s.repeaters) {
      const l = repeaterLevel(r);
      if (r.sos) out.push({ key: r.id + 'sos', level: 2, st: 'DANGER', title: `SOS at ${r.id}`, why: 'Someone pressed the SOS button on this repeater', onClick: () => select({ kind: 'repeater', id: r.id }) });
      else if (l >= 1) out.push({ key: r.id, level: l, st: l >= 2 ? 'DANGER' : 'WARNING', title: r.id, why: [...r.gas_why, ...r.air_why].join(' · ') || 'Gas or air above the limit', onClick: () => select({ kind: 'repeater', id: r.id }) });
      else if (!r.online) out.push({ key: r.id, level: 0.5, st: 'OFF', title: `${r.id} offline`, why: 'No report from this repeater — check its power', onClick: () => select({ kind: 'repeater', id: r.id }) });
    }
    for (const u of s.unknown || []) out.push({ key: u.body_id, level: 0.4, st: 'INFO', title: `${u.body_id} not registered`, why: 'Sending data but not linked to a worker', onClick: () => select({ kind: 'worker', id: u.body_id }) });
    const pend = s.verifications.filter((v) => v.status === 'PENDING').length;
    if (pend) out.push({ key: 'entry', level: 0.3, st: 'INFO', title: `${pend} entry check${pend > 1 ? 's' : ''} waiting`, why: 'Approve or reject at the gate', onClick: () => go('entry') });
    return out.sort((a, b) => b.level - a.level);
  }, [s, select, go]);

  return (
    <>
      <h3>Needs attention</h3>
      {items.length === 0 ? (
        <div className="allgood"><ICheck /><div><b>Nothing needs attention</b><div style={{ fontSize: 13 }}>All workers safe, gas and air within limits, every repeater reporting.</div></div></div>
      ) : (
        <div className="att">
          {items.map((it) => (
            <button key={it.key} className="att-item" onClick={it.onClick}>
              <StatusPill st={it.st}>{it.st === 'DANGER' ? 'Danger' : it.st === 'WARNING' ? 'Warning' : it.st === 'OFF' ? 'Offline' : 'To do'}</StatusPill>
              <span style={{ minWidth: 0 }}><b>{it.title}</b><small>{it.why}</small></span>
              <span className="muted" aria-hidden>›</span>
            </button>
          ))}
        </div>
      )}
      <h3 style={{ marginTop: 6 }}>Workers</h3>
      <WorkerMini s={s} />
      <p className="muted" style={{ fontSize: 13, margin: 0 }}>Click a worker, repeater, exit or danger zone in the 3D view for details. Drag to rotate, right-drag to pan, scroll to zoom.</p>
    </>
  );
}

function WorkerMini({ s }: { s: HubState }) {
  const { select } = useStore();
  if (!s.workers.length) return <div className="muted" style={{ fontSize: 14 }}>No workers registered yet. Add them on the setup page.</div>;
  return (
    <div className="att">
      {[...s.workers].sort(byStatus).map((w) => (
        <button key={w.body_id} className="att-item" onClick={() => select({ kind: 'worker', id: w.body_id })}>
          <StatusPill st={w.status} />
          <span style={{ minWidth: 0 }}><b>{w.name}</b><small>{w.live ? `${w.live.temp != null ? `${w.live.temp.toFixed(1)} °C` : 'no temp'}${w.live.hr ? ` · ${w.live.hr} bpm` : ''} · near ${w.live.near ?? '–'}` : 'no data yet'}</small></span>
          <span className="muted mono" style={{ fontSize: 12 }}>{w.body_id}</span>
        </button>
      ))}
    </div>
  );
}
