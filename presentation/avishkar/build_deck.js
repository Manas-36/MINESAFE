// MineSafe — Avishkar podium deck in the official convention slide format:
// bordered frame, "Inter-University Avishkar Research Convention" at top centre, Category (left), Level (right), Slot No. (bottom).
// Anonymous by rule: no college, guide or student names anywhere. 14 slides, about 6:40.
// 3D models: picture placeholders named M3D_<model>, replaced by add_3d_models.py with native PowerPoint 3D models (glb).
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const path = require("path");
const { applyTheme } = require("/root/.claude/skills/synced/c2e8f71d-f377-4681-b29e-484210bc5b66_2143c34c-7913-4352-9dd0-e9350e70e053/pptx/scripts/apply_theme.js");

const R = path.resolve(__dirname, "..", "..");
const IMG = (p) => path.join(R, p);
const OUT = path.join(__dirname, "build", "MineSafe_Avishkar_base.pptx");
const CONVENTION = "Inter-University Avishkar Research Convention:  2026-27";
const CATEGORY = "Engineering & Technology", LEVEL = "UG";

const THEME = {
  name: "MineSafe Avishkar", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "1B2329", lt1: "FFFFFF", dk2: "2C3840", lt2: "F4F1EA", accent1: "F2A900", accent2: "E8710A", accent3: "2E8B57",
            accent4: "2F5F9E", accent5: "8A949C", accent6: "C8102E", hlink: "2F5F9E", folHlink: "1F7A6D" },
};
const H = { ink: "1B2329", ink2: "2C3840", amber: "F2A900", orange: "E8710A", accent: "B85C00", red: "C8102E", green: "2E8B57", blue: "2F5F9E",
            teal: "1F7A6D", grey: "8A949C", panel: "F4F1EA", panel2: "EAE4D7", soft: "FFF6DB", line: "D8D1C2", muted: "5B6670" };
