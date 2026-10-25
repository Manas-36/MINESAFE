// MineSafe technical document -> professional Word file (Times New Roman), built from the Docs export (source.md).
// Cover page, table of contents, numbered sections, figures with captions, equations, styled tables,
// running header and "Page X of Y" footer. A4, 1-inch margins.
const fs = require("fs");
const path = require("path");
const { marked } = require("marked");
const sizeOf = (p) => { const b = fs.readFileSync(p); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; };   // PNG header
const D = require("docx");
const {
  Document, Packer, Paragraph, TextRun, ExternalHyperlink, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  HeadingLevel, BorderStyle, ShadingType, PageBreak, Header, Footer, PageNumber, TableOfContents, LevelFormat, VerticalAlign,
  TabStopType, TableLayoutType, LineRuleType,
} = D;

const R = path.resolve(__dirname, "..", "..", "..");
const FONT = "Times New Roman";
const TEXT_W = 9026;                         // A4 width 11906 - 2 x 1440
const MAX_IMG_PX = 576;                      // 6.0 in at 96 dpi

const FIG = {
  "5.1": "presentation/avishkar/report/img/fig_5.1.jpg", "7.1": "presentation/avishkar/report/img/fig_7.1.jpg", "7.2": "presentation/avishkar/report/img/fig_7.2.jpg",
  "7.3": "presentation/avishkar/report/img/fig_7.3.jpg", "7.4": "presentation/avishkar/report/img/fig_7.4.jpg", "7.5": "presentation/avishkar/report/img/fig_7.5.jpg",
  "7.6": "presentation/avishkar/report/img/fig_7.6.jpg", "7.7": "presentation/avishkar/report/img/fig_7.7.jpg", "7.8": "presentation/avishkar/report/img/fig_7.8.jpg",
  "7.9": "presentation/avishkar/report/img/fig_7.9.jpg", "7.10": "presentation/avishkar/report/img/fig_7.10.jpg", "8.1": "presentation/avishkar/report/img/fig_8.1.jpg",
  "8.2": "presentation/avishkar/report/img/fig_8.2.jpg", "8.3": "presentation/avishkar/report/img/fig_8.3.jpg", "8.4": "presentation/avishkar/report/img/fig_8.4.jpg",
  "8.5": "presentation/avishkar/report/img/fig_8.5.jpg", "8.6": "presentation/avishkar/report/img/fig_8.6.jpg", "8.7": "presentation/avishkar/report/img/fig_8.7.jpg",
  "9.1": "presentation/avishkar/report/img/fig_9.1.jpg", "9.2": "presentation/avishkar/report/img/fig_9.2.jpg", "9.3": "presentation/avishkar/report/img/fig_9.3.jpg",
  "9.4": "presentation/avishkar/report/img/fig_9.4.jpg", "9.5": "presentation/avishkar/report/img/fig_9.5.jpg", "12.1": "presentation/avishkar/report/img/fig_12.1.jpg",
  "12.2": "presentation/avishkar/report/img/fig_12.2.jpg", "12.3": "presentation/avishkar/report/img/fig_12.3.jpg", "12.4": "presentation/avishkar/report/img/fig_12.4.jpg",
  "12.5": "presentation/avishkar/report/img/fig_12.5.jpg",
};

