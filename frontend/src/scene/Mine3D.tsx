import { Suspense, useEffect, useMemo, useRef } from 'react';
import { Canvas, useFrame, useThree, type ThreeEvent } from '@react-three/fiber';
import { Html, Line, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import type { OrbitControls as OrbitImpl } from 'three-stdlib';
import type { HubState, Repeater, Worker } from '../api';
import { hubUrl } from '../api';
import { COLOR, levelColor, repeaterLevel, signText, statusColor } from '../util';
import { buildTunnels, mapBounds, P, signTexture, WALL_H } from './geometry';
import { useStore } from '../store';

export type View = 'iso' | 'top';
export interface SceneOpts { labels: boolean; plan: boolean; routes: boolean; trails: boolean }

const DEG = Math.PI / 180;

/* ---------------- camera ---------------- */
function CameraRig({ s, view, fitKey, focus }: { s: HubState; view: View; fitKey: number; focus: [number, number] | null }) {
  const { camera, controls } = useThree() as unknown as { camera: THREE.PerspectiveCamera; controls: OrbitImpl | null };
  const b = useMemo(() => mapBounds(s.map), [s.map]);
  const goal = useRef<{ pos: THREE.Vector3; tgt: THREE.Vector3 } | null>(null);

  useEffect(() => {
    const [tx, , tz] = P(b.cx, b.cy);
    const d = b.size * 1.05;
    goal.current = view === 'top'
      ? { pos: new THREE.Vector3(tx, d * 1.35, tz + 0.01), tgt: new THREE.Vector3(tx, 0, tz) }
      : { pos: new THREE.Vector3(tx + d * 0.45, d * 0.75, tz + d * 0.85), tgt: new THREE.Vector3(tx, 0, tz) };
  }, [b, view, fitKey]);

  useEffect(() => {
    if (!focus) return;
    const [fx, , fz] = P(focus[0], focus[1]);
    const c = controls?.target ?? new THREE.Vector3();
    const off = camera.position.clone().sub(c).setLength(Math.min(60, camera.position.distanceTo(c)));
    goal.current = { pos: new THREE.Vector3(fx, 0, fz).add(off), tgt: new THREE.Vector3(fx, 0, fz) };
  }, [focus?.[0], focus?.[1]]); // eslint-disable-line react-hooks/exhaustive-deps

  useFrame((_, dt) => {
    const g = goal.current;
    if (!g || !controls) return;
    const k = 1 - Math.exp(-dt * 5);
    camera.position.lerp(g.pos, k);
    controls.target.lerp(g.tgt, k);
    controls.update();
    if (camera.position.distanceTo(g.pos) < 0.05 && controls.target.distanceTo(g.tgt) < 0.05) goal.current = null;
  });
  return null;
}

/* ---------------- ground + plan ---------------- */
function Ground({ s, plan }: { s: HubState; plan: boolean }) {
  const b = useMemo(() => mapBounds(s.map), [s.map]);
  const m = s.map;
  const tex = useMemo(() => {
    if (!m.image) return null;
    const t = new THREE.TextureLoader().load(hubUrl(`/mapimg/${encodeURIComponent(m.image)}?r=${m.rev}`));
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 8;
    return t;
  }, [m.image, m.rev]);
  const size = b.size * 2.2;
  const [gx, , gz] = P(b.cx, b.cy);
  // plan image: pixel (px, py) → x = (px - ox) / ppm, y = (oy - py) / ppm
  const pw = m.img_w / m.ppm, ph = m.img_h / m.ppm;
  const pcx = (m.img_w / 2 - m.ox) / m.ppm, pcy = (m.oy - m.img_h / 2) / m.ppm;
  return (
    <group>
      <mesh rotation-x={-Math.PI / 2} position={[gx, -0.06, gz]} receiveShadow>
        <planeGeometry args={[size, size]} />
        <meshStandardMaterial color="#1A2125" roughness={1} />
      </mesh>
      <gridHelper args={[size, Math.round(size / 10), '#26313A', '#1F282E']} position={[gx, -0.04, gz]} />
      {plan && tex && (
        <mesh rotation-x={-Math.PI / 2} position={[pcx, -0.02, -pcy]}>
          <planeGeometry args={[pw, ph]} />
          <meshBasicMaterial map={tex} transparent opacity={0.42} depthWrite={false} toneMapped={false} />
        </mesh>
      )}
    </group>
  );
}

/* ---------------- tunnels ---------------- */
function Tunnels({ s }: { s: HubState }) {
  const key = JSON.stringify(s.map.tunnels);
  const geo = useMemo(() => buildTunnels(s.map.tunnels), [key]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => { geo.floor?.dispose(); geo.walls?.dispose(); geo.rim?.dispose(); }, [geo]);
  return (
    <group rotation-x={-Math.PI / 2}>
      {geo.floor && (
        <mesh geometry={geo.floor} position-z={0.01} receiveShadow>
          <meshStandardMaterial color="#3A464D" roughness={0.95} />
        </mesh>
      )}
      {geo.walls && (
        <mesh geometry={geo.walls} castShadow receiveShadow>
          <meshStandardMaterial color="#59646A" roughness={0.9} metalness={0.05} />
        </mesh>
      )}
      {geo.rim && (
        <mesh geometry={geo.rim} position-z={WALL_H + 0.02}>
          <meshStandardMaterial color="#8C969B" roughness={0.8} />
        </mesh>
      )}
    </group>
  );
}

/* ---------------- exits ---------------- */
function Exits({ s, labels, k }: { s: HubState; labels: boolean; k: number }) {
  const { sel, select } = useStore();
  const tex = useMemo(() => signTexture([{ text: 'EXIT', color: '#F3F0E8', size: 64 }], '#1E8B4F', '#F3F0E8', 200, 100), []);
  return (
    <>
      {s.map.exits.map((e) => {
        const on = sel?.kind === 'exit' && sel.id === e.name;
        return (
          <group key={e.name} position={P(e.x, e.y)} scale={k}
            onClick={(ev: ThreeEvent<MouseEvent>) => { ev.stopPropagation(); select({ kind: 'exit', id: e.name }); }}>
            <mesh position-y={3}>
              <cylinderGeometry args={[2.6, 2.6, 6, 24, 1, true]} />
              <meshStandardMaterial color={COLOR.safe} transparent opacity={0.28} side={THREE.DoubleSide} depthWrite={false} />
            </mesh>
            <mesh position-y={0.05} rotation-x={-Math.PI / 2}>
              <ringGeometry args={[2.3, on ? 3.6 : 2.9, 32]} />
              <meshBasicMaterial color={on ? COLOR.amber : COLOR.safe} />
            </mesh>
            <sprite position-y={7.6} scale={[5, 2.5, 1]}>
              <spriteMaterial map={tex} depthWrite={false} />
            </sprite>
            {labels && <Html position={[0, 10, 0]} center className="tag3d tag-exit" zIndexRange={[10, 0]}>{e.name}</Html>}
          </group>
        );
      })}
    </>
  );
}

/* ---------------- repeaters + exit signs ---------------- */
function RepeaterNode({ id, x, y, z, r, guide, evac, labels, k }: {
  id: string; x: number; y: number; z: number; r: Repeater | undefined;
  guide: { code: number; dist: number } | undefined; evac: boolean; labels: boolean; k: number;
}) {
  const { sel, select } = useStore();
  const lvl = r ? repeaterLevel(r) : -1;
  const col = levelColor(lvl);
  const on = sel?.kind === 'repeater' && sel.id === id;
  const halo = useRef<THREE.Mesh>(null);
  const sign = guide && evac ? signText(guide.code, guide.dist) : null;
  const tex = useMemo(() => {
    const short = id.replace('REP-', 'R');
    if (sign && sign.text) {
      const danger = sign.text === 'DANGER' || sign.text === 'NO GO';
      return signTexture([{ text: `${sign.arrow} ${sign.text}`.trim(), color: danger ? '#FF4D4F' : '#FF9F1A', size: 58 }], '#0B0F11', danger ? '#FF4D4F' : '#FF9F1A');
    }
    return signTexture([{ text: short, color: r?.online ? '#F2A900' : '#6B7A80', size: 60 }], '#0B0F11', '#2E3A40');
  }, [id, sign?.arrow, sign?.text, r?.online]); // eslint-disable-line react-hooks/exhaustive-deps

  useFrame(({ clock }) => {
    if (!halo.current) return;
    const pulse = lvl >= 1 || r?.sos ? 1 + 0.25 * Math.sin(clock.elapsedTime * (lvl >= 2 ? 6 : 3)) : 1;
    halo.current.scale.setScalar(pulse);
  });

  return (
    <group position={P(x, y, z)} scale={k}
      onClick={(ev: ThreeEvent<MouseEvent>) => { ev.stopPropagation(); select({ kind: 'repeater', id }); }}
      onPointerOver={() => (document.body.style.cursor = 'pointer')}
      onPointerOut={() => (document.body.style.cursor = '')}>
      <mesh position-y={1.4}>
        <cylinderGeometry args={[0.18, 0.18, 2.8, 8]} />
        <meshStandardMaterial color="#9DA7AD" />
      </mesh>
      <mesh position-y={3.0}>
        <boxGeometry args={[1.4, 0.9, 0.9]} />
        <meshStandardMaterial color={r?.online ? '#E9E4D8' : '#556166'} emissive={col} emissiveIntensity={r?.online ? 0.25 : 0} />
      </mesh>
      <mesh ref={halo} position-y={0.08} rotation-x={-Math.PI / 2}>
        <ringGeometry args={[1.5, 2.1, 32]} />
        <meshBasicMaterial color={on ? COLOR.amber : col} transparent opacity={0.95} />
      </mesh>
      <sprite position-y={5.4} scale={sign?.text ? [5.6, 2.8, 1] : [3.4, 1.7, 1]}>
        <spriteMaterial map={tex} depthWrite={false} />
      </sprite>
      {labels && (
        <Html position={[0, 8.2, 0]} center className={`tag3d${lvl >= 1 ? ' tag-hot' : ''}`} zIndexRange={[10, 0]}>
          {id}{r && !r.online ? ' · offline' : ''}
        </Html>
      )}
    </group>
  );
}

function Repeaters({ s, labels, k }: { s: HubState; labels: boolean; k: number }) {
  return (
    <>
      {Object.entries(s.map.repeaters).map(([id, p]) => (
        <RepeaterNode key={id} id={id} x={p.x} y={p.y} z={p.z || 0}
          r={s.repeaters.find((r) => r.id === id)} guide={s.evac.guide[id]} evac={s.evac.active} labels={labels} k={k} />
      ))}
    </>
  );
}

/* ---------------- danger zones ---------------- */
function Hazards({ s }: { s: HubState }) {
  const { select } = useStore();
  const g = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    g.current?.children.forEach((c) => {
      const ring = c.children[1] as THREE.Mesh | undefined;
      if (ring) ring.scale.setScalar(0.6 + ((clock.elapsedTime * 0.5) % 1) * 0.4);
    });
  });
  return (
    <group ref={g}>
      {s.evac.hazards.map((h, i) => (
        <group key={i} position={P(h.x, h.y)}
          onClick={(ev: ThreeEvent<MouseEvent>) => { ev.stopPropagation(); select({ kind: 'hazard', id: String(i) }); }}>
          <mesh position-y={2}>
            <cylinderGeometry args={[h.r, h.r, 4, 48, 1, true]} />
            <meshBasicMaterial color={COLOR.danger} transparent opacity={0.16} side={THREE.DoubleSide} depthWrite={false} />
          </mesh>
          <mesh position-y={0.1} rotation-x={-Math.PI / 2}>
            <ringGeometry args={[h.r * 0.96, h.r, 64]} />
            <meshBasicMaterial color={COLOR.danger} transparent opacity={0.9} />
          </mesh>
          <mesh position-y={0.04} rotation-x={-Math.PI / 2}>
            <circleGeometry args={[h.r, 64]} />
            <meshBasicMaterial color={COLOR.danger} transparent opacity={0.12} depthWrite={false} />
          </mesh>
          <Html position={[0, 5, 0]} center className="tag3d tag-danger" zIndexRange={[11, 0]}>{h.why || 'Danger zone'}</Html>
        </group>
      ))}
    </group>
  );
}

