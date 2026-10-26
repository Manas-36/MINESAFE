// MineSafe — Avishkar research poster, 1 m x 1 m (Annexure 1 header: Slot No., convention, Category, Level).
// Anonymous by rule: no college, guide or student names anywhere.
// node build_poster.js  ->  MineSafe_Avishkar_Poster.pptx (editable; fill Slot No. / Level) ; PDF via LibreOffice
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const path = require("path");

const R = path.resolve(__dirname, "..", "..", "..");
const IMG = (p) => path.join(R, p);
const PI = (p) => path.join(__dirname, "img", p);
const OUT = path.join(__dirname, "MineSafe_Avishkar_Poster.pptx");

const S = 39.37;                                        // 1 m in inches
const C = { ink: "1B2329", ink2: "2C3840", amber: "F2A900", orange: "E8710A", red: "C8102E", green: "2E8B57", blue: "2F5F9E",
            bg: "F4F1EA", card: "FFFFFF", line: "D8D1C2", muted: "5B6670", soft: "FFF6DB", teal: "1F7A6D" };
const F = "Calibri", FH = "Cambria";

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
}
async function stripes(wIn, hIn) {
  const W = Math.round(wIn * 100), H = Math.round(hIn * 100), step = H * 1.6;
  let p = "";
  for (let x = -H; x < W + H; x += step * 2) p += `<polygon points="${x},${H} ${x + H},0 ${x + H + step},0 ${x + step},${H}" fill="#1B2329"/>`;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><rect width="${W}" height="${H}" fill="#F2A900"/>${p}</svg>`;
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.defineLayout({ name: "POSTER_1M", width: S, height: S });
  pres.layout = "POSTER_1M";
  pres.title = "MineSafe — Avishkar poster";
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };

  const T = (t, o) => s.addText(t, { isTextBox: true, fontFace: F, color: C.ink, margin: 0, valign: "top", fontSize: 24, ...o });
  const rect = (x, y, w, h, fill, line, o = {}) => s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: line || fill, width: o.lw || 1 }, ...o });
  const rrect = (x, y, w, h, fill, line, o = {}) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: o.r ?? 0.15, fill: { color: fill }, line: { color: line || fill, width: o.lw || 1.5, dashType: o.dash || "solid" } });
  const hline = (x1, x2, y, col = C.ink, o = {}) => s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y, w: Math.abs(x2 - x1), h: 0, flipH: x2 < x1,
    line: { color: col, width: o.w || 3, dashType: o.dash || "solid", endArrowType: o.noArrow ? undefined : "triangle" } });
  const vline = (x, y1, y2, col = C.ink, o = {}) => s.addShape(pres.shapes.LINE, { x, y: Math.min(y1, y2), w: 0, h: Math.abs(y2 - y1), flipV: y2 < y1,
    line: { color: col, width: o.w || 3, dashType: o.dash || "solid", endArrowType: o.noArrow ? undefined : "triangle" } });
  const dot = (x, y, r = 0.12, col = C.orange) => s.addShape(pres.shapes.OVAL, { x: x - r, y: y - r, w: 2 * r, h: 2 * r, fill: { color: col }, line: { color: "FFFFFF", width: 2 } });

  // section card: number tab + dark header bar
  const sec = (x, y, w, h, n, title) => {
    rect(x, y, w, h, C.card, C.line, { lw: 1.5 });
    rect(x, y, w, 1.0, C.ink);
    rect(x, y, 1.15, 1.0, C.amber);
    T(String(n).padStart(2, "0"), { x, y, w: 1.15, h: 1.0, fontSize: 36, bold: true, align: "center", valign: "middle", color: C.ink });
    T(title.toUpperCase(), { x: x + 1.45, y, w: w - 1.6, h: 1.0, fontSize: 32, bold: true, color: "FFFFFF", valign: "middle", charSpacing: 2 });
  };

  // ---------------------------------------------------------------- frame + Annexure-1 header
  rect(0.35, 0.35, S - 0.7, S - 0.7, "FFFFFF", C.ink, { lw: 3 });
  T([{ text: "Slot No.: ", options: { bold: true } }, { text: "____________" }], { x: 30.2, y: 0.65, w: 8.3, h: 0.7, fontSize: 32, align: "right" });
  T([{ text: "Inter-University Avishkar Research Convention:  ", options: { bold: true } }, { text: "2026-27", options: { bold: true } }],
    { x: 6, y: 0.75, w: S - 12, h: 0.8, fontSize: 40, align: "center" });
  T([{ text: "Category: ", options: { bold: true } }, { text: "Engineering & Technology" }], { x: 0.9, y: 1.6, w: 14, h: 0.7, fontSize: 32 });
  T([{ text: "Level: ", options: { bold: true } }, { text: "UG" }], { x: 26.5, y: 1.6, w: 12, h: 0.7, fontSize: 32, align: "right" });

  // title band
  const bx = 0.9, bw = S - 1.8, by = 2.55, bh = 3.6;
  rect(bx, by, bw, bh, C.ink);
  rect(bx, by, 0.35, bh, C.amber);
  s.addImage({ data: await icon(fa.FaHardHat, C.amber, 512), x: bx + 0.9, y: by + 0.55, w: 2.5, h: 2.5 });
  T("MineSafe", { x: bx + 3.9, y: by + 0.25, w: 14, h: 1.75, fontSize: 118, bold: true, color: C.amber, fontFace: FH, valign: "middle" });
  T("Intelligent Safety Gear Compliance, Health Monitoring and Navigation System for Underground Miners",
    { x: bx + 3.9, y: by + 2.05, w: 23.5, h: 1.3, fontSize: 40, color: "FFFFFF", fontFace: FH, valign: "middle" });
  const chips = [["No GPS", fa.FaSatelliteDish], ["No internet", fa.FaWifi], ["No new cabling", fa.FaPlug]];
  for (let i = 0; i < chips.length; i++) {
    const cy = by + 0.4 + i * 1.0;
    rrect(bx + bw - 7.3, cy, 6.7, 0.8, C.ink2, C.amber, { r: 0.4, lw: 2 });
    s.addImage({ data: await icon(chips[i][1], C.amber), x: bx + bw - 7.0, y: cy + 0.16, w: 0.48, h: 0.48 });
    T(chips[i][0], { x: bx + bw - 6.3, y: cy, w: 5.6, h: 0.8, fontSize: 30, bold: true, color: "FFFFFF", valign: "middle" });
  }
  s.addImage({ data: await stripes(bw, 0.32), x: bx, y: by + bh, w: bw, h: 0.32 });

  // body background
  const top = 6.75, bot = 37.75;
  rect(0.9, top - 0.25, S - 1.8, bot - top + 0.5, C.bg);

  const X0 = 1.15, W = S - 2.3, G = 0.45;
  const rows = { A: [top, 7.9], B: [top + 7.9 + G, 9.1], C: [top + 7.9 + 9.1 + 2 * G, 6.5] };
  rows.D = [rows.C[0] + 6.5 + G, bot - (rows.C[0] + 6.5 + G)];

  // ================================================================ 01 problem
  {
    const [y, h] = rows.A, x = X0, w = 12.1;
    sec(x, y, w, h, 1, "The problem");
    s.addChart(pres.charts.BAR, [{ name: "Deaths", labels: ["2023", "2024", "2025"], values: [41, 49, 51] }], {
      x: x + 0.3, y: y + 1.25, w: 6.4, h: 5.2, barDir: "col", chartColors: [C.red], barGapWidthPct: 55,
      showValue: true, dataLabelPosition: "outEnd", dataLabelColor: C.ink, dataLabelFontSize: 26, dataLabelFontBold: true, dataLabelFontFace: F,
      catAxisLabelColor: C.ink, catAxisLabelFontSize: 24, catAxisLabelFontFace: F, valAxisHidden: true, valAxisMaxVal: 60, valAxisMinVal: 0,
      valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false,
      showTitle: true, title: "Coal-mine deaths in India", titleColor: C.ink, titleFontSize: 24, titleFontFace: F });
    const st = [["141", "deaths, 2023–25", C.red], ["355", "serious accidents", C.orange], ["0", "GPS or phone signal below ground", C.ink]];
    st.forEach(([b, l, col], i) => {
      const yy = y + 1.35 + i * 1.75;
      rect(x + 6.95, yy, 0.14, 1.5, col);
      T(b, { x: x + 7.25, y: yy - 0.05, w: 4.6, h: 0.95, fontSize: 60, bold: true, color: col, fontFace: FH });
      T(l, { x: x + 7.25, y: yy + 0.92, w: 4.6, h: 0.6, fontSize: 22, color: C.muted });
    });
    rect(x + 0.3, y + 6.6, w - 0.6, 1.0, C.soft);
    T([{ text: "In every rescue: ", options: { bold: true, color: C.red } }, { text: "nobody knows who is underground, where, or whether they are alive." }],
      { x: x + 0.5, y: y + 6.6, w: w - 1.0, h: 1.0, fontSize: 23, valign: "middle" });
  }

  // ================================================================ 02 objectives
  {
    const [y, h] = rows.A, x = X0 + 12.1 + G, w = 11.6;
    sec(x, y, w, h, 2, "Objectives");
    const ob = [[fa.FaHardHat, "Kit compliance", "RFID / ID card + YOLOv8 photo check at the gate"], [fa.FaHeartbeat, "Health", "heart rate, SpO₂, temperature, falls, no-movement"],
                [fa.FaMapMarkedAlt, "GPS-free location", "steps + heading, corrected at every repeater"], [fa.FaProjectDiagram, "Self-healing network", "hop-by-hop ESP-NOW, no cabling or internet"],
                [fa.FaSmog, "Gas and heat", "CH₄, CO, H₂S, wet-bulb at every repeater"], [fa.FaRupeeSign, "Low cost", "< ₹7,000 / repeater · ≈ ₹12,800 / suit"]];
    for (let i = 0; i < ob.length; i++) {
      const [Ic, a, b] = ob[i], yy = y + 1.3 + i * 1.08;
      s.addShape(pres.shapes.OVAL, { x: x + 0.35, y: yy + 0.06, w: 0.86, h: 0.86, fill: { color: C.soft }, line: { color: C.amber, width: 2.5 } });
      s.addImage({ data: await icon(Ic, C.ink), x: x + 0.56, y: yy + 0.27, w: 0.44, h: 0.44 });
      T(a, { x: x + 1.45, y: yy, w: w - 1.7, h: 0.48, fontSize: 25, bold: true });
      T(b, { x: x + 1.45, y: yy + 0.46, w: w - 1.7, h: 0.5, fontSize: 21, color: C.muted });
    }
  }

  // ================================================================ 03 research gap
  {
    const [y, h] = rows.A, x = X0 + 12.1 + 11.6 + 2 * G, w = W - 12.1 - 11.6 - 2 * G;
    sec(x, y, w, h, 3, "Research gap");
    const Y = "✓", N = "✗", P = "~";
    const rowsT = [["System", "Kit", "Vitals", "Fall", "Location", "Gas", "Price"],
      ["MineGuard 360", N, Y, P, P, Y, "quote"], ["MineARC GuardIAN", N, N, P, "zone", Y, "quote"], ["Leantegra UWB", N, N, N, Y, Y, "quote"],
      ["Rajant Health", "tag", Y, Y, P, P, "quote"], ["SmartKavach", N, P, Y, N, N, "quote"], ["36Zero + Bodytrak", P, Y, Y, N, N, "quote"],
      ["MineSafe", Y, Y, Y, Y, Y, "₹12.8k"]];
    const cell = (v, r, c) => {
      const head = r === 0, last = r === rowsT.length - 1;
      let col = C.ink;
      if (!head && !last && c > 0 && c < 6) col = v === Y ? C.green : v === N ? C.red : C.orange;
      if (c === 6 && !head && !last) col = C.muted;
      return { text: v, options: { bold: head || last || (c > 0 && c < 6), color: head ? "FFFFFF" : last ? C.ink : col,
        fill: { color: head ? C.ink2 : last ? C.amber : r % 2 ? "FFFFFF" : "F7F4EE" }, align: c === 0 ? "left" : "center",
        fontSize: head ? 20 : (c > 0 && c < 6 ? (v.length > 1 ? 21 : 26) : 21), valign: "middle" } };
    };
    s.addTable(rowsT.map((r, ri) => r.map((v, ci) => cell(v, ri, ci))), { x: x + 0.3, y: y + 1.3, w: w - 0.6,
      colW: [3.85, 1.05, 1.2, 1.0, 1.75, 1.0, 1.42], rowH: 0.66, fontFace: F, border: { type: "solid", color: C.line, pt: 1 }, margin: [0, 0.1, 0, 0.12] });
    T([{ text: "Novelty: ", options: { bold: true, color: C.orange } }, { text: "the first low-cost system that combines kit check, vitals and GPS-free location in one self-healing network." }],
      { x: x + 0.3, y: y + 6.75, w: w - 0.6, h: 0.95, fontSize: 22 });
  }

  // ================================================================ 04 methodology (architecture + shift flowchart)
  {
    const [y, h] = rows.B, x = X0, w = 24.5;
    sec(x, y, w, h, 4, "Methodology — architecture and data flow");
    const ax = x + 0.4, ay = y + 1.75, bh = 2.3;
    const boxes = [["Smart suit", "4 pods: vitals, fall, kit, steps", 3.6, true, fa.FaUserShield], ["REP-03", "gas · air · exit sign", 2.9, false, fa.FaBroadcastTower],
                   ["REP-02", "gas · air · exit sign", 2.9, false, fa.FaBroadcastTower], ["REP-01", "main repeater", 3.0, false, fa.FaBroadcastTower],
                   ["Hub laptop", "API · AI kit check · evacuation planner", 3.7, true, fa.FaServer], ["3D control app", "browser or phone, live", 3.2, false, fa.FaDesktop]];
    const gap = (w - 0.8 - boxes.reduce((a, b) => a + b[2], 0)) / (boxes.length - 1);
    let cx = ax; const xs = [];
    for (const [t, sub, bw, hi, Ic] of boxes) {
      rrect(cx, ay, bw, bh, hi ? C.soft : "FFFFFF", hi ? C.amber : C.ink, { lw: hi ? 3 : 2 });
      s.addImage({ data: await icon(Ic, hi ? C.orange : C.ink), x: cx + bw / 2 - 0.3, y: ay + 0.15, w: 0.6, h: 0.6 });
      T(t, { x: cx, y: ay + 0.8, w: bw, h: 0.55, fontSize: 25, bold: true, align: "center" });
      T(sub, { x: cx + 0.12, y: ay + 1.35, w: bw - 0.24, h: 0.9, fontSize: 19, align: "center", color: C.muted });
      xs.push([cx, bw]); cx += bw + gap;
    }
    const labels = ["ESP-NOW", "ESP-NOW", "ESP-NOW", "Wi-Fi", "Wi-Fi"];
    for (let i = 0; i < xs.length - 1; i++) {
      const x1 = xs[i][0] + xs[i][1], x2 = xs[i + 1][0];
      hline(x1 + 0.05, x2 - 0.05, ay + bh / 2, C.orange, { w: 4 });
      T(labels[i], { x: x1 - 0.4, y: ay - 0.5, w: x2 - x1 + 0.8, h: 0.4, fontSize: 17, bold: true, color: C.orange, align: "center" });
    }
    hline(xs[4][0] + 1.8, xs[0][0] + 1.8, ay + bh + 0.45, C.blue, { w: 3, dash: "dash" });
    vline(xs[4][0] + 1.8, ay + bh, ay + bh + 0.45, C.blue, { w: 3, dash: "dash", noArrow: true });
    vline(xs[0][0] + 1.8, ay + bh + 0.45, ay + bh + 0.02, C.blue, { w: 3, dash: "dash" });
    T("alerts and evacuation routes return down the same chain · 1 packet / s per worker · data stays on site, no cloud",
      { x: xs[0][0] + 2.2, y: ay + bh + 0.55, w: 17, h: 0.45, fontSize: 19, color: C.blue, align: "center", italic: true });

    // shift flowchart
    const fy = y + 6.05, fh = 1.65;
    T("WORKER'S SHIFT", { x: ax, y: fy - 0.6, w: 8, h: 0.45, fontSize: 21, bold: true, color: C.orange, charSpacing: 3 });
    const nodes = [["Kit up", "suit self-checks", 2.55, "b"], ["Entry check", "ID card + YOLOv8 photo", 3.05, "b"], ["Kit OK?", "", 2.2, "d"],
                   ["Underground", "vitals · steps · gas, every 1 s", 3.3, "b"], ["Alarm?", "", 2.2, "d"], ["Alert + route", "exit signs, cuff, helmet voice", 3.3, "h"], ["Exit scan", "dock charges", 2.55, "b"]];
    const g2 = (w - 0.8 - nodes.reduce((a, b) => a + b[2], 0)) / (nodes.length - 1);
    let nx = ax; const nxs = [];
    for (const [t, sub, nw, kind] of nodes) {
      if (kind === "d") {
        s.addShape(pres.shapes.DIAMOND, { x: nx, y: fy - 0.1, w: nw, h: fh + 0.2, fill: { color: C.amber }, line: { color: C.ink, width: 2 } });
        T(t, { x: nx, y: fy - 0.1, w: nw, h: fh + 0.2, fontSize: 22, bold: true, align: "center", valign: "middle" });
      } else {
        rrect(nx, fy, nw, fh, kind === "h" ? "FBE3E6" : "FFFFFF", kind === "h" ? C.red : C.ink, { lw: 2 });
        T(t, { x: nx, y: fy + 0.18, w: nw, h: 0.5, fontSize: 23, bold: true, align: "center", color: kind === "h" ? C.red : C.ink });
        T(sub, { x: nx + 0.1, y: fy + 0.7, w: nw - 0.2, h: 0.85, fontSize: 18, align: "center", color: C.muted });
      }
      nxs.push([nx, nw]); nx += nw + g2;
    }
    for (let i = 0; i < nxs.length - 1; i++) hline(nxs[i][0] + nxs[i][1] + 0.03, nxs[i + 1][0] - 0.03, fy + fh / 2, C.ink, { w: 3 });
    T("yes", { x: nxs[2][0] + nxs[2][1], y: fy + 0.25, w: g2, h: 0.35, fontSize: 17, bold: true, color: C.green, align: "center" });
    T("yes", { x: nxs[4][0] + nxs[4][1], y: fy + 0.25, w: g2, h: 0.35, fontSize: 17, bold: true, color: C.red, align: "center" });
    // Kit OK? no -> fix kit, back to Kit up
    const d1 = nxs[2][0] + nxs[2][1] / 2, by2 = fy + fh + 0.35;
    vline(d1, fy + fh + 0.1, by2 + 0.2, C.red, { w: 3, noArrow: true });
    hline(d1, nxs[0][0] + nxs[0][1] / 2, by2 + 0.2, C.red, { w: 3, noArrow: true });
    vline(nxs[0][0] + nxs[0][1] / 2, by2 + 0.2, fy + fh + 0.03, C.red, { w: 3 });
    T("no → rejected, fix kit", { x: nxs[0][0] + nxs[0][1] / 2 + 0.2, y: by2 + 0.25, w: 5.5, h: 0.4, fontSize: 18, color: C.red, bold: true });
    // Alarm? no -> keep monitoring
    const d2 = nxs[4][0] + nxs[4][1] / 2;
    vline(d2, fy + fh + 0.1, by2 + 0.2, C.green, { w: 3, noArrow: true });
    hline(d2, nxs[3][0] + nxs[3][1] / 2, by2 + 0.2, C.green, { w: 3, noArrow: true });
    vline(nxs[3][0] + nxs[3][1] / 2, by2 + 0.2, fy + fh + 0.03, C.green, { w: 3 });
    T("no → keep monitoring", { x: nxs[3][0] + nxs[3][1] / 2 + 0.2, y: by2 + 0.25, w: 5, h: 0.4, fontSize: 18, color: C.green, bold: true });
  }

  // ================================================================ 05 smart suit (callouts)
  {
    const [y, h] = rows.B, x = X0 + 24.5 + G, w = W - 24.5 - G;
    sec(x, y, w, h, 5, "V4 smart suit");
    const ih = h - 2.0, iw = ih * 799 / 2421, ix = x + (w - iw) / 2, iy = y + 1.25;
    s.addImage({ path: PI("smart_suit.png"), x: ix, y: iy, w: iw, h: ih, altText: "Smart suit 3D render" });
    const P = (rx, ry) => [ix + rx * iw, iy + ry * ih];
    const L = [["Helmet pod", "antenna at head height, voice alerts, helmet-on switch", P(0.5, 0.05), 0],
               ["Core pod · chest", "ESP32-C6, 3000 mAh, IMU + pressure, SOS", P(0.38, 0.235), 1],
               ["Zip + seams", "reed switch, conductive thread: opened or torn = alert", P(0.47, 0.33), 0],
               ["Wrist cuff", "screen, 3 glove buttons, vibration, HR + SpO₂", P(0.9, 0.42), 1],
               ["Reflective bands", "hi-vis in cap-lamp light", P(0.7, 0.82), 1],
               ["Boot pod", "foot IMU measures every real stride", P(0.3, 0.95), 0]];
    const lw = (w - iw) / 2 - 0.45;
    const ly = { 0: [y + 1.4, y + 3.75, y + 7.2], 1: [y + 2.4, y + 4.65, y + 6.9] };
    const used = { 0: 0, 1: 0 };
    for (const [t, d, [px, py], side] of L) {
      const yy = ly[side][used[side]++];
      const tx = side === 0 ? x + 0.3 : ix + iw + 0.15;
      T(t, { x: tx, y: yy, w: lw, h: 0.5, fontSize: 23, bold: true, color: C.orange, align: side === 0 ? "left" : "right" });
      T(d, { x: tx, y: yy + 0.48, w: lw, h: 1.15, fontSize: 18, color: C.ink, align: side === 0 ? "left" : "right" });
      const ex = side === 0 ? x + 0.3 + lw : ix + iw + 0.15;
      // elbow connector: horizontal from label row to the point's x, then vertical to the point
      const lyy = yy + 0.25;
      hline(side === 0 ? x + 0.3 + Math.min(lw, 2.6) : ex + lw - Math.min(lw, 2.6), px, lyy, C.orange, { w: 2, noArrow: true });
      vline(px, lyy, py, C.orange, { w: 2, noArrow: true });
      dot(px, py, 0.13);
    }
    T("Never locked: removal is detected, never prevented", { x: x + 0.3, y: y + h - 0.6, w: w - 0.6, h: 0.45, fontSize: 18, italic: true, color: C.muted, align: "center" });
  }

  // ================================================================ 06 location + evacuation
  {
    const [y, h] = rows.C, x = X0, w = 12.1;
    sec(x, y, w, h, 6, "Location without GPS");
    const st = [["Count steps", "stride × gyro heading; pressure gives the level"], ["Snap to tunnel", "position pulled onto the mine-map centre line"],
                ["Reset at repeater", "signal ≥ −55 dBm → drift back to zero"], ["Route around danger", "Dijkstra from all exits, hazard zone ×1000 cost"]];
    st.forEach(([a, b], i) => {
      const yy = y + 1.3 + i * 1.22;
      s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: yy + 0.05, w: 0.72, h: 0.72, fill: { color: C.ink }, line: { color: C.ink } });
      T(String(i + 1), { x: x + 0.3, y: yy + 0.05, w: 0.72, h: 0.72, fontSize: 26, bold: true, color: C.amber, align: "center", valign: "middle" });
      if (i < 3) vline(x + 0.66, yy + 0.8, yy + 1.25, C.ink, { w: 2.5, noArrow: true });
      T(a, { x: x + 1.2, y: yy, w: 4.0, h: 0.45, fontSize: 22, bold: true });
      T(b, { x: x + 1.2, y: yy + 0.43, w: 4.0, h: 0.75, fontSize: 17, color: C.muted });
    });
    s.addImage({ path: IMG("docs/images/control/evacuation.png"), x: x + 5.35, y: y + 1.35, w: 6.45, h: 4.03, altText: "Evacuation in the 3D control app" });
    rect(x + 5.35, y + 1.35, 6.45, 4.03, "FFFFFF", C.ink, { lw: 1.5, fill: { type: "none" } });
    T("Live 3D control app: routes bend around a gas leak, every exit sign updates", { x: x + 5.35, y: y + 5.45, w: 6.45, h: 0.85, fontSize: 17, italic: true, color: C.muted });
  }

  // ================================================================ 07 repeater designed for the mine
  {
    const [y, h] = rows.C, x = X0 + 12.1 + G, w = 12.6;
    sec(x, y, w, h, 7, "Repeater: built for the mine");
    const ih = h - 1.45, iw = ih * 1056 / 1262, ix = x + (w - iw) / 2, iy = y + 1.2;
    s.addImage({ path: PI("repeater_case.png"), x: ix, y: iy, w: iw, h: ih, altText: "Repeater enclosure 3D render" });
    const P = (rx, ry) => [ix + rx * iw, iy + ry * ih];
    const L = [["CH₄ port on top", "methane rises; rain chimney", P(0.86, 0.06), 1], ["LED exit sign", "arrow + metres, under a drip hood", P(0.45, 0.2), 0],
               ["IP65 gasket", "silicone cord, 6 × M4", P(0.98, 0.45), 1], ["85 dB buzzer", "works if the hub is down", P(0.1, 0.73), 0],
               ["Guarded SOS", "glove-sized, knock-proof", P(0.72, 0.82), 1], ["CO / H₂S below", "heavier gases; flame arrestors", P(0.33, 0.93), 0]];
    const lw = (w - iw) / 2 - 0.35;
    const ys = { 0: [y + 1.3, y + 3.0, y + 4.7], 1: [y + 1.3, y + 3.0, y + 4.7] }, used = { 0: 0, 1: 0 };
    for (const [t, d, [px, py], side] of L) {
      const yy = ys[side][used[side]++];
      const tx = side === 0 ? x + 0.25 : ix + iw + 0.1;
      T(t, { x: tx, y: yy, w: lw, h: 0.45, fontSize: 21, bold: true, color: C.orange, align: side ? "right" : "left" });
      T(d, { x: tx, y: yy + 0.45, w: lw, h: 0.85, fontSize: 17, align: side ? "right" : "left" });
      const lyy = yy + 0.22, from = side === 0 ? x + 0.25 + lw - 0.05 : ix + iw + 0.15;
      hline(from, px, lyy, C.orange, { w: 2, noArrow: true });
      vline(px, lyy, py, C.orange, { w: 2, noArrow: true });
      dot(px, py, 0.12);
    }
  }

  // ================================================================ 08 electrical + PCB
  {
    const [y, h] = rows.C, x = X0 + 12.1 + 12.6 + 2 * G, w = W - 12.1 - 12.6 - 2 * G;
    sec(x, y, w, h, 8, "Electrical design and PCBs");
    // power path
    const py = y + 1.35;
    rrect(x + 0.3, py, 2.0, 0.8, "FFFFFF", C.ink, { lw: 2 }); T("Mine 9–30 V", { x: x + 0.3, y: py, w: 2.0, h: 0.8, fontSize: 18, bold: true, align: "center", valign: "middle" });
    rrect(x + 0.3, py + 1.0, 2.0, 0.8, "FFFFFF", C.blue, { lw: 2 }); T("Battery 12 V", { x: x + 0.3, y: py + 1.0, w: 2.0, h: 0.8, fontSize: 18, bold: true, align: "center", valign: "middle", color: C.blue });
    const chain = [["Diode OR", "no reset"], ["Fuse + TVS", "1.6 A · 36 V"], ["5 V buck", "2 A, 90 %"], ["XIAO · 3 MQ · matrix", "≈ 3.7 W"]];
    const cw = [1.85, 1.95, 1.85, 2.55], cg = (w - 0.6 - 2.0 - cw.reduce((a, b) => a + b, 0)) / 4;
    let cx = x + 0.3 + 2.0 + cg;
    hline(x + 2.3, cx, py + 0.4, C.ink, { w: 2.5 }); hline(x + 2.3, cx, py + 1.4, C.blue, { w: 2.5 });
    chain.forEach(([a, b], i) => {
      rrect(cx, py, cw[i], 1.8, i === 3 ? C.soft : "FFFFFF", i === 3 ? C.amber : C.ink, { lw: 2 });
      T(a, { x: cx + 0.05, y: py + 0.2, w: cw[i] - 0.1, h: 0.85, fontSize: 19, bold: true, align: "center", valign: "middle" });
      T(b, { x: cx + 0.05, y: py + 1.05, w: cw[i] - 0.1, h: 0.55, fontSize: 16, align: "center", color: C.muted });
      if (i < 3) hline(cx + cw[i], cx + cw[i] + cg, py + 0.9, C.ink, { w: 2.5 });
      cx += cw[i] + cg;
    });
    // boards
    const B = [["hardware/repeater_pcb/renders/pcb_top.png", 1600 / 1200, "Repeater"], ["hardware/suit_pcb/core/renders/core_top.png", 1600 / 1310, "Core"],
               ["hardware/suit_pcb/cuff/renders/cuff_top.png", 1600 / 1461, "Cuff"], ["hardware/suit_pcb/helmet/renders/helmet_top.png", 1600 / 1746, "Helmet"],
               ["hardware/suit_pcb/boot/renders/boot_top.png", 1600 / 1977, "Boot"]];
    const bh = 1.75, tot = B.reduce((a, b) => a + b[1] * bh, 0), bg = (w - 0.6 - tot) / 4;
    let bxx = x + 0.3; const byy = y + 3.5;
    for (const [p, ar, lab] of B) {
      s.addImage({ path: IMG(p), x: bxx, y: byy, w: ar * bh, h: bh, altText: lab + " PCB" });
      T(lab, { x: bxx - 0.2, y: byy + bh + 0.05, w: ar * bh + 0.4, h: 0.4, fontSize: 17, bold: true, align: "center" });
      bxx += ar * bh + bg;
    }
    T("5 own 2-layer boards · KiCad + Freerouting · 100 % routed · 0 unconnected pads", { x: x + 0.3, y: y + h - 0.6, w: w - 0.6, h: 0.45, fontSize: 17, italic: true, color: C.muted, align: "center" });
  }

  // ================================================================ 09 energy
  const [dy, dh] = rows.D;
  const dw = [9.4, 9.0, 11.3]; const dw4 = W - dw.reduce((a, b) => a + b, 0) - 3 * G;
  const dx = [X0, X0 + dw[0] + G, X0 + dw[0] + dw[1] + 2 * G, X0 + dw[0] + dw[1] + dw[2] + 3 * G];
  {
    const x = dx[0], w = dw[0], y = dy, h = dh;
    sec(x, y, w, h, 9, "Energy budget");
    s.addChart(pres.charts.BAR, [{ name: "Hours", labels: ["Repeater backup", "Core pod", "Helmet pod*", "Boot pod*"], values: [7, 21, 56, 92] }], {
      x: x + 0.2, y: y + 1.15, w: w - 0.4, h: h - 2.0, barDir: "bar", chartColors: [C.amber], barGapWidthPct: 45, catAxisOrientation: "maxMin",
      showValue: true, dataLabelPosition: "outEnd", dataLabelColor: C.ink, dataLabelFontSize: 22, dataLabelFontBold: true, dataLabelFontFace: F, dataLabelFormatCode: '0" h"',
      catAxisLabelColor: C.ink, catAxisLabelFontSize: 20, catAxisLabelFontFace: F, valAxisHidden: true, valAxisMaxVal: 110,
      valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false });
    T("Hours on one charge; a shift is 12 h. *duty-cycled radio. Repeater ≈ 3.7 W on mine power.", { x: x + 0.3, y: y + h - 0.85, w: w - 0.6, h: 0.75, fontSize: 16, italic: true, color: C.muted });
  }
  // ================================================================ 10 cost
  {
    const x = dx[1], w = dw[1], y = dy, h = dh;
    sec(x, y, w, h, 10, "Cost");
    s.addChart(pres.charts.DOUGHNUT, [{ name: "Suit cost", labels: ["Core pod", "Helmet pod", "Wrist cuff", "Boot pod", "Fabric + sensing"], values: [2790, 2260, 1480, 3270, 3040] }], {
      x: x + 0.35, y: y + 1.1, w: 3.9, h: 3.4, holeSize: 55, chartColors: [C.amber, C.orange, C.teal, C.blue, "8A949C"], showLegend: false,
      showPercent: false, showValue: false, dataBorder: { pt: 2, color: "FFFFFF" } });
    T([{ text: "₹12.8k", options: { bold: true, fontSize: 30, breakLine: true } }, { text: "per suit", options: { fontSize: 17, color: C.muted } }],
      { x: x + 1.2, y: y + 2.3, w: 2.2, h: 1.0, align: "center", valign: "middle", fontFace: F });
    const lg = [["Boot pod", "3,270", C.blue], ["Fabric + sensing", "3,040", "8A949C"], ["Core pod", "2,790", C.amber], ["Helmet pod", "2,260", C.orange], ["Wrist cuff", "1,480", C.teal]];
    lg.forEach(([a, b, col], i) => {
      const yy = y + 1.35 + i * 0.62;
      rect(x + 4.6, yy + 0.1, 0.32, 0.32, col);
      T(a, { x: x + 5.05, y: yy, w: 2.6, h: 0.5, fontSize: 18 });
      T(b, { x: x + 7.4, y: yy, w: 1.35, h: 0.5, fontSize: 18, bold: true, align: "right" });
    });
    rect(x + 0.3, y + h - 1.3, w - 0.6, 1.05, C.soft);
    T([{ text: "₹6,862", options: { bold: true, color: C.orange } }, { text: " / repeater   ·   " }, { text: "₹3.26 L", options: { bold: true, color: C.orange } }, { text: " for 10 repeaters + 20 suits" }],
      { x: x + 0.45, y: y + h - 1.3, w: w - 0.9, h: 1.05, fontSize: 19, valign: "middle", align: "center" });
  }
  // ================================================================ 11 validation
  {
    const x = dx[2], w = dw[2], y = dy, h = dh;
    sec(x, y, w, h, 11, "Validation");
    const ok = "Passed", ip = "In progress", pl = "Planned";
    const rowsV = [["Test", "Pass criterion", "Status"], ["PCB DRC, 5 boards", "0 unconnected pads", ok], ["CAD fit, 5 cases", "no collisions", ok],
      ["Power budget", "core pod ≥ 12 h (21 h)", ok], ["Repeater chain", "self-forms, 3 / 3", ok], ["Gas + local buzzer", "alarm at limit", ok],
      ["Distance error", "≤ 5 % over 100 m", ip], ["Alert latency", "≤ 3 s for 95 %", pl], ["Fall detection", "≥ 90 %, ≤ 1 false / h", pl]];
    const sc = { [ok]: C.green, [ip]: C.orange, [pl]: "8A949C" };
    s.addTable(rowsV.map((r, ri) => r.map((v, ci) => ({ text: v, options: {
      bold: ri === 0 || ci === 2, color: ri === 0 || (ci === 2 && ri > 0) ? "FFFFFF" : C.ink, fontSize: ri === 0 ? 19 : 18,
      fill: { color: ri === 0 ? C.ink2 : ci === 2 ? sc[v] : ri % 2 ? "FFFFFF" : "F7F4EE" }, align: ci === 2 ? "center" : "left", valign: "middle" } }))),
      { x: x + 0.3, y: y + 1.25, w: w - 0.6, colW: [3.9, 4.25, 2.55], rowH: 0.5, fontFace: F, border: { type: "solid", color: C.line, pt: 1 }, margin: [0, 0.1, 0, 0.12] });
  }
  // ================================================================ 12 conclusion + outcome
  {
    const x = dx[3], w = dw4, y = dy, h = dh;
    sec(x, y, w, h, 12, "Conclusion");
    T([{ text: "Every worker ", options: {} }, { text: "checked, monitored, located and reachable", options: { bold: true, color: C.orange } },
       { text: " for the whole shift, on hardware a small mine can install itself." }], { x: x + 0.3, y: y + 1.2, w: w - 0.6, h: 1.4, fontSize: 20 });
    const out = ["Working V3 prototype: 3 repeaters, body unit, hub, 3D app", "V4: 5 PCBs, 5 mine-rated cases, smart suit", "Next: LoRa backbone, certified gas sensors, mine trial"];
    T(out.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < out.length - 1 } })), { x: x + 0.3, y: y + 2.6, w: w - 0.6, h: 1.75, fontSize: 18, paraSpaceAfter: 4 });
    const sdg = [["3", "Good health", "4C9F38"], ["8", "Decent work", "A21942"], ["9", "Industry", "FD6925"]];
    const sw = (w - 0.6 - 0.3) / 3;
    sdg.forEach(([n, t, col], i) => {
      const sx = x + 0.3 + i * (sw + 0.15);
      rect(sx, y + h - 1.2, sw, 0.95, col);
      T([{ text: "SDG " + n, options: { bold: true, fontSize: 19, breakLine: true } }, { text: t, options: { fontSize: 14 } }],
        { x: sx, y: y + h - 1.2, w: sw, h: 0.95, color: "FFFFFF", align: "center", valign: "middle" });
    });
  }

  // ---------------------------------------------------------------- references strip
  T([{ text: "References  ", options: { bold: true } },
     { text: "[1] Ministry of Mines data, ETV Bharat, Aug 2026 · [2] Coal Mines Regulations 2017, reg. 153 · [3] NIOSH Pocket Guide to Chemical Hazards · [4] Bandyopadhyay et al., Wireless Information and Safety System for Mines, JSIR 2009 · [5] IMU-assisted UWB positioning in underground coal mines, Micromachines 2023 · [6] Real-time PPE compliance detection (YOLO), Sustainability 2023" }],
    { x: 1.15, y: bot + 0.12, w: S - 2.3, h: 0.95, fontSize: 17, color: C.muted, valign: "middle" });

  await pres.writeFile({ fileName: OUT });
  console.log("wrote", OUT);
})();