const decode = (s) => s.replace(/&#91;/g, "[").replace(/&#93;/g, "]").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
  .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/\\\]/g, "]").replace(/\\\[/g, "[").replace(/\\([*_#|`~])/g, "$1");

// ------------------------------------------------------------------ inline tokens -> runs
function runs(tokens, st = {}) {
  const out = [];
  for (const t of tokens || []) {
    if (t.type === "strong") out.push(...runs(t.tokens, { ...st, bold: true }));
    else if (t.type === "em") out.push(...runs(t.tokens, { ...st, italics: true }));
    else if (t.type === "codespan") out.push(new TextRun({ text: decode(t.text), font: "Courier New", size: st.size ? st.size - 2 : 21, ...st, bold: st.bold }));
    else if (t.type === "link") out.push(new ExternalHyperlink({ link: t.href, children: runs(t.tokens, { ...st, color: "1F4E79", underline: {} }) }));
    else if (t.type === "br") out.push(new TextRun({ break: 1 }));
    else if (t.tokens) out.push(...runs(t.tokens, st));
    else out.push(new TextRun({ text: decode(t.text ?? t.raw ?? ""), ...st }));
  }
  return out;
}

const body = (children, o = {}) => new Paragraph({ children, alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, line: 276, lineRule: LineRuleType.AUTO }, ...o });

const SIZES = JSON.parse(fs.readFileSync(path.join(__dirname, "img", "sizes.json"), "utf8"));
function image(file, maxW = MAX_IMG_PX, maxH = 620) {
  const p = path.join(R, file);
  const { w, h } = SIZES[file] ? { w: SIZES[file][0], h: SIZES[file][1] } : sizeOf(p);
  let s = Math.min(maxW / w, maxH / h);
  return new ImageRun({ type: file.endsWith(".jpg") ? "jpg" : "png", data: fs.readFileSync(p), transformation: { width: Math.round(w * s), height: Math.round(h * s) },
    altText: { title: path.basename(file), description: path.basename(file), name: path.basename(file) } });
}

// ------------------------------------------------------------------ tables
const thin = { style: BorderStyle.SINGLE, size: 4, color: "8C8C8C" };
function table(t) {
  const n = t.header.length;
  const len = (c) => decode(c.text).length;
  const weights = t.header.map((h, i) => Math.max(6, Math.min(60, Math.max(len(h), ...t.rows.map((r) => len(r[i] || { text: "" }))))));
  const sum = weights.reduce((a, b) => a + b, 0);
  let widths = weights.map((w) => Math.round((w / sum) * TEXT_W));
  const MIN = 900;                                   // no column narrower than ~0.63 in (avoids one-letter wrapping)
  for (let k = 0; k < n; k++) if (widths[k] < MIN) {
    const need = MIN - widths[k]; widths[k] = MIN;
    const big = widths.indexOf(Math.max(...widths)); widths[big] -= need;
  }
  widths[n - 1] += TEXT_W - widths.reduce((a, b) => a + b, 0);
  const cell = (c, i, head) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    shading: head ? { type: ShadingType.CLEAR, color: "auto", fill: "D9E2EA" } : undefined,
    margins: { top: 60, bottom: 60, left: 90, right: 90 },
    borders: { top: thin, bottom: thin, left: thin, right: thin },
    children: [new Paragraph({ children: runs(c.tokens, { size: 20, bold: head || undefined }), spacing: { after: 0, line: 252, lineRule: LineRuleType.AUTO } })],
  });
  return new Table({
    width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED,
    rows: [new TableRow({ tableHeader: true, children: t.header.map((c, i) => cell(c, i, true)) }),
           ...t.rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false)) }))],
  });
}

// ------------------------------------------------------------------ lists
let listInstance = 0;
function list(t, level = 0, out = []) {
  const inst = ++listInstance;
  t.items.forEach((it, k) => {
    const inline = [], nested = [];
    for (const tok of it.tokens) (tok.type === "list" ? nested : inline).push(tok);
    const children = runs(inline.flatMap((x) => (x.type === "text" || x.type === "paragraph") ? (x.tokens || [x]) : [x]));
    if (t.ordered && t.start && t.start !== 1 && level === 0) {
      out.push(new Paragraph({ children: [new TextRun({ text: `[${t.start + k}]\t` }), ...children], alignment: AlignmentType.LEFT,
        tabStops: [{ type: TabStopType.LEFT, position: 567 }], indent: { left: 567, hanging: 567 }, spacing: { after: 80, line: 264, lineRule: LineRuleType.AUTO } }));
    } else {
      out.push(new Paragraph({ children, alignment: AlignmentType.JUSTIFIED, spacing: { after: 80, line: 264, lineRule: LineRuleType.AUTO },
        numbering: { reference: t.ordered ? "num" : "bul", level, instance: t.ordered ? inst : 0 } }));
    }
    nested.forEach((nl) => list(nl, level + 1, out));
  });
  return out;
}