const F = "Calibri", FH = "Cambria";

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";            // 13.33 x 7.5 in
  pres.title = "MineSafe";
  pres.theme = { headFontFace: FH, bodyFontFace: F };

  // ---------------------------------------------------------------- official frame layout
  const frame = [
    { rect: { x: 0.25, y: 0.22, w: 12.83, h: 7.06, fill: { type: "none" }, line: { color: H.ink, width: 1.25 } } },
    { text: { text: CONVENTION, options: { x: 2.4, y: 0.3, w: 8.53, h: 0.36, fontSize: 15, bold: true, color: H.ink, fontFace: F, align: "center", margin: 0 } } },
    { text: { text: "Category:  " + CATEGORY, options: { x: 0.45, y: 0.6, w: 5, h: 0.3, fontSize: 12, bold: true, color: H.ink, fontFace: F, margin: 0 } } },
    { text: { text: "Level:  " + LEVEL, options: { x: 7.9, y: 0.6, w: 4.98, h: 0.3, fontSize: 12, bold: true, color: H.ink, fontFace: F, align: "right", margin: 0 } } },
    { text: { text: "Slot No.:  __________", options: { x: 4.67, y: 6.9, w: 4, h: 0.3, fontSize: 12, bold: true, color: H.ink, fontFace: F, align: "center", margin: 0 } } },
  ];
  pres.defineSlideMaster({ title: "AV_TITLE", background: { color: "FFFFFF" }, objects: frame });
  pres.defineSlideMaster({
    title: "AV_CONTENT", background: { color: "FFFFFF" }, margin: [1.0, 0.45, 0.6, 0.45],
    objects: [...frame,
      { rect: { x: 0.45, y: 1.08, w: 0.09, h: 0.5, fill: { color: H.amber }, line: { color: H.amber } } },
      { placeholder: { options: { name: "title", type: "title", x: 0.68, y: 1.0, w: 12.2, h: 0.66, fontSize: 25, bold: true, color: H.ink, fontFace: FH, valign: "middle", align: "left", margin: 0 }, text: "" } }],
    slideNumber: { x: 12.3, y: 6.9, w: 0.58, h: 0.3, fontSize: 11, color: H.muted, fontFace: F, align: "right" },
  });

  const card = (s, x, y, w, h, fill = H.panel, line) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: line || fill, width: line ? 1.25 : 0.5 }, rectRadius: 0.06 });
  const txt = (s, t, o) => s.addText(t, { isTextBox: true, fontFace: F, color: H.ink, margin: 0, valign: "top", ...o });
  const model = (s, name, x, y, w, h) => s.addImage({ path: IMG(`hardware/glb/preview/${name}.png`), x, y, w, h, objectName: `M3D_${name}`, sizing: { type: "contain", w, h }, altText: `3D model: ${name.replace(/_/g, " ")} (rotate with the mouse)` });
  const hline = (s, x1, x2, y, col = H.ink, o = {}) => s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y, w: Math.abs(x2 - x1), h: 0, flipH: x2 < x1,
    line: { color: col, width: o.w || 1.75, dashType: o.dash || "solid", endArrowType: o.noArrow ? undefined : "triangle" } });
  const vline = (s, x, y1, y2, col = H.ink, o = {}) => s.addShape(pres.shapes.LINE, { x, y: Math.min(y1, y2), w: 0, h: Math.abs(y2 - y1), flipV: y2 < y1,
    line: { color: col, width: o.w || 1.75, dashType: o.dash || "solid", endArrowType: o.noArrow ? undefined : "triangle" } });
  const iconCircle = async (s, Ic, x, y, d = 0.62, fill = H.soft, col = H.ink) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: H.amber, width: 1.5 } });
    s.addImage({ data: await icon(Ic, col), x: x + d * 0.26, y: y + d * 0.26, w: d * 0.48, h: d * 0.48 });
  };
  const chartText = { catAxisLabelColor: H.ink, catAxisLabelFontFace: F, valAxisLabelColor: H.muted, valAxisLabelFontFace: F, dataLabelFontFace: F, titleFontFace: F, titleColor: H.ink };

  // ================================================================ 1. title (Annexure 2: convention, category, level, slot only)
  {
    const s = pres.addSlide({ masterName: "AV_TITLE" });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 1.1, w: 8.0, h: 5.55, fill: { color: H.ink }, line: { color: H.ink } });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 1.1, w: 0.14, h: 5.55, fill: { color: H.amber }, line: { color: H.amber } });
    s.addImage({ data: await icon(fa.FaHardHat, H.amber, 512), x: 0.95, y: 1.5, w: 1.1, h: 1.1 });
    txt(s, "MineSafe", { x: 2.25, y: 1.4, w: 6.0, h: 1.3, fontSize: 66, bold: true, color: H.amber, fontFace: FH, valign: "middle" });
    txt(s, "Intelligent Safety Gear Compliance, Health Monitoring and Navigation System for Underground Miners",
        { x: 0.95, y: 2.95, w: 7.2, h: 1.4, fontSize: 24, color: "FFFFFF", fontFace: FH });
    const chips = [[fa.FaSatelliteDish, "No GPS"], [fa.FaWifi, "No internet"], [fa.FaPlug, "No new cabling"]];
    for (let i = 0; i < chips.length; i++) {
      const x = 0.95 + i * 2.4;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 4.75, w: 2.2, h: 0.55, rectRadius: 0.27, fill: { color: H.ink2 }, line: { color: H.amber, width: 1.25 } });
      s.addImage({ data: await icon(chips[i][0], H.amber), x: x + 0.18, y: 4.88, w: 0.3, h: 0.3 });
      txt(s, chips[i][1], { x: x + 0.55, y: 4.75, w: 1.6, h: 0.55, fontSize: 15, bold: true, color: "FFFFFF", valign: "middle" });
    }
    txt(s, "Checked at the gate · monitored all shift · located without GPS · reachable in seconds", { x: 0.95, y: 5.6, w: 7.2, h: 0.7, fontSize: 15, color: "D9D3C5", italic: true });
    model(s, "smart_suit", 8.75, 1.05, 4.1, 5.7);
    s.addNotes("0:00–0:15. Say the slot number only — never your name or college. The suit on the right is a live 3D model: click and drag to turn it.");
  }

  // ================================================================ 2. problem
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("Underground, nobody knows who is where — or if they are alive", { placeholder: "title" });
    s.addChart(pres.charts.BAR, [{ name: "Deaths", labels: ["2023", "2024", "2025"], values: [41, 49, 51] }], {
      x: 0.45, y: 1.8, w: 3.9, h: 4.85, barDir: "col", chartColors: [H.red], barGapWidthPct: 50, showValue: true, dataLabelPosition: "outEnd",
      dataLabelColor: H.ink, dataLabelFontSize: 16, dataLabelFontBold: true, catAxisLabelFontSize: 14, valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 60,
      valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, showTitle: true, title: "Coal-mine deaths, India", titleFontSize: 14, ...chartText });
    const st = [["141", "deaths, 2023–25", H.red], ["355", "serious accidents", H.orange], ["0", "GPS or phone signal underground", H.ink]];
    st.forEach(([b, l, c], i) => {
      const y = 1.85 + i * 1.62;
      s.addShape(pres.shapes.RECTANGLE, { x: 4.55, y, w: 0.07, h: 1.35, fill: { color: c }, line: { color: c } });
      txt(s, b, { x: 4.75, y: y - 0.05, w: 2.4, h: 0.8, fontSize: 44, bold: true, color: c, fontFace: FH });
      txt(s, l, { x: 4.75, y: y + 0.78, w: 2.4, h: 0.55, fontSize: 13, color: H.muted });
    });
    const inc = [["SLBC tunnel, Telangana · 2025", "8 trapped — ground radar needed to find them"], ["Umrangso, Assam · 2025", "flooded mine, 150+ hour search"],
                 ["Kolihan, Rajasthan · 2024", "cage rope snapped, 15 trapped, 1 died"], ["Ksan, Meghalaya · 2018", "15 trapped, about 80-day search"]];
    inc.forEach(([h, d], i) => {
      const y = 1.8 + i * 1.23;
      card(s, 7.35, y, 5.53, 1.1);
      txt(s, h, { x: 7.6, y: y + 0.14, w: 5.1, h: 0.38, fontSize: 16, bold: true, color: H.accent });
      txt(s, d, { x: 7.6, y: y + 0.55, w: 5.1, h: 0.42, fontSize: 14 });
    });
    s.addNotes("0:15–0:45. Source: Ministry of Mines data (ETV Bharat, Aug 2026). Every rescue shows the same gap: no last known position, no vitals, no way to tell each worker which way to go.");
  }

  // ================================================================ 3. gap & novelty
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("No existing system combines kit check, vitals and GPS-free location", { placeholder: "title" });
    const Y = "✓", N = "✗", P = "~";
    const rows = [["Product", "Kit check", "Vitals", "Fall alert", "GPS-free location", "Gas", "Public price"],
      ["Teknovate MineGuard 360", N, Y, P, P, Y, "quote only"], ["MineARC GuardIAN", N, N, P, "zone", Y, "quote only"], ["Leantegra (UWB)", N, N, N, Y, Y, "quote only"],
      ["Rajant Health", "tag", Y, Y, P, P, "quote only"], ["EasyM2M SmartKavach", N, P, Y, N, N, "quote only"], ["36Zero + Bodytrak", P, Y, Y, N, N, "quote only"],
      ["MineSafe", Y, Y, Y, Y, Y, "₹6.9k / ₹12.8k"]];
    const cell = (v, r, c) => {
      const head = r === 0, last = r === rows.length - 1;
      let color = H.ink;
      if (!head && !last && c > 0 && c < 6) color = v === Y ? H.green : v === N ? H.red : H.orange;
      if (!head && !last && c === 6) color = H.muted;
      return { text: v, options: { bold: head || last || (c > 0 && c < 6), color: head ? "FFFFFF" : color,
        fill: { color: last ? H.amber : head ? H.ink2 : r % 2 ? "FFFFFF" : H.panel }, align: c === 0 ? "left" : "center",
        fontSize: head ? 13 : (c > 0 && c < 6 && v.length === 1 ? 17 : 14), valign: "middle" } };
    };
    s.addTable(rows.map((r, ri) => r.map((v, ci) => cell(v, ri, ci))), { x: 0.45, y: 1.85, w: 12.43, colW: [3.3, 1.35, 1.25, 1.35, 2.05, 1.05, 2.08],
      rowH: 0.5, fontFace: F, border: { type: "solid", color: H.line, pt: 1 }, margin: [0, 0.12, 0, 0.12] });
    card(s, 0.45, 5.95, 12.43, 0.75, H.soft);
    txt(s, [{ text: "What is new:  ", options: { bold: true, color: H.accent } },
            { text: "one integrated network · location without GPS or new infrastructure · repeaters that are also exit signs · a suit that checks the kit all shift · small-mine price" }],
        { x: 0.65, y: 5.95, w: 12.0, h: 0.75, fontSize: 14, valign: "middle" });
    s.addNotes("0:45–1:10. Nine commercial products checked (July 2026). Do not claim to beat Leantegra on positioning — the point is the integration and the cost.");
  }

  // ================================================================ 4. methodology: architecture + shift flowchart
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("Methodology: one self-healing network from the gate to the control room", { placeholder: "title" });
    const ay = 2.15, bh = 1.45;
    const boxes = [["Smart suit", "4 pods: vitals, fall, kit, steps", 2.3, true, fa.FaUserShield], ["REP-03", "gas · air · exit sign", 1.65, false, fa.FaBroadcastTower],
                   ["REP-02", "gas · air · exit sign", 1.65, false, fa.FaBroadcastTower], ["REP-01", "main repeater", 1.65, false, fa.FaBroadcastTower],
                   ["Hub laptop", "API · AI kit check · evacuation planner", 2.3, true, fa.FaServer], ["3D control app", "browser or phone", 1.75, false, fa.FaDesktop]];
    const gap = (12.43 - boxes.reduce((a, b) => a + b[2], 0)) / (boxes.length - 1);
    let cx = 0.45; const xs = [];
    for (const [t, sub, w, hi, Ic] of boxes) {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx, y: ay, w, h: bh, rectRadius: 0.08, fill: { color: hi ? H.soft : "FFFFFF" }, line: { color: hi ? H.amber : H.ink, width: hi ? 2 : 1.25 } });
      s.addImage({ data: await icon(Ic, hi ? H.orange : H.ink), x: cx + w / 2 - 0.17, y: ay + 0.1, w: 0.34, h: 0.34 });
      txt(s, t, { x: cx, y: ay + 0.48, w, h: 0.35, fontSize: 15, bold: true, align: "center" });
      txt(s, sub, { x: cx + 0.08, y: ay + 0.84, w: w - 0.16, h: 0.58, fontSize: 11.5, align: "center", color: H.muted });
      xs.push([cx, w]); cx += w + gap;
    }
    ["ESP-NOW", "ESP-NOW", "ESP-NOW", "Wi-Fi", "Wi-Fi"].forEach((l, i) => {
      const x1 = xs[i][0] + xs[i][1], x2 = xs[i + 1][0];
      hline(s, x1 + 0.02, x2 - 0.02, ay + bh / 2, H.orange, { w: 2.25 });
      txt(s, l, { x: x1 - 0.3, y: ay - 0.3, w: x2 - x1 + 0.6, h: 0.25, fontSize: 10.5, bold: true, color: H.orange, align: "center" });
    });
    const rx1 = xs[4][0] + 1.15, rx0 = xs[0][0] + 1.15, ry = ay + bh + 0.28;
    vline(s, rx1, ay + bh, ry, H.blue, { dash: "dash", noArrow: true }); hline(s, rx1, rx0, ry, H.blue, { dash: "dash", noArrow: true }); vline(s, rx0, ry, ay + bh + 0.02, H.blue, { dash: "dash" });
    txt(s, "alerts and evacuation routes return down the same chain · data stays on site", { x: rx0 + 0.3, y: ry + 0.04, w: rx1 - rx0 - 0.6, h: 0.28, fontSize: 11.5, italic: true, color: H.blue, align: "center" });

    const fy = 4.75, fh = 1.0;
    txt(s, "WORKER'S SHIFT", { x: 0.45, y: fy - 0.42, w: 4, h: 0.3, fontSize: 12, bold: true, color: H.accent, charSpacing: 2 });
    const nodes = [["Kit up", "suit self-checks", 1.5, "b"], ["Entry check", "ID card + YOLOv8 photo", 1.85, "b"], ["Kit OK?", "", 1.35, "d"],
                   ["Underground", "vitals · steps · gas, 1 / s", 2.0, "b"], ["Alarm?", "", 1.35, "d"], ["Alert + route", "exit signs, cuff, voice", 1.95, "h"], ["Exit scan", "dock charges", 1.5, "b"]];
    const g2 = (12.43 - nodes.reduce((a, b) => a + b[2], 0)) / (nodes.length - 1);
    let nx = 0.45; const ns = [];
    for (const [t, sub, w, k] of nodes) {
      if (k === "d") {
        s.addShape(pres.shapes.DIAMOND, { x: nx, y: fy - 0.1, w, h: fh + 0.2, fill: { color: H.amber }, line: { color: H.ink, width: 1.25 } });
        txt(s, t, { x: nx, y: fy - 0.1, w, h: fh + 0.2, fontSize: 13, bold: true, align: "center", valign: "middle" });
      } else {
        s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: nx, y: fy, w, h: fh, rectRadius: 0.08, fill: { color: k === "h" ? "FBE3E6" : "FFFFFF" }, line: { color: k === "h" ? H.red : H.ink, width: 1.25 } });
        txt(s, t, { x: nx, y: fy + 0.1, w, h: 0.32, fontSize: 14, bold: true, align: "center", color: k === "h" ? H.red : H.ink });
        txt(s, sub, { x: nx + 0.06, y: fy + 0.44, w: w - 0.12, h: 0.5, fontSize: 11, align: "center", color: H.muted });
      }
      ns.push([nx, w]); nx += w + g2;
    }
    for (let i = 0; i < ns.length - 1; i++) hline(s, ns[i][0] + ns[i][1] + 0.02, ns[i + 1][0] - 0.02, fy + fh / 2);
    txt(s, "yes", { x: ns[2][0] + ns[2][1] - 0.15, y: fy + 0.12, w: g2 + 0.3, h: 0.22, fontSize: 10.5, bold: true, color: H.green, align: "center" });
    txt(s, "yes", { x: ns[4][0] + ns[4][1] - 0.15, y: fy + 0.12, w: g2 + 0.3, h: 0.22, fontSize: 10.5, bold: true, color: H.red, align: "center" });
    const loop = (from, to, col, label) => {
      const a = ns[from][0] + ns[from][1] / 2, b = ns[to][0] + ns[to][1] / 2, yy = fy + fh + 0.32;
      vline(s, a, fy + fh + 0.08, yy, col, { noArrow: true }); hline(s, a, b, yy, col, { noArrow: true }); vline(s, b, yy, fy + fh + 0.02, col);
      txt(s, label, { x: b + 0.12, y: yy + 0.03, w: 3, h: 0.26, fontSize: 11, bold: true, color: col });
    };
    loop(2, 0, H.red, "no → rejected, fix kit");
    loop(4, 3, H.green, "no → keep monitoring");
    s.addNotes("1:10–1:45. Top: data flow left to right, alerts come back on the dashed path. Bottom: the worker's shift — the system runs on its own after the gate.");
  }

  // ================================================================ 5. location + evacuation
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("Location without GPS, evacuation without guesswork", { placeholder: "title" });
    const steps = [["Count steps", "steps × stride along the gyro heading; pressure gives the level"], ["Snap to the tunnel", "position pulled onto the nearest tunnel on the mine map"],
                   ["Reset at repeaters", "signal ≥ −55 dBm = next to that repeater: drift goes to zero"], ["Route around danger", "Dijkstra from all exits; hazard tunnels cost 1000×; each exit sign shows arrow + metres"]];
    steps.forEach(([h, d], i) => {
      const y = 1.85 + i * 1.2;
      s.addShape(pres.shapes.OVAL, { x: 0.45, y: y + 0.05, w: 0.55, h: 0.55, fill: { color: H.ink }, line: { color: H.ink } });
      txt(s, String(i + 1), { x: 0.45, y: y + 0.05, w: 0.55, h: 0.55, fontSize: 18, bold: true, color: H.amber, align: "center", valign: "middle" });
      if (i < 3) vline(s, 0.725, y + 0.62, y + 1.23, H.ink, { noArrow: true, w: 1.5 });
      txt(s, h, { x: 1.2, y, w: 4.4, h: 0.36, fontSize: 16, bold: true });
      txt(s, d, { x: 1.2, y: y + 0.38, w: 4.4, h: 0.75, fontSize: 13, color: H.muted });
    });
    s.addImage({ path: IMG("docs/images/control/evacuation.png"), x: 5.9, y: 1.85, w: 6.98, h: 4.36, altText: "3D control room during an evacuation" });
    txt(s, "Live 3D control app during an evacuation: routes go around the gas leak, exit signs update", { x: 5.9, y: 6.3, w: 6.98, h: 0.35, fontSize: 12, color: H.muted, italic: true });
    s.addNotes("1:45–2:10. Integrating acceleration drifts about 175 m a minute — that is why we count steps and reset at every repeater. V4 adds a foot IMU that measures each real stride.");
  }

  // ================================================================ 6. design considerations
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("Design considerations: dust, water, methane, heat and blasting", { placeholder: "title" });
    const items = [[fa.FaTint, "Water and dust", "IP65 gasket, drip hood, every opening faces down"], [fa.FaFire, "Methane rises", "CH₄ port on top under a rain chimney; H₂S / CO at the bottom"],
      [fa.FaShieldAlt, "Ignition risk", "sintered flame-arrestor seat at every gas port"], [fa.FaThermometerHalf, "Heat 30–45 °C", "air sensor in its own chamber, away from heaters"],
      [fa.FaBomb, "Blasting shock", "screw bosses, latching connectors, rubber grommets"], [fa.FaBolt, "Power cuts", "mine supply + battery, switch-over with no reset"],
      [fa.FaLightbulb, "Dark and smoke", "LED exit signs, reflective hi-vis tape"], [fa.FaHandPaper, "Thick gloves", "16–22 mm buttons, vibration and voice alerts"]];
    for (let i = 0; i < items.length; i++) {
      const [Ic, h, d] = items[i], col = i % 4, row = Math.floor(i / 4), x = 0.45 + col * 3.15, y = 1.85 + row * 2.45;
      card(s, x, y, 2.98, 2.25);
      await iconCircle(s, Ic, x + 0.22, y + 0.22, 0.66);
      txt(s, h, { x: x + 0.22, y: y + 1.0, w: 2.6, h: 0.38, fontSize: 16, bold: true });
      txt(s, d, { x: x + 0.22, y: y + 1.4, w: 2.6, h: 0.8, fontSize: 13, color: H.muted });
    }
    s.addNotes("2:10–2:30. Every hardware decision starts from a mine condition. The suit is never locked — removal is detected, never prevented.");
  }

  // ================================================================ 7. repeater (3D)
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("Each repeater is a radio relay, gas station and exit sign", { placeholder: "title" });
    card(s, 0.45, 1.8, 5.0, 4.9, H.panel);
    model(s, "repeater_case", 0.6, 1.85, 4.7, 4.5);
    txt(s, "3D model — click and drag to turn it", { x: 0.45, y: 6.35, w: 5.0, h: 0.3, fontSize: 11, color: H.muted, italic: true, align: "center" });
    const f = [["Gas", "MQ-4 CH₄ (top) · MQ-7 CO · MQ-136 H₂S (bottom), Indian limits"], ["Air", "temperature, humidity, wet-bulb limit 30.5 / 33.5 °C"],
               ["Exit sign", "8×32 LED matrix: arrow + distance to the safe exit"], ["Alarm", "85 dB buzzer works even if the control room is down"],
               ["Power", "9–30 V mine supply or battery, ≈ 3.7 W, ≈ 7 h backup"], ["Case", "223 × 292 × 118 mm, IP65 target, rock-bolt / chain mount"]];
    f.forEach(([h, d], i) => {
      const y = 1.8 + i * 0.83;
      card(s, 5.75, y, 7.13, 0.72, i % 2 ? "FFFFFF" : H.panel, H.line);
      txt(s, h, { x: 5.95, y, w: 1.35, h: 0.72, fontSize: 15, bold: true, color: H.accent, valign: "middle" });
      txt(s, d, { x: 7.3, y, w: 5.45, h: 0.72, fontSize: 13.5, valign: "middle" });
    });
    s.addNotes("2:30–3:00. Turn the 3D model to show the CH4 chimney on top and the downward-facing ports. The same board runs as main repeater or tunnel repeater.");
  }

  // ================================================================ 8. electrical + PCB
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("Electrical design: five own PCBs, 100 % routed, 0 errors", { placeholder: "title" });
    s.addImage({ path: IMG("hardware/repeater_pcb/renders/repeater_schematic.png"), x: 0.45, y: 1.8, w: 7.5, h: 3.75, altText: "Repeater PCB schematic" });
    s.addImage({ path: IMG("hardware/repeater_pcb/renders/pcb_top.png"), x: 8.2, y: 1.8, w: 4.68, h: 3.51, altText: "Repeater PCB top render" });
    txt(s, "Repeater schematic and board, 100 × 75 mm, 2 layers, through-hole", { x: 0.45, y: 5.55, w: 7.5, h: 0.28, fontSize: 11, italic: true, color: H.muted });
    txt(s, "KiCad 7 + Freerouting, generated by our own script", { x: 8.2, y: 5.33, w: 4.68, h: 0.28, fontSize: 11, italic: true, color: H.muted, align: "center" });
    // power path flowchart
    const py = 5.95, ph = 0.75;
    const inBox = (t, y, col) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.45, y, w: 1.55, h: 0.34, rectRadius: 0.06, fill: { color: "FFFFFF" }, line: { color: col, width: 1.25 } });
      txt(s, t, { x: 0.45, y, w: 1.55, h: 0.34, fontSize: 12, bold: true, align: "center", valign: "middle", color: col });
    };
    inBox("Mine 9–30 V", py, H.ink); inBox("Battery 12 V", py + ph - 0.34, H.blue);
    const chain = [["Diode OR", "no reset on power cut", 2.0], ["Fuse + TVS", "1.6 A · 36 V", 1.9], ["5 V switcher", "2 A, ≈ 90 %", 1.9], ["XIAO · 3 MQ · matrix", "≈ 3.7 W total", 2.7]];
    const gap = (12.43 - 1.55 - chain.reduce((a, b) => a + b[2], 0)) / 4;
    let cx = 0.45 + 1.55 + gap;
    hline(s, 2.0, cx, py + 0.17); hline(s, 2.0, cx, py + ph - 0.17, H.blue);
    chain.forEach(([t, sub, w], i) => {
      const last = i === chain.length - 1;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx, y: py, w, h: ph, rectRadius: 0.06, fill: { color: last ? H.soft : "FFFFFF" }, line: { color: last ? H.amber : H.ink, width: 1.25 } });
      txt(s, t, { x: cx, y: py + 0.06, w, h: 0.34, fontSize: 13, bold: true, align: "center" });
      txt(s, sub, { x: cx, y: py + 0.4, w, h: 0.3, fontSize: 11, align: "center", color: H.muted });
      if (!last) hline(s, cx + w, cx + w + gap, py + ph / 2);
      cx += w + gap;
    });
    s.addNotes("3:00–3:25. Point at the power path: mine supply and battery are OR-ed by diodes, so a power cut never resets the repeater.");
  }

  // ================================================================ 9. smart suit (3D)
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("V4 smart suit: the kit checks itself all shift", { placeholder: "title" });
    card(s, 0.45, 1.8, 3.6, 4.9, H.panel);
    model(s, "smart_suit", 0.55, 1.85, 3.4, 4.8);
    const pods = [[fa.FaMicrochip, "Core pod · chest", "ESP32-C6, 3000 mAh, motion + pressure, guarded SOS"], [fa.FaHardHat, "Helmet pod", "antenna at head height, voice alerts, helmet-on switch"],
                  [fa.FaClock, "Wrist cuff", "screen, 3 glove buttons, vibration, heart rate + SpO₂"], [fa.FaShoePrints, "Boot pod", "foot IMU measures each real stride, heel force sensor"],
                  [fa.FaUserShield, "Seams and zip", "conductive thread + zip switch: torn or opened = alert"]];
    for (let i = 0; i < pods.length; i++) {
      const [Ic, h, d] = pods[i], y = 1.85 + i * 0.86;
      await iconCircle(s, Ic, 4.35, y + 0.05, 0.6);
      txt(s, h, { x: 5.15, y, w: 7.7, h: 0.36, fontSize: 16, bold: true });
      txt(s, d, { x: 5.15, y: y + 0.38, w: 7.7, h: 0.38, fontSize: 13.5, color: H.muted });
    }
    card(s, 4.35, 6.2, 8.53, 0.5, H.soft, H.amber);
    txt(s, "Never locked: removal or a tear is detected and reported, never prevented", { x: 4.55, y: 6.2, w: 8.2, h: 0.5, fontSize: 14, bold: true, color: H.accent, valign: "middle" });
    s.addNotes("3:25–3:50. Turn the suit to show the helmet pod at the back and the boot pod on the right heel. Helmet and boot talk to the core over ESP-NOW; only the cuff is wired.");
  }

  // ================================================================ 10. pods (3D x4)
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("Four pods, each designed around its own board", { placeholder: "title" });
    const P = [["pod_core", "Core pod", "118 × 93 × 44 mm", "21 h"], ["pod_cuff", "Wrist cuff", "88 × 75 × 27 mm", "wired to core"],
               ["pod_helmet", "Helmet pod", "75 × 66 × 31 mm", "56 h*"], ["pod_boot", "Boot pod", "57 × 58 × 29 mm", "92 h*"]];
    P.forEach(([m, h, d, b], i) => {
      const x = 0.45 + i * 3.15;
      card(s, x, 1.8, 2.98, 4.9);
      model(s, m, x + 0.1, 1.9, 2.78, 3.6);
      txt(s, h, { x, y: 5.55, w: 2.98, h: 0.38, fontSize: 17, bold: true, align: "center" });
      txt(s, `${d} · ${b}`, { x, y: 5.95, w: 2.98, h: 0.32, fontSize: 12.5, color: H.muted, align: "center" });
    });
    txt(s, "Lids lifted to show the board, battery and modules · every case fit-checked in CAD against its real KiCad board · *duty-cycled radio",
        { x: 0.45, y: 6.38, w: 12.43, h: 0.3, fontSize: 11, italic: true, color: H.muted, align: "center" });
    s.addNotes("3:50–4:05. Turn one pod if time allows. Four pods because each body position does one job best: radio at head height, stride at the foot, screen at the wrist, battery at the chest.");
  }

  // ================================================================ 11. energy
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("Energy budget: the core pod lasts almost two shifts", { placeholder: "title" });
    s.addChart(pres.charts.BAR, [{ name: "Battery life (h)", labels: ["Repeater backup", "Core pod", "Helmet pod*", "Boot pod*"], values: [7, 21, 56, 92] }], {
      x: 0.45, y: 1.8, w: 6.4, h: 4.45, barDir: "bar", chartColors: [H.amber], barGapWidthPct: 45, showValue: true, dataLabelPosition: "outEnd", dataLabelColor: H.ink,
      dataLabelFontSize: 14, dataLabelFontBold: true, dataLabelFormatCode: '0" h"', catAxisLabelFontSize: 14, valAxisHidden: true, valAxisMaxVal: 110,
      valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, showTitle: true, title: "Hours on one charge (a shift is 12 h)",
      titleFontSize: 14, catAxisOrientation: "maxMin", ...chartText });
    s.addChart(pres.charts.DOUGHNUT, [{ name: "Repeater power", labels: ["3 × MQ gas heaters", "LED matrix", "XIAO ESP32-C6 radio", "Sensors + logic"], values: [2.25, 0.60, 0.45, 0.03] }], {
      x: 7.1, y: 1.8, w: 5.78, h: 4.45, holeSize: 55, chartColors: [H.orange, H.amber, H.blue, H.grey], showLegend: true, legendPos: "r", legendFontSize: 12, legendFontFace: F, legendColor: H.ink,
      showPercent: true, showValue: false, dataLabelColor: "FFFFFF", dataLabelFontSize: 12, dataLabelFontBold: true, dataBorder: { pt: 1.5, color: "FFFFFF" },
      showTitle: true, title: "Where the repeater's 3.3 W goes (5 V rail)", titleFontSize: 14, ...chartText });
    txt(s, "* radio duty-cycled (V4 firmware). Datasheet estimates, to be confirmed by measurement. 10 repeaters ≈ 0.9 kWh / day ≈ ₹7 / day.",
        { x: 0.45, y: 6.33, w: 12.43, h: 0.35, fontSize: 11.5, color: H.muted, italic: true });
    s.addNotes("4:05–4:30. Core pod ≈ 112 mA at 3.3 V → ≈ 21 h from 3000 mAh. Two-thirds of the repeater's power is the gas-sensor heaters — that is why gas is measured on the repeaters, not on the body.");
  }

  // ================================================================ 12. component selection
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("Component selection: every choice against an alternative", { placeholder: "title" });
    const rows = [["Function", "Chosen", "Instead of", "Why"],
      ["Controller", "XIAO ESP32-C6", "ESP32-S3, Arduino + radio", "21 mm board; Wi-Fi 6, BLE, Zigbee and ESP-NOW on one chip; ≈ ₹600"],
      ["Worker ↔ repeater link", "ESP-NOW", "Zigbee, LoRa", "no re-joining for a moving worker; no extra hardware"],
      ["Location", "steps + repeater fixes", "UWB (DWM3000)", "UWB ≈ ₹2,000 per tag and anchor; steps cost nothing"],
      ["Kit identity", "PN532 NFC / ID card", "UHF RFID portal", "UHF reader ≈ ₹28,000; PN532 a few hundred rupees"],
      ["Gas (prototype)", "MQ-4 / MQ-7 / MQ-136", "electrochemical, NDIR", "₹150–400 each; hub accepts certified sensors later"],
      ["Regulator", "K7805 switcher", "linear 7805", "a linear 7805 would waste ≈ 11 W at 24 V input"],
      ["Exit sign", "MAX7219 8×32 matrix", "OLED, e-paper", "bright in smoke and darkness; ₹250–350"]];
    s.addTable(rows.map((r, ri) => r.map((v, ci) => ({ text: v, options: { bold: ri === 0 || ci === 1, color: ri === 0 ? "FFFFFF" : ci === 1 ? H.accent : ci === 2 ? H.muted : H.ink,
      fill: { color: ri === 0 ? H.ink2 : ri % 2 ? "FFFFFF" : H.panel }, fontSize: ri === 0 ? 13 : 13, valign: "middle" } }))),
      { x: 0.45, y: 1.85, w: 12.43, colW: [2.35, 2.55, 2.45, 5.08], rowH: 0.58, fontFace: F, border: { type: "solid", color: H.line, pt: 1 }, margin: [0, 0.1, 0, 0.12] });
    s.addNotes("4:30–4:55. Five criteria for every part: works underground, low cost, buyable in India, open library, upgradable to a certified part.");
  }

  // ================================================================ 13. validation
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("Validation: design and bench checks done, field tests next", { placeholder: "title" });
    const pills = [["4 / 4", "design checks passed", H.green], ["5 / 6", "bench tests passed", H.green], ["13", "field tests with numeric pass criteria", H.orange]];
    pills.forEach(([b, l, c], i) => {
      const x = 0.45 + i * 4.21;
      card(s, x, 1.8, 4.01, 0.85, H.panel);
      s.addShape(pres.shapes.RECTANGLE, { x, y: 1.8, w: 0.08, h: 0.85, fill: { color: c }, line: { color: c } });
      txt(s, b, { x: x + 0.25, y: 1.8, w: 1.3, h: 0.85, fontSize: 28, bold: true, color: c, fontFace: FH, valign: "middle" });
      txt(s, l, { x: x + 1.55, y: 1.8, w: 2.35, h: 0.85, fontSize: 13, valign: "middle" });
    });
    const ok = "Passed", ip = "In progress", pl = "Planned", sc = { [ok]: H.green, [ip]: H.orange, [pl]: H.grey };
    const rows = [["Test", "Method", "Pass criterion", "Status"],
      ["PCB electrical rules", "KiCad DRC, 5 boards", "0 unconnected pads", ok], ["Enclosure fit", "CAD collision check, 5 cases", "no collisions", ok],
      ["Repeater chain", "3 repeaters, any power-up order", "forms by itself, 3 / 3", ok], ["Gas + local buzzer", "MQ sensor + gas source", "alarm at the set limit", ok],
      ["Distance accuracy", "100 m corridor, 5 walkers", "error ≤ 5 %", ip], ["Alert latency", "3-hop chain, 50 trials", "≤ 3 s for 95 %", pl],
      ["Fall detection", "20 staged falls + 1 h normal", "≥ 90 %, ≤ 1 false / h", pl], ["Water / shock", "hose 30 min, 1 m drop, 45 °C", "no water, no reset", pl]];
    s.addTable(rows.map((r, ri) => r.map((v, ci) => ({ text: v, options: { bold: ri === 0 || ci === 3, fontSize: 12.5, valign: "middle", align: ci === 3 ? "center" : "left",
      color: ri === 0 || (ci === 3 && ri > 0) ? "FFFFFF" : ci === 1 ? H.muted : H.ink,
      fill: { color: ri === 0 ? H.ink2 : ci === 3 ? sc[v] : ri % 2 ? "FFFFFF" : H.panel } } }))),
      { x: 0.45, y: 2.85, w: 12.43, colW: [2.9, 3.9, 3.6, 2.03], rowH: 0.42, fontFace: F, border: { type: "solid", color: H.line, pt: 1 }, margin: [0, 0.1, 0, 0.12] });
    s.addNotes("4:55–5:35. Be honest: V3 is in field calibration. Each field test has a numeric pass criterion; results are logged with screenshots and video.");
  }

  // ================================================================ 14. cost, impact, conclusion
  {
    const s = pres.addSlide({ masterName: "AV_CONTENT" });
    s.addText("Affordable for small mines: checked, located, reachable", { placeholder: "title" });
    s.addChart(pres.charts.DOUGHNUT, [{ name: "Suit cost (₹)", labels: ["Boot pod", "Fabric + sensing", "Core pod", "Helmet pod", "Wrist cuff"], values: [3270, 3040, 2790, 2260, 1480] }], {
      x: 0.45, y: 1.75, w: 5.6, h: 3.6, holeSize: 55, chartColors: [H.blue, H.grey, H.amber, H.orange, H.teal], showLegend: true, legendPos: "r", legendFontSize: 12,
      legendFontFace: F, legendColor: H.ink, showValue: false, showPercent: false, dataBorder: { pt: 1.5, color: "FFFFFF" },
      showTitle: true, title: "One smart suit ≈ ₹12,800", titleFontSize: 14, ...chartText });
    const st = [["₹6,862", "per repeater"], ["₹12,800", "per smart suit"], ["₹3.26 L", "site: 10 repeaters + 20 suits"]];
    st.forEach(([b, l], i) => {
      const y = 1.85 + i * 1.15;
      card(s, 6.35, y, 6.53, 1.0, i === 2 ? H.soft : H.panel, i === 2 ? H.amber : undefined);
      txt(s, b, { x: 6.6, y, w: 2.6, h: 1.0, fontSize: 30, bold: true, color: H.accent, fontFace: FH, valign: "middle" });
      txt(s, l, { x: 9.2, y, w: 3.55, h: 1.0, fontSize: 14, valign: "middle" });
    });
    txt(s, "Every commercial system: enterprise quote only", { x: 6.35, y: 5.3, w: 6.53, h: 0.3, fontSize: 12, italic: true, color: H.muted, align: "center" });
    const sdg = [["SDG 3", "Good health", "4C9F38"], ["SDG 8", "Decent work", "A21942"], ["SDG 9", "Industry, innovation", "FD6925"]];
    sdg.forEach(([a, b, c], i) => {
      const x = 0.45 + i * 1.95;
      s.addShape(pres.shapes.RECTANGLE, { x, y: 5.75, w: 1.8, h: 0.9, fill: { color: c }, line: { color: c } });
      txt(s, [{ text: a, options: { bold: true, fontSize: 15, breakLine: true } }, { text: b, options: { fontSize: 11 } }], { x, y: 5.75, w: 1.8, h: 0.9, color: "FFFFFF", align: "center", valign: "middle" });
    });
    txt(s, [{ text: "Next: ", options: { bold: true, color: H.accent } }, { text: "LoRa backbone · certified gas sensors · intrinsic-safety design · field trial with a mine" }],
        { x: 6.35, y: 5.75, w: 4.6, h: 0.9, fontSize: 13, valign: "middle" });
    txt(s, "Thank you", { x: 11.0, y: 5.75, w: 1.88, h: 0.9, fontSize: 22, bold: true, color: H.accent, fontFace: FH, valign: "middle", align: "right" });
    s.addNotes("5:35–6:20. End on cost and impact (20 of 100 marks are economic efficiency and social relevance). Stop by 6:45 — over 7:15 disqualifies.");
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