/* ---------------- workers ---------------- */
function WorkerNode({ w, x, y, z, labels, k, stack }: { w: Worker; x: number; y: number; z: number; labels: boolean; k: number; stack: number }) {
  const { sel, select } = useStore();
  const g = useRef<THREE.Group>(null);
  const ring = useRef<THREE.Mesh>(null);
  const target = useMemo(() => new THREE.Vector3(...P(x, y, z)), [x, y, z]);
  const first = useRef(true);
  const col = statusColor(w.status);
  const on = sel?.kind === 'worker' && sel.id === w.body_id;
  const sos = !!w.live && (w.live.fl & 8) !== 0;

  useFrame(({ clock }, dt) => {
    if (!g.current) return;
    if (first.current) { g.current.position.copy(target); first.current = false; }
    g.current.position.lerp(target, 1 - Math.exp(-dt * 3));
    if (ring.current) {
      const fast = w.status === 'DANGER' || sos;
      ring.current.scale.setScalar(fast ? 1 + ((clock.elapsedTime * 1.2) % 1) * 1.6 : 1);
      (ring.current.material as THREE.MeshBasicMaterial).opacity = fast ? 1 - ((clock.elapsedTime * 1.2) % 1) : 0.9;
    }
  });

  return (
    <group ref={g}
      onClick={(ev: ThreeEvent<MouseEvent>) => { ev.stopPropagation(); select({ kind: 'worker', id: w.body_id }); }}
      onPointerOver={() => (document.body.style.cursor = 'pointer')}
      onPointerOut={() => (document.body.style.cursor = '')}>
      <group scale={k}>
      <mesh position-y={1.7} castShadow>
        <capsuleGeometry args={[0.9, 1.6, 6, 12]} />
        <meshStandardMaterial color={col} emissive={col} emissiveIntensity={0.35} roughness={0.5} />
      </mesh>
      <mesh position-y={3.55}>
        <sphereGeometry args={[0.75, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2]} />
        <meshStandardMaterial color={COLOR.amber} roughness={0.4} />
      </mesh>
      <mesh ref={ring} position-y={0.12} rotation-x={-Math.PI / 2}>
        <ringGeometry args={[1.5, 1.9, 32]} />
        <meshBasicMaterial color={col} transparent opacity={0.9} />
      </mesh>
      {on && (
        <mesh position-y={0.1} rotation-x={-Math.PI / 2}>
          <ringGeometry args={[2.4, 2.9, 40]} />
          <meshBasicMaterial color={COLOR.amber} />
        </mesh>
      )}
      </group>
      {(labels || on || w.status === 'DANGER') && (
        <Html position={[0, (6 + stack * 2.6) * k, 0]} center className={`tag3d tag-worker s-${w.status.replace(' ', '')}`} zIndexRange={[12, 0]}>
          <b>{w.name || w.body_id}</b>{w.reasons[0] && w.status !== 'SAFE' ? <span>{w.reasons[0]}</span> : null}
        </Html>
      )}
    </group>
  );
}

