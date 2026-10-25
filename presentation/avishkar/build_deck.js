// MineSafe — Avishkar podium deck (anonymous: slot number only, no names / college, per MU Aavishkar rules)
// 13 slides, about 6.5 min. 3D models: picture placeholders named M3D_<model>, replaced by
// add_3d_models.py with native PowerPoint 3D models (glb) after this script runs.
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

const THEME = {
  name: "MineSafe Underground", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "12171A", lt1: "FFFFFF", dk2: "1E262B", lt2: "F3F0E8", accent1: "F2A900", accent2: "D93025", accent3: "3C8C6A",
            accent4: "4A6FA5", accent5: "9AA5AE", accent6: "E8710A", hlink: "F2A900", folHlink: "C9A24A" },
};
const H = { bg: "12171A", panel: "1E262B", panel2: "263038", amber: "F2A900", ink: "F3F0E8", muted: "AEB7BE", red: "E5554A", green: "4FB07E", blue: "6F96D1" };

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";            // 13.33 x 7.5 in
  pres.title = "MineSafe";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  // ---------------------------------------------------------------- layouts
  pres.defineSlideMaster({
    title: "MS_TITLE", background: { color: H.bg },
    objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.7, y: 1.55, w: 7.4, h: 1.3, fontSize: 60, bold: true, color: H.amber, fontFace: "Cambria", valign: "bottom", align: "left", margin: 0 }, text: "" } }],
  });
  pres.defineSlideMaster({
    title: "MS_CONTENT", background: { color: H.bg },
    margin: [0.5, 0.6, 0.55, 0.6],
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.95, fontSize: 30, bold: true, color: H.ink, fontFace: "Cambria", valign: "middle", align: "left", margin: 0 }, text: "" } },
      { text: { text: "MineSafe · Avishkar", options: { x: 0.6, y: 7.05, w: 4, h: 0.3, fontSize: 10, color: H.muted, fontFace: "Calibri", margin: 0 } } },
    ],
    slideNumber: { x: 12.25, y: 7.05, w: 0.5, h: 0.3, fontSize: 10, color: H.muted, fontFace: "Calibri", align: "right" },
  });

  const card = (s, x, y, w, h, fill = H.panel) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: fill }, rectRadius: 0.08 });
  const txt = (s, t, o) => s.addText(t, { isTextBox: true, fontFace: "Calibri", color: H.ink, margin: 0, valign: "top", ...o });
  const stat = (s, x, y, w, big, label, col = H.amber) => {
    txt(s, big, { x, y, w, h: 0.95, fontSize: 54, bold: true, color: col, fontFace: "Cambria" });
    txt(s, label, { x, y: y + 0.95, w, h: 0.6, fontSize: 14, color: H.muted });
  };
  const model = (s, name, x, y, w, h) => s.addImage({ path: IMG(`hardware/glb/preview/${name}.png`), x, y, w, h, objectName: `M3D_${name}`, sizing: { type: "contain", w, h }, altText: `3D model: ${name.replace(/_/g, " ")} (rotate with the mouse)` });

  // ================================================================ 1. title (Annexure 2 fields)
  {
    const s = pres.addSlide({ masterName: "MS_TITLE" });
    s.addText("MineSafe", { placeholder: "title" });
    txt(s, "Intelligent Safety Gear Compliance, Health Monitoring and Navigation System for Underground Miners",
        { x: 0.7, y: 3.0, w: 7.2, h: 1.3, fontSize: 22, color: H.ink, fontFace: "Cambria" });
    card(s, 0.7, 4.75, 7.2, 1.5, H.panel);
    txt(s, [{ text: "Slot No.:  ", options: { bold: true, color: H.amber } }, { text: "________", options: { color: H.ink } }],
        { x: 1.0, y: 4.95, w: 6.6, h: 0.45, fontSize: 20 });
    txt(s, [{ text: "Category:  ", options: { bold: true, color: H.amber } }, { text: "Engineering and Technology · UG", options: { color: H.ink } }],
        { x: 1.0, y: 5.5, w: 6.6, h: 0.45, fontSize: 18 });
    model(s, "smart_suit", 8.6, 0.35, 4.2, 6.8);
    s.addNotes("0:00–0:15. Slot number only — do not say your name or college. First-slide fields must match Annexure 2 of the MU Aavishkar rules; adjust if your coordinator gives a different format. The suit on the right is a live 3D model: click and drag to turn it.");
  }

  // ================================================================ 2. problem
  {
    const s = pres.addSlide({ masterName: "MS_CONTENT" });
    s.addText("Underground, nobody knows who is where or if they are alive", { placeholder: "title" });
    stat(s, 0.6, 1.6, 3.6, "141", "deaths in Indian coal mines, 2023–25");
    stat(s, 0.6, 3.35, 3.6, "355", "serious accidents in the same period");
    stat(s, 0.6, 5.1, 3.6, "0", "GPS or mobile signal underground", H.red);
    const inc = [["SLBC tunnel, Telangana · 2025", "8 trapped — radar needed to find them"],
                 ["Umrangso, Assam · 2025", "flooded mine, 150+ hour search"],
                 ["Kolihan, Rajasthan · 2024", "cage rope snapped, 15 trapped, 1 died"],
                 ["Ksan, Meghalaya · 2018", "15 trapped, about 80-day search"]];
    inc.forEach(([h, d], i) => {
      const y = 1.6 + i * 1.22;
      card(s, 4.7, y, 8.0, 1.04);
      txt(s, h, { x: 5.0, y: y + 0.14, w: 7.5, h: 0.4, fontSize: 18, bold: true, color: H.amber });
      txt(s, d, { x: 5.0, y: y + 0.56, w: 7.5, h: 0.4, fontSize: 15, color: H.ink });
    });
    txt(s, "Manual kit checks at the gate · no health monitoring · gas measured at a few points · evacuation by siren",
        { x: 4.7, y: 6.55, w: 8.0, h: 0.35, fontSize: 13, color: H.muted, italic: true });
    s.addNotes("0:15–0:50. Source: Ministry of Mines data (ETV Bharat, Aug 2026). Every rescue shows the same gap: no last known position, no vitals, no way to tell each worker which way to go.");
  }

  // ================================================================ 3. gap & novelty
  {
    const s = pres.addSlide({ masterName: "MS_CONTENT" });
    s.addText("No system combines kit check, vitals and GPS-free location", { placeholder: "title" });
    const Y = "✓", N = "✗", P = "~";
    const rows = [["Product", "Kit check", "Vitals", "Fall alert", "GPS-free location", "Gas", "Public price"],
      ["Teknovate MineGuard 360", N, Y, P, P, Y, N], ["MineARC GuardIAN", N, N, P, "zone", Y, N],
      ["Leantegra (UWB)", N, N, N, Y, Y, N], ["Rajant Health", "tag", Y, Y, P, P, N],
      ["EasyM2M SmartKavach", N, P, Y, N, N, N], ["36Zero + Bodytrak", P, Y, Y, N, N, N],
      ["MineSafe", Y, Y, Y, Y, Y, "₹6.9k / ₹12.8k"]];
    const cell = (v, r, c) => {
      const last = r === rows.length - 1, head = r === 0;
      let color = H.ink;
      if (!head && c > 0) color = v === Y ? H.green : v === N ? H.red : H.amber;
      if (last && c > 0) color = H.bg;
      return { text: v, options: { bold: head || last || c > 0, color: head ? H.amber : last ? H.bg : color, fill: { color: last ? H.amber : head ? H.panel2 : H.panel },
        align: c === 0 ? "left" : "center", fontSize: head ? 14 : 15, valign: "middle" } };
    };
    s.addTable(rows.map((r, ri) => r.map((v, ci) => cell(v, ri, ci))), { x: 0.6, y: 1.55, w: 12.1, colW: [3.3, 1.35, 1.25, 1.35, 2.05, 1.05, 1.75],
      rowH: 0.52, fontFace: "Calibri", border: { type: "solid", color: H.bg, pt: 2 }, margin: [0, 0.12, 0, 0.12] });
    txt(s, [{ text: "What is new:  ", options: { bold: true, color: H.amber } },
            { text: "one integrated network · location without GPS or new infrastructure · repeaters that are also exit signs · a suit that checks the kit all shift · enterprise features at small-mine prices" }],
        { x: 0.6, y: 5.95, w: 12.1, h: 0.8, fontSize: 16 });
    s.addNotes("0:50–1:20. Nine commercial products checked (July 2026). Do not claim to beat Leantegra on positioning — the point is the integration and the cost.");
  }

  // ================================================================ 4. architecture (native diagram)
  {
    const s = pres.addSlide({ masterName: "MS_CONTENT" });
    s.addText("One self-healing network from the gate to the control room", { placeholder: "title" });
    const box = (x, y, w, h, t, sub, hi) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.1, fill: { color: hi ? "3A3214" : H.panel }, line: { color: hi ? H.amber : "3A464E", width: hi ? 2 : 1 } });
      txt(s, t, { x, y: y + 0.18, w, h: 0.4, fontSize: 17, bold: true, align: "center", color: hi ? H.amber : H.ink });
      txt(s, sub, { x: x + 0.1, y: y + 0.6, w: w - 0.2, h: h - 0.7, fontSize: 12.5, align: "center", color: H.muted });
    };
    const arrow = (x1, y1, x2, y2, dash) => s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001,
      flipH: x2 < x1, line: { color: dash ? H.muted : H.amber, width: 2, dashType: dash ? "dash" : "solid", endArrowType: "triangle" } });
    box(0.6, 1.75, 2.5, 1.5, "Smart suit", "core, helmet, cuff and boot pods — vitals, fall, kit, steps", true);
    box(3.75, 1.75, 1.65, 1.5, "REP-03", "gas · air · exit sign");
    box(5.85, 1.75, 1.65, 1.5, "REP-02", "gas · air · exit sign");
    box(7.95, 1.75, 1.65, 1.5, "REP-01", "main repeater");
    box(10.25, 1.75, 2.45, 1.5, "Control-room hub", "API · AI kit check · map · evacuation planner", true);
    arrow(3.1, 2.5, 3.75, 2.5); arrow(5.4, 2.5, 5.85, 2.5); arrow(7.5, 2.5, 7.95, 2.5); arrow(9.6, 2.5, 10.25, 2.5);
    arrow(10.25, 3.55, 3.1, 3.55, true);
    txt(s, "ESP-NOW, 1 packet / s, hop by hop", { x: 3.6, y: 1.3, w: 4.5, h: 0.35, fontSize: 13, color: H.amber });
    txt(s, "Wi-Fi", { x: 9.6, y: 2.1, w: 0.7, h: 0.3, fontSize: 12, color: H.amber, align: "center" });
    txt(s, "alerts and evacuation routes ride back down the chain", { x: 3.6, y: 3.65, w: 6.4, h: 0.35, fontSize: 13, color: H.muted, align: "center" });
    box(0.6, 4.35, 2.5, 1.25, "Entry station", "RFID / ID card + AI photo check");
    box(10.25, 4.35, 2.45, 1.25, "3D control app", "browser or phone, live");
    arrow(3.1, 4.95, 10.25, 4.95, false);
    txt(s, "Wi-Fi: kit verdict and pairing", { x: 4.8, y: 4.55, w: 4, h: 0.35, fontSize: 13, color: H.amber, align: "center" });
    const pts = [["No GPS, no internet, no cabling", "radio chain forms and heals by itself"], ["Every repeater measures gas", "CH₄ top, CO / H₂S bottom, air + wet-bulb"],
                 ["One dashboard", "who is underground, where, and how they are"]];
    pts.forEach(([h, d], i) => { const x = 0.6 + i * 4.1; card(s, x, 5.85, 3.9, 0.95, H.panel2);
      txt(s, h, { x: x + 0.2, y: 5.95, w: 3.6, h: 0.35, fontSize: 15, bold: true, color: H.ink });
      txt(s, d, { x: x + 0.2, y: 6.33, w: 3.6, h: 0.4, fontSize: 12.5, color: H.muted }); });
    s.addNotes("1:20–1:50. Walk the arrows left to right, then the dashed return path.");
  }

  // ================================================================ 5. location + evacuation
  {
    const s = pres.addSlide({ masterName: "MS_CONTENT" });
    s.addText("Location without GPS, evacuation without guesswork", { placeholder: "title" });
    const steps = [["1", "Count steps", "steps × step length along the gyro heading; pressure gives the level"],
                   ["2", "Snap to the tunnel", "every position is pulled onto the nearest tunnel on the mine map"],
                   ["3", "Reset at repeaters", "strong signal (≥ −55 dBm) = next to that repeater: drift goes to zero"],
                   ["4", "Route around danger", "Dijkstra from all exits; tunnels in the hazard zone cost 1000×; each exit sign shows its arrow + distance"]];
    steps.forEach(([n, h, d], i) => {
      const y = 1.55 + i * 1.3;
      s.addShape(pres.shapes.OVAL, { x: 0.6, y: y + 0.08, w: 0.62, h: 0.62, fill: { color: H.amber }, line: { color: H.amber } });
      txt(s, n, { x: 0.6, y: y + 0.08, w: 0.62, h: 0.62, fontSize: 20, bold: true, color: H.bg, align: "center", valign: "middle" });
      txt(s, h, { x: 1.45, y, w: 4.1, h: 0.4, fontSize: 18, bold: true });
      txt(s, d, { x: 1.45, y: y + 0.42, w: 4.1, h: 0.8, fontSize: 13.5, color: H.muted });
    });
    s.addImage({ path: IMG("docs/images/control/evacuation.png"), x: 5.85, y: 1.6, w: 6.85, h: 4.28, altText: "3D control room during an evacuation" });
    txt(s, "Live 3D control room during an evacuation: routes go around the gas leak, exit signs update", { x: 5.85, y: 6.0, w: 6.85, h: 0.4, fontSize: 12, color: H.muted, italic: true });
    s.addNotes("1:50–2:20. Integrating acceleration drifts ~175 m a minute — that is why we count steps and reset at every repeater. V4 adds a foot IMU that measures each real stride.");
  }

  // ================================================================ 6. design considerations
  {
    const s = pres.addSlide({ masterName: "MS_CONTENT" });
    s.addText("Designed for dust, water, methane, heat and blasting", { placeholder: "title" });
    const items = [[fa.FaTint, "Water and dust", "IP65 gasket, drip hood, every opening faces down"],
      [fa.FaFire, "Methane rises", "CH₄ port on top under a rain chimney; H₂S / CO ports at the bottom"],
      [fa.FaShieldAlt, "Ignition risk", "sintered flame-arrestor seat at every gas port"],
      [fa.FaThermometerHalf, "Heat 30–45 °C", "air sensor in its own chamber, away from heaters"],
      [fa.FaBomb, "Blasting shock", "screw bosses, latching connectors, rubber grommets"],
      [fa.FaBolt, "Power cuts", "mine supply + battery, switch-over with no reset"],
      [fa.FaLightbulb, "Dark and smoke", "LED exit signs, reflective hi-vis tape"],
      [fa.FaHandPaper, "Thick gloves", "16–22 mm buttons, vibration and voice alerts"]];
    for (let i = 0; i < items.length; i++) {
      const [Ic, h, d] = items[i];
      const col = i % 4, row = Math.floor(i / 4), x = 0.6 + col * 3.07, y = 1.6 + row * 2.6;
      card(s, x, y, 2.87, 2.35);
      s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: y + 0.25, w: 0.72, h: 0.72, fill: { color: "3A3214" }, line: { color: H.amber, width: 1 } });
      s.addImage({ data: await icon(Ic, H.amber), x: x + 0.41, y: y + 0.41, w: 0.4, h: 0.4 });
      txt(s, h, { x: x + 0.25, y: y + 1.1, w: 2.4, h: 0.4, fontSize: 17, bold: true });
      txt(s, d, { x: x + 0.25, y: y + 1.5, w: 2.45, h: 0.8, fontSize: 13, color: H.muted });
    }
    s.addNotes("2:20–2:50. Every hardware decision starts from a mine condition. The suit is never locked — removal is detected, never prevented.");
  }

  // ================================================================ 7. repeater (3D)
  {
    const s = pres.addSlide({ masterName: "MS_CONTENT" });
    s.addText("Each repeater is a radio relay, gas station and exit sign", { placeholder: "title" });
    model(s, "repeater_case", 0.6, 1.4, 5.3, 5.5);
    txt(s, "3D model — click and drag to turn it", { x: 0.6, y: 6.6, w: 5.3, h: 0.3, fontSize: 11, color: H.muted, italic: true, align: "center" });
    const f = [["Gas", "MQ-4 CH₄ (top) · MQ-7 CO · MQ-136 H₂S (bottom), alarms to Indian limits"], ["Air", "temperature, humidity, wet-bulb heat limit 30.5 / 33.5 °C"],
               ["Exit sign", "8×32 LED matrix: arrow + distance to the safe exit"], ["Alarm", "85 dB buzzer works even if the control room is down"],
               ["Power", "9–30 V mine supply or battery, ≈ 3.7 W, ≈ 7 h backup"], ["Case", "223 × 292 × 118 mm, IP65 target, rock-bolt / chain mount"]];
    f.forEach(([h, d], i) => { const y = 1.5 + i * 0.88; card(s, 6.4, y, 6.3, 0.76);
      txt(s, h, { x: 6.6, y: y + 0.2, w: 1.35, h: 0.36, fontSize: 16, bold: true, color: H.amber });
      txt(s, d, { x: 7.95, y: y + 0.13, w: 4.6, h: 0.55, fontSize: 13.5, valign: "middle" }); });
    s.addNotes("2:50–3:30. Turn the 3D model to show the CH4 chimney on top and the downward-facing ports. Same board runs as main repeater or tunnel repeater.");
  }

  // ================================================================ 8. electrical + PCB
  {
    const s = pres.addSlide({ masterName: "MS_CONTENT" });
    s.addText("Five own PCBs: 100 % routed, 0 design-rule errors", { placeholder: "title" });
    s.addImage({ path: IMG("hardware/repeater_pcb/renders/repeater_schematic.png"), x: 0.6, y: 1.5, w: 7.6, h: 3.8, altText: "Repeater PCB schematic" });
    s.addImage({ path: IMG("hardware/repeater_pcb/renders/pcb_top.png"), x: 8.5, y: 1.5, w: 4.2, h: 3.15, altText: "Repeater PCB top render" });
    txt(s, "Repeater schematic and board (100 × 75 mm)", { x: 0.6, y: 5.35, w: 7.6, h: 0.3, fontSize: 11, color: H.muted, italic: true });
    const chips = [["2-layer, through-hole", "hand-solderable, modules on sockets"], ["Diode-OR power", "fuse + TVS + 5 V / 2 A switcher"],
                   ["Suit boards", "core 66 × 54 · cuff 46 × 42 · helmet 44 × 48 · boot 34 × 42 mm"]];
    chips.forEach(([h, d], i) => { const x = 0.6 + i * 4.1; card(s, x, 5.8, 3.9, 0.95, H.panel2);
      txt(s, h, { x: x + 0.2, y: 5.9, w: 3.6, h: 0.35, fontSize: 15, bold: true, color: H.amber });
      txt(s, d, { x: x + 0.2, y: 6.28, w: 3.6, h: 0.45, fontSize: 12.5, color: H.muted }); });
    txt(s, "KiCad 7 + Freerouting, generated by our own script: place, route, ground pour, DRC, Gerbers", { x: 8.5, y: 4.75, w: 4.2, h: 0.75, fontSize: 12, color: H.muted });
    s.addNotes("3:30–4:00. Point at the power path: mine supply and battery OR-ed by diodes, so a power cut never resets the repeater.");
  }

  // ================================================================ 9. smart suit (3D)
  {
    const s = pres.addSlide({ masterName: "MS_CONTENT" });
    s.addText("V4 smart suit: the kit checks itself all shift", { placeholder: "title" });
    model(s, "smart_suit", 0.6, 1.35, 3.6, 5.6);
    const pods = [[fa.FaMicrochip, "Core pod · chest", "ESP32-C6, 3000 mAh, motion + pressure, guarded SOS"],
                  [fa.FaHardHat, "Helmet pod", "antenna at head height, voice alerts, helmet-on switch"],
                  [fa.FaClock, "Wrist cuff", "screen, 3 glove buttons, vibration, heart rate + SpO₂"],
                  [fa.FaShoePrints, "Boot pod", "foot IMU measures each real stride, heel force sensor"],
                  [fa.FaUserShield, "Seams and zip", "conductive thread + zip switch: torn or opened = alert"]];
    for (let i = 0; i < pods.length; i++) {
      const [Ic, h, d] = pods[i], y = 1.45 + i * 1.0;
      s.addShape(pres.shapes.OVAL, { x: 4.6, y: y + 0.08, w: 0.66, h: 0.66, fill: { color: "3A3214" }, line: { color: H.amber, width: 1 } });
      s.addImage({ data: await icon(Ic, H.amber), x: 4.76, y: y + 0.24, w: 0.34, h: 0.34 });
      txt(s, h, { x: 5.5, y: y + 0.02, w: 7.2, h: 0.38, fontSize: 17, bold: true });
      txt(s, d, { x: 5.5, y: y + 0.42, w: 7.2, h: 0.4, fontSize: 13.5, color: H.muted });
    }
    card(s, 4.6, 6.45, 8.1, 0.5, "3A3214");
    txt(s, "Never locked: removal or a tear is detected and reported, never prevented", { x: 4.8, y: 6.5, w: 7.8, h: 0.4, fontSize: 14, bold: true, color: H.amber, valign: "middle" });
    s.addNotes("4:00–4:30. Turn the suit to show the helmet pod at the back and the boot pod on the right heel. Helmet and boot talk to the core over ESP-NOW; only the cuff is wired.");
  }

  // ================================================================ 10. pods (3D x4)
  {
    const s = pres.addSlide({ masterName: "MS_CONTENT" });
    s.addText("Four pods, each designed around its own board", { placeholder: "title" });
    const P = [["pod_core", "Core pod", "118 × 93 × 44 mm"], ["pod_cuff", "Wrist cuff", "88 × 75 × 27 mm"], ["pod_helmet", "Helmet pod", "75 × 66 × 31 mm"], ["pod_boot", "Boot pod", "57 × 58 × 29 mm"]];
    P.forEach(([m, h, d], i) => { const x = 0.6 + i * 3.07; card(s, x, 1.5, 2.87, 5.2);
      model(s, m, x + 0.1, 1.6, 2.67, 3.9);
      txt(s, h, { x: x + 0.2, y: 5.6, w: 2.5, h: 0.4, fontSize: 18, bold: true, align: "center" });
      txt(s, d, { x: x + 0.2, y: 6.02, w: 2.5, h: 0.35, fontSize: 13, color: H.muted, align: "center" }); });
    s.addNotes("4:30–4:50. Lids shown lifted so the board, battery and modules are visible. Every case was fit-checked in CAD against its real KiCad board.");
  }

  // ================================================================ 11. energy + components
  {
    const s = pres.addSlide({ masterName: "MS_CONTENT" });
    s.addText("Energy budget: the core pod lasts almost two shifts", { placeholder: "title" });
    s.addChart(pres.charts.BAR, [{ name: "Battery life (h)", labels: ["Repeater backup", "Core pod", "Helmet pod*", "Boot pod*"], values: [7, 21, 56, 92] }], {
      x: 0.6, y: 1.5, w: 6.4, h: 4.6, barDir: "bar", chartColors: [H.amber], showValue: true, dataLabelPosition: "outEnd", dataLabelColor: H.ink, dataLabelFontSize: 14,
      dataLabelFontFace: "+mn-lt", catAxisLabelColor: H.ink, catAxisLabelFontSize: 14, catAxisLabelFontFace: "+mn-lt", valAxisLabelColor: H.muted, valAxisLabelFontFace: "+mn-lt",
      valAxisLabelFontSize: 11, valGridLine: { color: "2E3A42", size: 0.75 }, catGridLine: { style: "none" }, showLegend: false, showTitle: true, title: "Hours on one charge (shift = 12 h)",
      titleColor: H.ink, titleFontSize: 15, titleFontFace: "+mn-lt", catAxisOrientation: "maxMin" });
    txt(s, "* with the radio duty-cycled (V4 firmware). Datasheet estimates, to be confirmed by measurement.", { x: 0.6, y: 6.15, w: 6.4, h: 0.5, fontSize: 11, color: H.muted, italic: true });
    const comp = [["ESP32-C6 (XIAO)", "Wi-Fi, BLE, Zigbee + ESP-NOW on one 21 mm board"], ["ESP-NOW, not Zigbee", "no re-joining for a moving worker; LoRa later for long tunnels"],
                  ["Step counting, not UWB", "UWB ≈ ₹2,000 per tag and anchor; steps cost nothing"], ["Switching regulators", "a linear 7805 would waste ≈ 11 W at 24 V"],
                  ["Gas on repeaters only", "MQ heaters use 150 mA — wrong for a battery wearable"]];
    comp.forEach(([h, d], i) => { const y = 1.5 + i * 1.0; card(s, 7.4, y, 5.3, 0.86);
      txt(s, h, { x: 7.6, y: y + 0.1, w: 5.0, h: 0.35, fontSize: 15, bold: true, color: H.amber });
      txt(s, d, { x: 7.6, y: y + 0.45, w: 5.0, h: 0.35, fontSize: 12.5, color: H.ink }); });
    s.addNotes("4:50–5:15. Repeater: ≈ 3.7 W, mostly the three gas-sensor heaters. Core pod: ≈ 112 mA at 3.3 V → ≈ 21 h from 3000 mAh.");
  }

  // ================================================================ 12. validation
  {
    const s = pres.addSlide({ masterName: "MS_CONTENT" });
    s.addText("Validated in steps: design and bench done, field tests next", { placeholder: "title" });
    const cols = [["Design checks", "4 / 4 passed", H.green, ["PCB DRC: 0 unconnected pads (5 boards)", "CAD fit check: no collisions (5 cases)", "Power budget: core pod 21 h ≥ 12 h", "Signal levels: ADC and 5 V logic in range"]],
                  ["Bench tests", "5 / 6 passed", H.green, ["Repeater chain forms by itself (3/3)", "Air sensing logged (31.3 °C, 62 % RH)", "Gas alarm + local buzzer", "Hub logic + robustness with simulator", "Body sensors: wiring being fixed"]],
                  ["Field tests (pass criteria)", "in progress", H.amber, ["Alert to deepest worker ≤ 3 s (95 %)", "Distance error ≤ 5 % over 100 m", "Falls detected ≥ 90 %, ≤ 1 false / h", "HR ± 5 bpm, SpO₂ ± 3 % vs oximeter", "Hose test 30 min, 1 m drop, 24 h at 45\u00a0°C"]]];
    cols.forEach(([h, st, col, items], i) => { const x = 0.6 + i * 4.1; card(s, x, 1.5, 3.9, 5.3);
      txt(s, h, { x: x + 0.25, y: 1.7, w: 3.4, h: 0.4, fontSize: 19, bold: true });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.25, y: 2.2, w: 1.8, h: 0.4, rectRadius: 0.2, fill: { color: col }, line: { color: col } });
      txt(s, st, { x: x + 0.25, y: 2.2, w: 1.8, h: 0.4, fontSize: 13, bold: true, color: H.bg, align: "center", valign: "middle" });
      txt(s, items.map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < items.length - 1 } })), { x: x + 0.25, y: 2.85, w: 3.45, h: 3.8, fontSize: 14, paraSpaceAfter: 8, color: H.ink }); });
    s.addNotes("5:15–5:50. Be honest: V3 is in field calibration. Each field test has a numeric pass criterion; results are logged with screenshots and video.");
  }

  // ================================================================ 13. cost, impact, conclusion
  {
    const s = pres.addSlide({ masterName: "MS_CONTENT" });
    s.addText("Affordable for small mines: checked, located, reachable", { placeholder: "title" });
    stat(s, 0.6, 1.5, 3.0, "₹6,860", "per repeater (PCB + mine case)");
    stat(s, 3.75, 1.5, 3.0, "₹12,800", "per smart suit");
    stat(s, 6.9, 1.5, 3.0, "₹3.3 L", "site: 10 repeaters + 20 suits");
    txt(s, "Every commercial system: enterprise quote only", { x: 10.0, y: 1.6, w: 2.7, h: 1.4, fontSize: 16, color: H.muted, italic: true });
    const imp = [["Social", "faster rescue with a last known position; falls, gas and heat caught as they happen"], ["SDGs", "3 Good health · 8 Decent work · 9 Industry and innovation"],
                 ["Next", "LoRa backbone · certified NDIR / electrochemical gas sensors · intrinsic-safety design · field trial with a mine"]];
    imp.forEach(([h, d], i) => { const y = 3.4 + i * 0.95; card(s, 0.6, y, 12.1, 0.8);
      txt(s, h, { x: 0.85, y: y + 0.2, w: 1.4, h: 0.4, fontSize: 17, bold: true, color: H.amber });
      txt(s, d, { x: 2.3, y: y + 0.2, w: 10.2, h: 0.45, fontSize: 15 }); });
    txt(s, "Thank you", { x: 0.6, y: 6.35, w: 6, h: 0.55, fontSize: 26, bold: true, color: H.amber, fontFace: "Cambria" });
    s.addNotes("5:50–6:30. End on cost and impact (20 of 100 marks are economic efficiency and social relevance). Stop by 6:45 — over 7:15 disqualifies.");
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
