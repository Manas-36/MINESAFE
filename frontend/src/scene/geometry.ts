import * as THREE from 'three';
import polygonClipping, { type MultiPolygon, type Polygon } from 'polygon-clipping';
import type { MapCfg } from '../api';

/** hub plan (x east, y north, z up, metres) → three.js (x, y up, z south) */
export const P = (x: number, y: number, z = 0): [number, number, number] => [x, z, -y];

export const TUNNEL_W = 3.6;   // drawn tunnel width (m)
export const WALL_T = 0.6;     // wall thickness
export const WALL_H = 2.6;     // wall height

function segmentRect(a: [number, number], b: [number, number], half: number): Polygon {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const L = Math.hypot(dx, dy) || 1;
  const nx = (-dy / L) * half, ny = (dx / L) * half;
  return [[[a[0] + nx, a[1] + ny], [b[0] + nx, b[1] + ny], [b[0] - nx, b[1] - ny], [a[0] - nx, a[1] - ny], [a[0] + nx, a[1] + ny]]];
}
function disc(c: [number, number], r: number, n = 16): Polygon {
  const ring: [number, number][] = [];
  for (let i = 0; i <= n; i++) {
    const t = (i / n) * Math.PI * 2;
    ring.push([c[0] + Math.cos(t) * r, c[1] + Math.sin(t) * r]);
  }
  return [ring];
}

function unionAll(parts: Polygon[]): MultiPolygon {
  // one union of everything; polygon-clipping can trip over exactly-overlapping edges,
  // so on failure retry piece by piece, skipping a piece that still fails
  try { return polygonClipping.union(parts[0], ...parts.slice(1)); } catch { /* fall through */ }
  let acc: MultiPolygon = [parts[0]];
  for (const q of parts.slice(1)) {
    try { acc = polygonClipping.union(acc, q); } catch { /* skip this piece */ }
  }
  return acc;
}

function tunnelArea(tunnels: MapCfg['tunnels'], half: number): MultiPolygon {
  // a tiny, fixed jitter per point keeps edges from lying exactly on top of each other
  const j = (p: [number, number]): [number, number] => {
    const h = Math.sin(p[0] * 12.9898 + p[1] * 78.233) * 43758.5453;
    const f = h - Math.floor(h);
    return [p[0] + (f - 0.5) * 1e-3, p[1] + (((f * 7.13) % 1) - 0.5) * 1e-3];
  };
  const parts: Polygon[] = [];
  const pts = new Map<string, [number, number]>();
  for (const line of tunnels) {
    for (let i = 0; i < line.length - 1; i++) {
      if (Math.hypot(line[i + 1][0] - line[i][0], line[i + 1][1] - line[i][1]) < 0.01) continue;
      parts.push(segmentRect(j(line[i]), j(line[i + 1]), half));
    }
    for (const p of line) pts.set(`${p[0].toFixed(2)},${p[1].toFixed(2)}`, p);
  }
  for (const p of pts.values()) parts.push(disc(j(p), half * 1.0005, 20));
  if (!parts.length) return [];
  return unionAll(parts);
}

function toShapes(mp: MultiPolygon): THREE.Shape[] {
  // plan (x, y) → shape (x, y); the mesh is then rotated so shape-y becomes -z (north)
  return mp.map((poly) => {
    const [outer, ...holes] = poly;
    const shape = new THREE.Shape(outer.map(([x, y]) => new THREE.Vector2(x, y)));
    for (const h of holes) shape.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
    return shape;
  });
}

export interface TunnelGeo { floor: THREE.BufferGeometry | null; walls: THREE.BufferGeometry | null; rim: THREE.BufferGeometry | null }

/** floor = the tunnel area; walls = a band of WALL_T around it, extruded WALL_H high */
export function buildTunnels(tunnels: MapCfg['tunnels']): TunnelGeo {
  if (!tunnels?.length) return { floor: null, walls: null, rim: null };
  const inner = tunnelArea(tunnels, TUNNEL_W / 2);
  const outer = tunnelArea(tunnels, TUNNEL_W / 2 + WALL_T);
  let band: MultiPolygon = [];
  try { band = polygonClipping.difference(outer, inner); } catch { band = []; }   // no walls rather than no mine
  const floor = new THREE.ShapeGeometry(toShapes(inner));
  const walls = new THREE.ExtrudeGeometry(toShapes(band), { depth: WALL_H, bevelEnabled: false });
  const rim = new THREE.ShapeGeometry(toShapes(band));
  return { floor, walls, rim };
}

export function mapBounds(m: MapCfg) {
  const xs: number[] = [], ys: number[] = [];
  for (const l of m.tunnels || []) for (const [x, y] of l) { xs.push(x); ys.push(y); }
  for (const r of Object.values(m.repeaters || {})) { xs.push(r.x); ys.push(r.y); }
  for (const e of m.exits || []) { xs.push(e.x); ys.push(e.y); }
  if (!xs.length) { xs.push(-20, 20); ys.push(-20, 20); }
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  return { minX, maxX, minY, maxY, cx: (minX + maxX) / 2, cy: (minY + maxY) / 2, size: Math.max(maxX - minX, maxY - minY, 40) };
}

/** canvas texture for an LED exit sign / label (offline: no font downloads) */
export function signTexture(lines: { text: string; color: string; size: number; font?: string }[], bg: string, border?: string, w = 256, h = 128) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const g = c.getContext('2d')!;
  g.fillStyle = bg;
  const r = 14;
  g.beginPath();
  g.roundRect(4, 4, w - 8, h - 8, r);
  g.fill();
  if (border) { g.lineWidth = 6; g.strokeStyle = border; g.stroke(); }
  const total = lines.reduce((a, l) => a + l.size * 1.1, 0);
  let y = (h - total) / 2;
  for (const l of lines) {
    g.fillStyle = l.color;
    g.font = `700 ${l.size}px ${l.font ?? 'Oswald, "Arial Narrow", Arial, sans-serif'}`;
    g.textAlign = 'center';
    g.textBaseline = 'top';
    g.fillText(l.text, w / 2, y);
    y += l.size * 1.1;
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}