// ------------------------------------------------------------------ document body
const md = fs.readFileSync(path.join(__dirname, "source.md"), "utf8");
const toks = marked.lexer(md);
const content = [];
let eqn = 0, inRefs = false, figTableCount = 0;
for (let i = 0; i < toks.length; i++) {
  const t = toks[i];
  if (t.type === "space" || t.type === "hr") continue;
  if (t.type === "heading") {
    if (t.depth === 1) continue;                                   // title goes on the cover
    const txt = decode(t.text);
    inRefs = /^18\. References/.test(txt);
    content.push(new Paragraph({ heading: t.depth === 2 ? HeadingLevel.HEADING_1 : HeadingLevel.HEADING_2, children: [new TextRun(txt)],
      pageBreakBefore: t.depth === 2 && /^(5|7|8|9|10|12|15|18)\./.test(txt) }));
    continue;
  }
  if (t.type === "paragraph") {
    const raw = decode(t.raw.trim());
    if (/^[A-Z][a-z]{2} \d+, \d{4} · @/.test(raw)) continue;      // byline (date · author) -> cover page
    let m = raw.match(/^\[image: Figure ([\d.]+)/);
    if (m && FIG[m[1]]) { content.push(new Paragraph({ children: [image(FIG[m[1]], MAX_IMG_PX, /^8\.[4-7]$/.test(m[1]) ? 700 : 400)], alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 } })); continue; }
    if (/^\[embedded content: MineSafe system architecture/.test(raw)) {
      content.push(new Paragraph({ children: [image("presentation/avishkar/report/architecture.png", MAX_IMG_PX, 400)], alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 } }));
      content.push(new Paragraph({ children: [new TextRun({ text: "Figure 5.0 – MineSafe system architecture (V4): data rises hop by hop to the hub; alerts and routes return down the chain.", italics: true, size: 20 })], alignment: AlignmentType.CENTER, spacing: { after: 200 } }));
      continue;
    }
    if (/^\*Figure [\d.]+/.test(t.raw.trim())) {
      content.push(new Paragraph({ children: runs(t.tokens, { size: 20 }), alignment: AlignmentType.CENTER, spacing: { after: 200 } }));
      continue;
    }
    content.push(body(runs(t.tokens), inRefs ? { alignment: AlignmentType.LEFT } : {}));
    continue;
  }
  if (t.type === "code" && t.lang === "latex") {
    eqn++;
    const f = `presentation/avishkar/report/eq/eq${eqn}.png`;
    const { w, h } = sizeOf(path.join(R, f));
    const s = Math.min(520 / w, 0.28);
    content.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 160 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(path.join(R, f)), transformation: { width: Math.round(w * s), height: Math.round(h * s) },
        altText: { title: `Equation ${eqn}`, description: t.text, name: `eq${eqn}` } })] }));
    continue;
  }
  if (t.type === "table") { content.push(table(t)); content.push(new Paragraph({ children: [], spacing: { after: 120 } })); figTableCount++; continue; }
  if (t.type === "list") { content.push(...list(t)); continue; }
  if (t.type === "code") { content.push(new Paragraph({ children: [new TextRun({ text: t.text, font: "Courier New", size: 20 })] })); continue; }
  console.warn("unhandled", t.type);
}

// ------------------------------------------------------------------ cover page
const title = decode(toks.find((t) => t.type === "heading" && t.depth === 1).text);
const [main, sub] = title.split(" — ");
const rule = new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: "1F2933", space: 1 } }, spacing: { after: 240 } });
const kv = [["Category", "Engineering and Technology (UG)"], ["Team", "Manas Pednekar (Roll 36) · Amey Satale (Roll 46) · Aaryaa Kanojia (Roll 18)"],
  ["Guide", "Mr Dipesh Tare"], ["Department", "Mechanical and Mechatronics Engineering (Additive Manufacturing)"],
  ["Institute", "Thakur College of Engineering and Technology (TCET), Mumbai"], ["Academic year", "2026–27"], ["Date", "25 October 2026"]];