function Workers({ s, opts, k }: { s: HubState; opts: SceneOpts; k: number }) {
  const { sel } = useStore();
  const list = useMemo(() => {
    const known = s.workers.map((w) => w);
    for (const u of s.unknown || []) {
      known.push({ body_id: u.body_id, name: `${u.body_id} (not registered)`, status: u.status, reasons: u.reasons, live: u.live } as Worker);
    }
    return known;
  }, [s.workers, s.unknown]);
  const seen = new Map<string, number>();
  return (
    <>
      {list.map((w) => {
        const p = s.positions[w.body_id];
        if (!p || p.x === null || p.y === null) return null;
        const route = s.routes[w.body_id];
        const showRoute = route && (opts.routes && (s.evac.active || (sel?.kind === 'worker' && sel.id === w.body_id)));
        const cell = `${Math.round(p.x / 4)},${Math.round(p.y / 4)}`;
        const stack = seen.get(cell) ?? 0;
        seen.set(cell, stack + 1);
        return (
          <group key={w.body_id}>
            <WorkerNode w={w} x={p.x} y={p.y} z={p.z ?? 0} labels={opts.labels} k={k} stack={stack} />
            {opts.trails && p.trail?.length > 1 && (
              <Line points={p.trail.map(([x, y]) => P(x, y, 0.25))} color={statusColor(w.status)} lineWidth={1.5} transparent opacity={0.45} />
            )}
            {showRoute && <RouteLine path={route.path} hazard={route.hazard} />}
          </group>
        );
      })}
    </>
  );
}

