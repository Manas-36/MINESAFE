import { useMemo, useState } from 'react';
import { actions, hubUrl, type HubState, type Verification } from '../api';
import { Bars, Empty, Spark, StatusPill } from '../components/common';
import { GasCard, RepeaterDetail, WorkerDetail } from '../panels/Details';
import { useStore } from '../store';
import { COLOR, ago, byStatus, fmt, gearName, repeaterLevel } from '../util';

/* side drawer used by the list pages */
function Drawer({ s }: { s: HubState }) {
  const { sel } = useStore();
  if (!sel || (sel.kind !== 'worker' && sel.kind !== 'repeater')) return null;
  return (
    <aside className="side" style={{ position: 'fixed', right: 0, top: 'var(--top)', bottom: 0, width: 'min(420px, 100%)', zIndex: 30, boxShadow: '-12px 0 30px #0008' }}>
      <div className="side-in">
        {sel.kind === 'worker' && (() => { const w = s.workers.find((x) => x.body_id === sel.id); return w ? <WorkerDetail s={s} w={w} /> : null; })()}
        {sel.kind === 'repeater' && <RepeaterDetail s={s} id={sel.id} r={s.repeaters.find((r) => r.id === sel.id)} />}
      </div>
    </aside>
  );
}

/* ---------------- workers ---------------- */
export function WorkersPage() {
  const { s, select } = useStore();
  const [q, setQ] = useState('');
  const [f, setF] = useState<'all' | 'attention'>('all');
  if (!s) return null;
  const list = [...s.workers].sort(byStatus).filter((w) =>
    (f === 'all' || w.status === 'DANGER' || w.status === 'WARNING' || w.status === 'NO DATA') &&
    (!q || `${w.name} ${w.body_id} ${w.emp_id} ${w.zone} ${w.work}`.toLowerCase().includes(q.toLowerCase())));
  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Workers</h2><p>Everyone registered, most urgent first. Click a worker for vitals, location, route to the exit and medical card.</p></div>
        <div className="tools">
          <input className="input" style={{ width: 220 }} placeholder="Search name, ID, zone" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search workers" />
          <div className="seg"><button className={f === 'all' ? 'on' : ''} onClick={() => setF('all')}>All</button><button className={f === 'attention' ? 'on' : ''} onClick={() => setF('attention')}>Needs attention</button></div>
          <a className="btn" href="/#workers">Register a worker</a>
        </div>
      </div>
      {s.unknown.length > 0 && (
        <div className="card" style={{ marginBottom: 14, borderColor: COLOR.info }}>
          <b>Body units sending data but not registered:</b> <span className="mono">{s.unknown.map((u) => u.body_id).join(', ')}</span>. <a href="/#workers">Register them</a> so you know who is wearing them.
        </div>
      )}
      {list.length === 0 ? <Empty title={s.workers.length ? 'No one matches' : 'No workers registered yet'}>{s.workers.length ? 'Try another search.' : <>Register workers and their body unit code on the <a href="/#workers">setup page</a>.</>}</Empty> : (
        <div className="grid">
          {list.map((w) => {
            const L = w.live;
            return (
              <button key={w.body_id} className={`card click s-${w.status.replace(' ', '')}`} onClick={() => select({ kind: 'worker', id: w.body_id })}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                  <div style={{ minWidth: 0 }}><h3>{w.name}</h3><div className="muted" style={{ fontSize: 13 }}>{[w.work, w.zone].filter(Boolean).join(' · ') || '—'}</div></div>
                  <span style={{ marginLeft: 'auto' }}><StatusPill st={w.status} /></span>
                </div>
                {w.reasons.length > 0 && <div className="reasons">{w.reasons.slice(0, 3).map((r) => <span key={r} className={`reason${w.status === 'WARNING' ? ' w' : ''}`}>{r}</span>)}</div>}
                <div className="vitals">
                  <div className="vital"><small>Body</small><span className="num" style={{ fontSize: 19 }}>{fmt(L?.temp, 1, '°')}</span></div>
                  <div className="vital"><small>Heart</small><span className="num" style={{ fontSize: 19 }}>{L?.hr ?? '–'}</span></div>
                  <div className="vital"><small>Near</small><span className="num mono" style={{ fontSize: 15 }}>{L?.near ?? '–'}</span></div>
                  <div className="vital"><small>Signal</small><span style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Bars rssi={L?.near_rssi} /><small>{L ? ago(L.age) : 'never'}</small></span></div>
                </div>
                <div className="muted mono" style={{ fontSize: 12, marginTop: 8 }}>{w.body_id}{w.emp_id ? ` · ${w.emp_id}` : ''} · blood {w.blood || '–'}</div>
              </button>
            );
          })}
        </div>
      )}
      <Drawer s={s} />
    </div>
  );
}