const kvTable = new Table({
  width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: [2400, TEXT_W - 2400], layout: TableLayoutType.FIXED,
  rows: kv.map(([k, v]) => new TableRow({ children: [
    new TableCell({ width: { size: 2400, type: WidthType.DXA }, borders: { top: thin, bottom: thin, left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" } },
      margins: { top: 80, bottom: 80, left: 0, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: k, bold: true, size: 22 })] })] }),
    new TableCell({ width: { size: TEXT_W - 2400, type: WidthType.DXA }, borders: { top: thin, bottom: thin, left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" } },
      margins: { top: 80, bottom: 80, left: 120, right: 0 }, children: [new Paragraph({ children: [new TextRun({ text: v, size: 22 })] })] }),
  ] })),
});
const cover = [
  new Paragraph({ children: [new TextRun({ text: "TECHNICAL DOCUMENT · AVISHKAR 2026–27", size: 22, bold: true, characterSpacing: 40, color: "595959" })], spacing: { before: 600, after: 240 } }),
  new Paragraph({ children: [new TextRun({ text: main, size: 72, bold: true })], spacing: { after: 160 } }),
  new Paragraph({ children: [new TextRun({ text: sub, size: 32 })], spacing: { after: 240 } }),
  rule,
  new Paragraph({ alignment: AlignmentType.CENTER, children: [image("hardware/glb/preview/smart_suit.png", 300, 380), new TextRun("   "), image("hardware/glb/preview/repeater_case.png", 300, 380)], spacing: { after: 360 } }),
  kvTable,
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ children: [new TextRun({ text: "Contents", bold: true, size: 32 })], spacing: { after: 240 } }),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ children: [new PageBreak()] }),
];

const doc = new Document({
  creator: "MineSafe team", title: "MineSafe — Technical Document", description: "Avishkar 2026–27 technical document",
  features: { updateFields: true },
  styles: {
    default: { document: { run: { font: FONT, size: 24 }, paragraph: { spacing: { line: 276, lineRule: LineRuleType.AUTO } } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 32, bold: true, color: "1F2933" }, paragraph: { spacing: { before: 360, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 26, bold: true, color: "1F2933" }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 1 } },
    ],
    characterStyles: [{ id: "Hyperlink", name: "Hyperlink", run: { color: "1F4E79", underline: {} } }],
  },
  numbering: { config: [
    { reference: "bul", levels: [0, 1, 2].map((l) => ({ level: l, format: LevelFormat.BULLET, text: l === 1 ? "–" : "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 567 * (l + 1), hanging: 284 } }, run: { font: FONT } } })) },
    { reference: "num", levels: [0, 1, 2].map((l) => ({ level: l, format: l === 1 ? LevelFormat.LOWER_LETTER : LevelFormat.DECIMAL, text: l === 1 ? "%2)" : `%${l + 1}.`,
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 567 * (l + 1), hanging: 340 } }, run: { font: FONT } } })) },
  ] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440, header: 708, footer: 708 } }, titlePage: true },
    headers: {
      first: new Header({ children: [new Paragraph({ children: [] })] }),
      default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "8C8C8C", space: 4 } },
        children: [new TextRun({ text: "MineSafe — Technical Document", italics: true, size: 18, color: "595959" })] })] }),
    },
    footers: {
      first: new Footer({ children: [new Paragraph({ children: [] })] }),
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
        new TextRun({ children: ["Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], size: 18, color: "595959" })] })] }),
    },
    children: [...cover, ...content],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(__dirname, "MineSafe_Technical_Document.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, (buf.length / 1e6).toFixed(1), "MB; equations", eqn, "tables", figTableCount);
});