function RouteLine({ path, hazard }: { path: [number, number][]; hazard: boolean }) {
  const ref = useRef<{ material: { dashOffset: number } } | null>(null);
  useFrame((_, dt) => { if (ref.current) ref.current.material.dashOffset -= dt * 4; });
  if (path.length < 2) return null;
  return (
    <Line ref={ref as never} points={path.map(([x, y]) => P(x, y, 0.5))} color={hazard ? COLOR.danger : COLOR.safe}
      lineWidth={4} dashed dashSize={2.2} gapSize={1.4} />
  );
}

/* ---------------- scene ---------------- */
export default function Mine3D({ s, view, fitKey, opts, focus }: { s: HubState; view: View; fitKey: number; opts: SceneOpts; focus: [number, number] | null }) {
  const { select } = useStore();
  const b = mapBounds(s.map);
  const [cx, , cz] = P(b.cx, b.cy);
  const k = Math.min(3, Math.max(1, b.size / 70));   // markers grow with the mine so they stay visible
  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ position: [cx + b.size * 0.5, b.size * 0.8, cz + b.size * 0.9], fov: 42, near: 0.5, far: 5000 }}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      onPointerMissed={() => select(null)}
      shadows={false}
    >
      <color attach="background" args={['#12171A']} />
      <fog attach="fog" args={['#12171A', b.size * 2.2, b.size * 5]} />
      <hemisphereLight args={['#F3F0E8', '#1A2125', 0.9]} />
      <directionalLight position={[cx + 80, 160, cz + 60]} intensity={1.6} />
      <ambientLight intensity={0.25} />
      <Suspense fallback={null}>
        <Ground s={s} plan={opts.plan} />
        <Tunnels s={s} />
        <Exits s={s} labels={opts.labels} k={k} />
        <Hazards s={s} />
        <Repeaters s={s} labels={opts.labels} k={k} />
        <Workers s={s} opts={opts} k={k} />
      </Suspense>
      <OrbitControls makeDefault enableDamping dampingFactor={0.12} maxPolarAngle={84 * DEG} minDistance={8} maxDistance={b.size * 4}
        target={[cx, 0, cz]} screenSpacePanning={false} />
      <CameraRig s={s} view={view} fitKey={fitKey} focus={focus} />
    </Canvas>
  );
}