/* ---------------- gas & air ---------------- */
export function GasPage() {
  const { s, select } = useStore();
  if (!s) return null;
  const reps = [...s.repeaters].sort((a, b) => repeaterLevel(b) - repeaterLevel(a) || a.id.localeCompare(b.id));
  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Gas and air</h2><p>Every repeater's gas sensors against the mine's limits (CMR 2017, NIOSH), plus air temperature, humidity and wet-bulb heat stress. Highest first.</p></div>
        <div className="tools"><a className="btn" href="/#limits">Change limits</a><a className="btn" href="/#gas">Calibrate sensors</a></div>
      </div>
      {reps.length === 0 ? <Empty title="No repeaters reporting yet">Power the main repeater first, then the others. They appear here within a few seconds.</Empty> : (
        <div className="grid">
          {reps.map((r) => {
            const l = repeaterLevel(r);
            return (
              <div key={r.id} className={`card s-${l >= 2 ? 'DANGER' : l === 1 ? 'WARNING' : l < 0 ? 'NODATA' : 'SAFE'}`} style={{ display: 'grid', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <h3 className="mono" style={{ fontFamily: 'var(--mono)', fontSize: 17 }}>{r.id}</h3>
                  <StatusPill st={!r.online ? 'OFF' : l >= 2 ? 'DANGER' : l === 1 ? 'WARNING' : 'SAFE'}>{!r.online ? `Offline · ${ago(r.age)}` : l >= 2 ? 'Danger' : l === 1 ? 'Warning' : 'Normal'}</StatusPill>
                  <button className="btn sm ghost" style={{ marginLeft: 'auto' }} onClick={() => select({ kind: 'repeater', id: r.id })}>Details</button>
                </div>
                <GasCard r={r} bare />
                {(r.gas_chs || []).filter((c) => c.spark?.length > 1).map((c) => (
                  <div className="chartbox" key={c.ch}><small>Sensor {c.ch}{c.ana ? ` · ${c.ana.model}` : ''} raw output (mV), last few minutes</small><Spark values={c.spark} color={COLOR.amber} height={44} /></div>
                ))}
                {!r.air_missing && r.air_spark?.length > 1 && (
                  <div className="chartbox"><small>Air temperature (°C)</small><Spark values={r.air_spark.map((p) => p[0])} warn={s.limits.air_temp_warn} danger={s.limits.air_temp_danger} height={44} /></div>
                )}
              </div>
            );
          })}
        </div>
      )}
      <Drawer s={s} />
    </div>
  );
}

/* ---------------- network ---------------- */
export function NetworkPage() {
  const { s, select } = useStore();
  const tiers = useMemo(() => {
    if (!s) return [];
    const t: string[][] = [];
    for (const r of s.repeaters) {
      const h = r.online ? Math.max(0, r.hop) : 99;
      const i = h === 99 ? -1 : h;
      if (i < 0) continue;
      (t[i] ||= []).push(r.id);
    }
    return t.filter(Boolean);
  }, [s]);
  if (!s) return null;
  const off = s.repeaters.filter((r) => !r.online);
  const bodies = [...s.workers.filter((w) => w.live), ...s.unknown.map((u) => ({ ...u, name: '(not registered)', live: u.live }))];
  return (
    <div className="page">
      <div className="page-head"><div><h2>Network</h2><p>How data reaches the control room: body units → nearest repeater → repeater chain (ESP-NOW) → main repeater → hub over Wi-Fi. The chain repairs itself if a repeater goes down.</p></div></div>
      <div className="card">
        <h3 style={{ marginBottom: 10 }}>Repeater chain</h3>
        {tiers.length === 0 ? <div className="muted">No repeaters online.</div> : (
          <div className="chain">
            <div className="node hub"><b>Control room</b><div className="muted" style={{ fontSize: 13 }}>this hub · {s.workers.length} workers registered</div></div>
            {tiers.map((ids, i) => (
              <div key={i} style={{ display: 'flex' }}>
                <div className="link">{i === 0 ? 'Wi-Fi' : 'ESP-NOW'}<br />→</div>
                <div className="tier">
                  {ids.map((id) => {
                    const r = s.repeaters.find((x) => x.id === id)!;
                    return (
                      <button key={id} className="node" style={{ textAlign: 'left', cursor: 'pointer', borderColor: repeaterLevel(r) >= 1 ? COLOR.warn : undefined }} onClick={() => select({ kind: 'repeater', id })}>
                        <b className="mono">{id}</b> {r.gateway && <span className="muted" style={{ fontSize: 12 }}>main</span>}
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 13 }} className="muted">
                          <Bars rssi={r.gateway ? r.rssi : r.prssi} /> {r.gateway ? `${r.rssi} dBm` : `${r.prssi ?? '–'} dBm to ${r.parent}`}
                        </div>
                        <div className="muted" style={{ fontSize: 12 }}>{s.workers.filter((w) => w.live?.near === id).length} workers near</div>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
        {off.length > 0 && <p style={{ color: COLOR.warn, marginBottom: 0 }}>Offline: {off.map((r) => `${r.id} (last heard ${ago(r.age)})`).join(', ')}. Check power, then the distance to its neighbours.</p>}
      </div>

      <div className="section">
        <h3>Repeaters</h3>
        <div className="tablewrap">
          <table className="t">
            <thead><tr><th>Repeater</th><th>Status</th><th>Hops</th><th>Sends to</th><th>Link</th><th>Last report</th><th>Air</th><th>Buzzer</th></tr></thead>
            <tbody>
              {s.repeaters.map((r) => (
                <tr key={r.id} className="click" onClick={() => select({ kind: 'repeater', id: r.id })}>
                  <td className="mono">{r.id}</td>
                  <td><StatusPill st={r.online ? 'SAFE' : 'OFF'}>{r.online ? 'Online' : 'Offline'}</StatusPill></td>
                  <td>{r.hop}</td>
                  <td className="mono">{r.gateway ? 'Hub (Wi-Fi)' : r.parent}</td>
                  <td><Bars rssi={r.gateway ? r.rssi : r.prssi} /> {r.gateway ? r.rssi : r.prssi} dBm</td>
                  <td>{ago(r.age)}</td>
                  <td>{r.air_missing ? '–' : `${fmt(r.air_t, 1)} °C · ${fmt(r.air_h, 0)} %`}</td>
                  <td>{r.buzzing ? <b style={{ color: COLOR.danger }}>sounding</b> : 'quiet'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section">
        <h3>Body units on air</h3>
        {bodies.length === 0 ? <Empty title="No body units heard yet">Switch a body unit on near a repeater. It appears here within a few seconds.</Empty> : (
          <div className="tablewrap">
            <table className="t">
              <thead><tr><th>Body unit</th><th>Worker</th><th>Last packet</th><th>Nearest repeater</th><th>Packet loss</th><th>Route to hub</th></tr></thead>
              <tbody>
                {bodies.map((b) => (
                  <tr key={b.body_id} className="click" onClick={() => select({ kind: 'worker', id: b.body_id })}>
                    <td className="mono">{b.body_id}</td>
                    <td>{b.name}</td>
                    <td>{b.live ? ago(b.live.age) : '–'}</td>
                    <td><span className="mono">{b.live?.near ?? '–'}</span> <Bars rssi={b.live?.near_rssi} /></td>
                    <td>{b.live ? `${Math.round(b.live.loss * 100)} %` : '–'}</td>
                    <td className="mono" style={{ fontSize: 13 }}>{b.live?.path?.join(' → ') ?? '–'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <Drawer s={s} />
    </div>
  );
}

/* ---------------- entry ---------------- */
export function EntryPage() {
  const { s, toast } = useStore();
  if (!s) return null;
  const pending = s.verifications.filter((v) => v.status === 'PENDING');
  const done = s.verifications.filter((v) => v.status !== 'PENDING').slice(0, 12);
  const cleared = Object.entries(s.cleared);
  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Entry check</h2><p>At the gate the worker taps each gear tag on the scanner, then a photo is taken on the phone page. Check the photo and tags, then approve to pair the body unit for this shift.</p></div>
        <div className="tools"><a className="btn" href="/phone" target="_blank" rel="noreferrer">Open phone camera page</a></div>
      </div>
      {s.pending_scans > 0 && <div className="card" style={{ marginBottom: 14, borderColor: COLOR.amber }}><b>{s.pending_scans} gear tag{s.pending_scans > 1 ? 's' : ''} scanned</b> — waiting for the photo from the phone page.</div>}
      <h3 style={{ marginBottom: 10 }}>Waiting for approval</h3>
      {pending.length === 0 ? <Empty title="No one waiting at the gate">New entry checks appear here as soon as the photo is sent.</Empty> : (
        <div style={{ display: 'grid', gap: 14 }}>{pending.map((v) => <VerCard key={v.id} v={v} s={s} toast={toast} />)}</div>
      )}
      <div className="section">
        <h3>Cleared for this shift</h3>
        {cleared.length === 0 ? <div className="muted">Nobody cleared yet.</div> : (
          <div className="tablewrap"><table className="t">
            <thead><tr><th>Body unit</th><th>Worker</th><th>Gear</th><th>Time</th><th /></tr></thead>
            <tbody>{cleared.map(([bid, c]) => (
              <tr key={bid}><td className="mono">{bid}</td><td>{c.worker || c.worker_id || '–'}</td><td>{c.gear.join(', ').toLowerCase() || '–'}</td><td>{c.time}</td>
                <td><button className="btn sm" onClick={async () => { const r = await actions.revoke(bid); toast(r.ok ? `${bid} no longer cleared` : `Not changed: ${r.error}`, !r.ok); }}>Revoke</button></td></tr>
            ))}</tbody>
          </table></div>
        )}
      </div>
      {done.length > 0 && (
        <div className="section">
          <h3>Recent decisions</h3>
          <div className="tablewrap"><table className="t">
            <thead><tr><th>Time</th><th>Body unit</th><th>Worker</th><th>Decision</th><th>AI check</th></tr></thead>
            <tbody>{done.map((v) => (
              <tr key={v.id}><td>{v.time}</td><td className="mono">{v.body_id || '–'}</td><td>{v.worker || v.worker_id || '–'}</td>
                <td><StatusPill st={v.status === 'APPROVED' ? 'SAFE' : 'DANGER'}>{v.status === 'APPROVED' ? 'Approved' : 'Rejected'}</StatusPill></td>
                <td>{v.ai?.ok ? v.ai.verdict : '–'}</td></tr>
            ))}</tbody>
          </table></div>
        </div>
      )}
    </div>
  );
}

function VerCard({ v, s, toast }: { v: Verification; s: HubState; toast: (m: string, b?: boolean) => void }) {
  const reg = s.workers.find((w) => w.body_id === v.body_id);
  const [worker, setWorker] = useState(reg?.name ?? '');
  const [bid, setBid] = useState(v.body_id);
  const scanned = Array.from(new Set(v.scans.filter((x) => x.check === 'OK').map((x) => x.gear)));
  const [gear, setGear] = useState<string[]>(scanned);
  const [busy, setBusy] = useState(false);
  const decide = async (a: 'approve' | 'reject') => {
    if (a === 'approve' && !bid.trim()) { toast('Type the body unit code before approving', true); return; }
    setBusy(true);
    const r = await actions.verify(v.id, a, worker, v.worker_id, bid, gear);
    setBusy(false);
    toast(r.ok ? (a === 'approve' ? `${worker || bid} approved — body unit paired` : 'Entry rejected') : `Not saved: ${r.error}`, !r.ok);
  };
  return (
    <div className="card ver">
      <a href={hubUrl(`/photos/${v.photo}`)} target="_blank" rel="noreferrer"><img src={hubUrl(`/photos/${v.photo}`)} alt={`Entry photo of ${v.body_id || 'worker'}`} /></a>
      <div style={{ display: 'grid', gap: 10, alignContent: 'start' }}>
        <div className="muted" style={{ fontSize: 13 }}>{v.time} · {v.source}</div>
        {v.ai ? (v.ai.ok
          ? <div><StatusPill st={v.ai.complete ? 'SAFE' : 'DANGER'}>{v.ai.verdict}</StatusPill>{v.ai.note && <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>{v.ai.note}</div>}</div>
          : <div className="muted">AI check not available: {v.ai.error}</div>)
          : <div className="muted">AI check off — check the photo by eye.</div>}
        <div>
          <div className="muted" style={{ fontSize: 13, marginBottom: 4 }}>Gear tags scanned</div>
          {v.scans.length === 0 ? <div className="muted">No tags were scanned before the photo.</div> : (
            <div className="gear">{v.scans.map((x) => (
              <span key={x.uid} className={`pill s-${x.check === 'OK' ? 'SAFE' : 'DANGER'}`}>{gearName(s.kit_names, x.gear)} · {x.check === 'OK' ? 'OK' : x.check.toLowerCase()}</span>
            ))}</div>
          )}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <label className="f">Worker<input className="input" value={worker} onChange={(e) => setWorker(e.target.value)} placeholder="Name" /></label>
          <label className="f">Body unit<input className="input mono" value={bid} onChange={(e) => setBid(e.target.value.toUpperCase())} placeholder="BODY-01" /></label>
        </div>
        <div>
          <div className="muted" style={{ fontSize: 13, marginBottom: 4 }}>Gear confirmed</div>
          <div className="gear">{s.gear_list.map((g) => (
            <label key={g}><input type="checkbox" checked={gear.includes(g)} onChange={(e) => setGear((x) => e.target.checked ? [...x, g] : x.filter((y) => y !== g))} />{gearName(s.kit_names, g)}</label>
          ))}</div>
        </div>
        <div className="actions">
          <button className="btn amber" disabled={busy} onClick={() => decide('approve')}>Approve and pair</button>
          <button className="btn redline" disabled={busy} onClick={() => decide('reject')}>Reject</button>
        </div>
      </div>
    </div>
  );
}

/* ---------------- log ---------------- */
export function LogPage() {
  const { s } = useStore();
  const [tab, setTab] = useState<'status' | 'alerts' | 'tags'>('status');
  if (!s) return null;
  return (
    <div className="page">
      <div className="page-head">
        <div><h2>Log</h2><p>Every change in a worker's status, every alert and evacuation, and every gear tag scanned at the gate — newest first. Kept by the hub while it runs.</p></div>
        <div className="tools"><div className="seg">
          <button className={tab === 'status' ? 'on' : ''} onClick={() => setTab('status')}>Status changes</button>
          <button className={tab === 'alerts' ? 'on' : ''} onClick={() => setTab('alerts')}>Alerts</button>
          <button className={tab === 'tags' ? 'on' : ''} onClick={() => setTab('tags')}>Gear tags</button>
        </div></div>
      </div>
      {tab === 'status' && (s.incidents.length === 0 ? <Empty title="No status changes yet" /> : (
        <div className="tablewrap"><table className="t">
          <thead><tr><th>Time</th><th>Worker</th><th>Change</th><th>Why</th></tr></thead>
          <tbody>{s.incidents.map((i, k) => (
            <tr key={k}><td>{i.time}</td><td>{i.name} <span className="muted mono" style={{ fontSize: 12 }}>{i.body_id}</span></td>
              <td><StatusPill st={i.from} /> → <StatusPill st={i.to} /></td><td>{i.why}</td></tr>
          ))}</tbody>
        </table></div>
      ))}
      {tab === 'alerts' && (s.alert_log.length === 0 ? <Empty title="No alerts sent yet" /> : (
        <div className="tablewrap"><table className="t">
          <thead><tr><th>Time</th><th>Action</th><th>Who</th><th>Message</th></tr></thead>
          <tbody>{s.alert_log.map((a, k) => <tr key={k}><td>{a.time}</td><td><b>{a.action}</b></td><td>{a.target || '–'}</td><td>{a.msg || '–'}</td></tr>)}</tbody>
        </table></div>
      ))}
      {tab === 'tags' && (s.events.length === 0 ? <Empty title="No tags scanned yet" /> : (
        <div className="tablewrap"><table className="t">
          <thead><tr><th>Time</th><th>Station</th><th>Event</th><th>Gear</th><th>Tag</th><th>Check</th></tr></thead>
          <tbody>{s.events.map((e, k) => <tr key={k}><td>{e.time}</td><td>{e.station || '–'}</td><td>{e.event}</td><td>{e.gear ? gearName(s.kit_names, e.gear) : '–'}</td><td className="mono" style={{ fontSize: 12 }}>{e.uid}</td><td>{e.check}</td></tr>)}</tbody>
        </table></div>
      ))}
    </div>
  );
}
