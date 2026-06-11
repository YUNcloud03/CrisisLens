// CrisisLens v2.0 — Final Report Presentation Generator
// Run: NODE_PATH=$(npm root -g) node gen_pptx.js

const pptxgen = require("pptxgenjs");

const OUT = "C:\\Users\\LIYUN\\Desktop\\DisasterAid AI\\crisislens\\docs\\CrisisLens_v2_Final_Report.pptx";

// ── Palette (NO # prefix) ────────────────────────────────────
const C = {
  bg:      "0F172A",
  card:    "1E293B",
  card2:   "263044",
  border:  "334155",
  text:    "E2E8F0",
  muted:   "94A3B8",
  dim:     "475569",
  blue:    "38BDF8",
  green:   "4ADE80",
  amber:   "FBBF24",
  coral:   "F87171",
  purple:  "C084FC",
  teal:    "2DD4BF",
  white:   "FFFFFF",
};

const FONT = "Arial";

// ── Helpers ──────────────────────────────────────────────────
const mkShadow = () => ({ type: "outer", blur: 8, offset: 2, angle: 135, color: "000000", opacity: 0.30 });

function addFooter(slide) {
  slide.addText("CrisisLens v2.0  |  SDG + NN Final Project  |  June 2026", {
    x: 0, y: 5.38, w: 10, h: 0.245,
    fontSize: 8, fontFace: FONT, color: C.dim,
    align: "center", valign: "middle", margin: 0,
  });
}

function addTitle(slide, text, accent) {
  slide.addText(text, {
    x: 0.4, y: 0.18, w: 9.2, h: 0.55,
    fontSize: 26, fontFace: FONT, bold: true,
    color: accent || C.blue, align: "left", valign: "middle", margin: 0,
  });
}

function card(slide, x, y, w, h, color, opts = {}) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill: { color: opts.fill || C.card },
    line: { color: color, width: opts.borderW || 1.5 },
    shadow: mkShadow(),
    rectRadius: 0,
  });
}

function tag(slide, x, y, text, color, w) {
  const tw = w || (text.length * 0.085 + 0.3);
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w: tw, h: 0.28,
    fill: { color: color, transparency: 80 },
    line: { color: color, width: 1 },
  });
  slide.addText(text, {
    x, y, w: tw, h: 0.28,
    fontSize: 9, fontFace: FONT, bold: true, color: color,
    align: "center", valign: "middle", margin: 0,
  });
  return tw;
}

function infoBox(slide, x, y, w, h, label, labelColor, body, opts = {}) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill: { color: opts.bgColor || C.card },
    line: { color: labelColor, width: opts.bw || 1.5 },
    shadow: mkShadow(),
  });
  if (label) {
    slide.addText(label, {
      x: x + 0.12, y: y + 0.08, w: w - 0.24, h: 0.28,
      fontSize: opts.labelSize || 11, fontFace: FONT, bold: true,
      color: labelColor, margin: 0,
    });
  }
  if (body) {
    slide.addText(body, {
      x: x + 0.12, y: y + (label ? 0.36 : 0.1), w: w - 0.24, h: h - (label ? 0.46 : 0.2),
      fontSize: opts.bodySize || 10, fontFace: FONT, color: opts.bodyColor || C.text,
      valign: "top", margin: 0, ...(opts.textOpts || {}),
    });
  }
}

// ══════════════════════════════════════════════════════════════
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title  = "CrisisLens v2.0 — Final Report";
pres.author = "CrisisLens Team";

// ═══════════════════════════════════════════════════════════
// SLIDE 1 — Title
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  // Large logo-style title
  s.addText("CrisisLens", {
    x: 0.6, y: 0.7, w: 8.8, h: 1.1,
    fontSize: 64, fontFace: FONT, bold: true, color: C.blue,
    align: "left", valign: "middle", margin: 0,
  });
  s.addText("v2.0", {
    x: 5.5, y: 0.82, w: 2, h: 0.75,
    fontSize: 32, fontFace: FONT, bold: false, color: C.muted,
    align: "left", valign: "middle", margin: 0,
  });

  s.addText("災情分類與應變建議系統", {
    x: 0.6, y: 1.72, w: 8.8, h: 0.5,
    fontSize: 22, fontFace: FONT, bold: false, color: C.text,
    align: "left", margin: 0,
  });
  s.addText("Disaster Classification & Response Advisory System", {
    x: 0.6, y: 2.15, w: 8.8, h: 0.4,
    fontSize: 14, fontFace: FONT, color: C.muted, align: "left", margin: 0,
  });

  // Tag chips
  let tx = 0.6;
  const chips = [
    { t: "SDG 11 | Sustainable Cities", c: C.blue },
    { t: "SDG 13 | Climate Action",     c: C.green },
    { t: "Neural Network + MLOps",       c: C.amber },
  ];
  chips.forEach(ch => {
    const tw = ch.t.length * 0.08 + 0.35;
    s.addShape(pres.shapes.RECTANGLE, { x: tx, y: 2.75, w: tw, h: 0.32, fill: { color: ch.c, transparency: 78 }, line: { color: ch.c, width: 1.2 } });
    s.addText(ch.t, { x: tx, y: 2.75, w: tw, h: 0.32, fontSize: 9.5, fontFace: FONT, bold: true, color: ch.c, align: "center", valign: "middle", margin: 0 });
    tx += tw + 0.18;
  });

  s.addShape(pres.shapes.LINE, { x: 0.6, y: 3.28, w: 8.8, h: 0, line: { color: C.border, width: 0.8 } });

  s.addText("Group Final Report  |  June 2026", {
    x: 0.6, y: 3.45, w: 8.8, h: 0.35,
    fontSize: 12, fontFace: FONT, color: C.muted, align: "left", margin: 0,
  });

  // Key stats row
  const stats = [
    { n: "3",    label: "Neural Network\nModels" },
    { n: "6",    label: "Disaster\nClasses" },
    { n: "H3",   label: "Hexagonal GIS\nHeatmap" },
    { n: "RAG",  label: "FAISS + Gemini\nAdvisory" },
    { n: "MLOps",label: "Version\nTracking" },
  ];
  const sstat = 0.6, statW = 1.72, statH = 0.85, statY = 3.9, statGap = 0.12;
  stats.forEach((st, i) => {
    const sx = sstat + i * (statW + statGap);
    s.addShape(pres.shapes.RECTANGLE, { x: sx, y: statY, w: statW, h: statH, fill: { color: C.card2 }, line: { color: C.border, width: 0.8 } });
    s.addText(st.n, { x: sx, y: statY + 0.04, w: statW, h: 0.44, fontSize: 22, fontFace: FONT, bold: true, color: C.blue, align: "center", margin: 0 });
    s.addText(st.label, { x: sx, y: statY + 0.46, w: statW, h: 0.36, fontSize: 8.5, fontFace: FONT, color: C.muted, align: "center", valign: "top", margin: 0 });
  });

  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 2 — Problem & SDG
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Problem Statement & SDG Alignment");

  // Left — problem bullets
  s.addText("The Challenge", { x: 0.4, y: 0.88, w: 5.2, h: 0.32, fontSize: 13, fontFace: FONT, bold: true, color: C.amber, margin: 0 });

  const probs = [
    "Taiwan faces ~4 typhoons, multiple earthquakes, and flooding events every year",
    "Citizens lack a fast, AI-powered tool to classify disasters and receive immediate guidance",
    "Emergency managers cannot aggregate scattered citizen reports into a spatial picture in real-time",
    "Delayed triage increases harm — the first 30 minutes of disaster response are critical",
  ];
  s.addText(probs.map((t, i) => ([
    { text: `${i+1}.  `, options: { bold: true, color: C.amber } },
    { text: t + (i < probs.length - 1 ? "\n" : ""), options: { color: C.text } },
  ])).flat(), {
    x: 0.4, y: 1.22, w: 5.0, h: 2.9,
    fontSize: 11.5, fontFace: FONT, valign: "top", margin: 0,
    paraSpaceAfter: 8,
  });

  // Right — SDG boxes
  // SDG 11
  s.addShape(pres.shapes.RECTANGLE, { x: 5.7, y: 0.9, w: 3.9, h: 1.7, fill: { color: "0C2340" }, line: { color: C.blue, width: 1.5 }, shadow: mkShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 5.7, y: 0.9, w: 3.9, h: 0.38, fill: { color: C.blue, transparency: 55 }, line: { width: 0 } });
  s.addText("SDG 11 — Sustainable Cities", { x: 5.82, y: 0.92, w: 3.66, h: 0.34, fontSize: 10.5, fontFace: FONT, bold: true, color: C.white, margin: 0 });
  s.addText("Enable rapid urban disaster reporting and response coordination, reducing harm in dense communities through AI-powered triage and spatial event aggregation.", {
    x: 5.82, y: 1.35, w: 3.66, h: 1.15, fontSize: 10, fontFace: FONT, color: C.text, valign: "top", margin: 0,
  });

  // SDG 13
  s.addShape(pres.shapes.RECTANGLE, { x: 5.7, y: 2.75, w: 3.9, h: 1.7, fill: { color: "0C2312" }, line: { color: C.green, width: 1.5 }, shadow: mkShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x: 5.7, y: 2.75, w: 3.9, h: 0.38, fill: { color: C.green, transparency: 60 }, line: { width: 0 } });
  s.addText("SDG 13 — Climate Action", { x: 5.82, y: 2.77, w: 3.66, h: 0.34, fontSize: 10.5, fontFace: FONT, bold: true, color: C.white, margin: 0 });
  s.addText("Address the growing frequency of climate-driven disasters — typhoons, floods, and landslides — through AI-assisted classification and data-driven response guidance.", {
    x: 5.82, y: 3.2, w: 3.66, h: 1.15, fontSize: 10, fontFace: FONT, color: C.text, valign: "top", margin: 0,
  });

  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 3 — System Architecture
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "System Architecture Overview");

  // Flow row 1: Upload → EXIF → Safety → AI → RAG
  const flow1 = [
    { label: "Citizen\nUpload",   color: C.muted },
    { label: "EXIF\nStrip",       color: C.green },
    { label: "Safety\nGuard",     color: C.amber },
    { label: "AI\nClassification",color: C.blue  },
    { label: "RAG\nAdvisory",     color: C.purple},
  ];
  const bw = 1.45, bh = 0.72, by = 0.88, gap = 0.22;
  const totalW = flow1.length * bw + (flow1.length - 1) * gap;
  let fx = (10 - totalW) / 2;

  flow1.forEach((item, i) => {
    s.addShape(pres.shapes.RECTANGLE, { x: fx, y: by, w: bw, h: bh, fill: { color: item.color, transparency: 78 }, line: { color: item.color, width: 1.5 } });
    s.addText(item.label, { x: fx, y: by, w: bw, h: bh, fontSize: 10, fontFace: FONT, bold: true, color: item.color, align: "center", valign: "middle", margin: 0 });
    if (i < flow1.length - 1) {
      s.addText("→", { x: fx + bw, y: by + 0.2, w: gap, h: 0.32, fontSize: 14, color: C.dim, align: "center", margin: 0 });
    }
    fx += bw + gap;
  });

  // Down arrow from AI Classification
  const aiX = (10 - totalW) / 2 + 3 * (bw + gap) + bw / 2 - 0.12;
  s.addText("↓", { x: aiX, y: by + bh + 0.02, w: 0.3, h: 0.3, fontSize: 16, color: C.dim, align: "center", margin: 0 });

  // Row 2: Event Aggregation
  const ea = { x: aiX - 0.55, y: by + bh + 0.3, w: 1.5, h: 0.55 };
  s.addShape(pres.shapes.RECTANGLE, { x: ea.x, y: ea.y, w: ea.w, h: ea.h, fill: { color: C.blue, transparency: 80 }, line: { color: C.blue, width: 1.5 } });
  s.addText("Event\nAggregation", { x: ea.x, y: ea.y, w: ea.w, h: ea.h, fontSize: 9.5, fontFace: FONT, bold: true, color: C.blue, align: "center", valign: "middle", margin: 0 });

  // Down arrow
  s.addText("↓", { x: aiX, y: ea.y + ea.h + 0.01, w: 0.3, h: 0.28, fontSize: 16, color: C.dim, align: "center", margin: 0 });

  // Row 3: H3 ← Admin → MLOps
  const row3y = ea.y + ea.h + 0.28;
  const row3Items = [
    { label: "H3\nHeatmap", color: C.teal, left: true },
    { label: "Admin\nDashboard", color: C.green },
    { label: "MLOps\nMonitor", color: C.purple, right: true },
  ];
  const rw = 1.5, rh = 0.55, rStart = aiX - 0.75 - rw - 0.25;
  row3Items.forEach((item, i) => {
    const rx = rStart + i * (rw + 0.25);
    s.addShape(pres.shapes.RECTANGLE, { x: rx, y: row3y, w: rw, h: rh, fill: { color: item.color, transparency: 80 }, line: { color: item.color, width: 1.5 } });
    s.addText(item.label, { x: rx, y: row3y, w: rw, h: rh, fontSize: 9.5, fontFace: FONT, bold: true, color: item.color, align: "center", valign: "middle", margin: 0 });
    if (i < 2) {
      const arrowLabel = i === 0 ? "←" : "→";
      s.addText(arrowLabel, { x: rx + rw, y: row3y + 0.1, w: 0.25, h: 0.35, fontSize: 14, color: C.dim, align: "center", margin: 0 });
    }
  });

  // 4 model pillars at bottom
  const pillars = [
    { t: "CLIP ViT-L/14",   sub: "Zero-shot primary",    c: C.blue  },
    { t: "ResNet50 LP",      sub: "MEDIC fine-tuned",     c: C.green },
    { t: "DisasterCNN_v1",  sub: "Custom trained",        c: C.amber },
    { t: "RAG + Gemini",    sub: "Response advisor",      c: C.coral },
  ];
  const pw = 2.2, ph = 0.62, py = 4.65, pgap = 0.12;
  const pstart = (10 - (4 * pw + 3 * pgap)) / 2;
  pillars.forEach((p, i) => {
    const px = pstart + i * (pw + pgap);
    s.addShape(pres.shapes.RECTANGLE, { x: px, y: py, w: pw, h: ph, fill: { color: p.c, transparency: 82 }, line: { color: p.c, width: 1.5 } });
    s.addText([
      { text: p.t + "\n", options: { bold: true, color: p.c } },
      { text: p.sub, options: { color: C.muted } },
    ], { x: px, y: py, w: pw, h: ph, fontSize: 9.5, fontFace: FONT, align: "center", valign: "middle", margin: 0 });
  });

  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 4 — CLIP ViT-L/14
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Model 1: CLIP ViT-L/14  (Primary Classifier — A2)");

  // Left column
  const leftItems = [
    { label: "Architecture", value: "ViT-L/14  ·  431M parameters  ·  Zero-shot" },
    { label: "Method", value: "Multi-prompt averaging: 6 classes × 4–7 prompts → cosine similarity mean → ×100 temperature scaling → softmax" },
    { label: "Output", value: "Top-3 class probabilities + confidence score (0–1)" },
    { label: "Prompt sets", value: "28 total prompts across 6 classes (7 earthquake, 4 flood, 4 fire, 4 typhoon, 5 landslide, 4 other)" },
  ];
  leftItems.forEach((item, i) => {
    const ly = 0.98 + i * 0.88;
    s.addText(item.label, { x: 0.4, y: ly, w: 4.7, h: 0.28, fontSize: 10, fontFace: FONT, bold: true, color: C.blue, margin: 0 });
    s.addText(item.value, { x: 0.4, y: ly + 0.26, w: 4.7, h: 0.55, fontSize: 9.5, fontFace: FONT, color: C.text, valign: "top", margin: 0 });
  });

  // Right — class table
  s.addText("6 Disaster Classes", { x: 5.35, y: 0.9, w: 4.2, h: 0.32, fontSize: 11.5, fontFace: FONT, bold: true, color: C.blue, margin: 0 });

  const classes = [
    { zh: "地震或建築損壞", en: "Earthquake Damage", c: C.amber },
    { zh: "淹水",           en: "Flood",              c: C.blue  },
    { zh: "火災",           en: "Fire",               c: C.coral },
    { zh: "颱風或強風災損", en: "Typhoon / Storm",    c: C.purple},
    { zh: "土石流或坍方",   en: "Landslide",          c: C.teal  },
    { zh: "其他或無明顯災害",en: "Other / No Disaster",c: C.muted },
  ];
  classes.forEach((cls, i) => {
    const cy = 1.3 + i * 0.56;
    s.addShape(pres.shapes.RECTANGLE, { x: 5.35, y: cy, w: 4.2, h: 0.5, fill: { color: cls.c, transparency: 88 }, line: { color: cls.c, width: 1 } });
    s.addShape(pres.shapes.RECTANGLE, { x: 5.35, y: cy, w: 0.07, h: 0.5, fill: { color: cls.c }, line: { color: cls.c, width: 0 } });
    s.addText([
      { text: cls.zh + "  ", options: { bold: true, color: cls.c, fontFace: "Microsoft YaHei" } },
      { text: cls.en, options: { color: C.muted, fontFace: FONT } },
    ], { x: 5.5, y: cy, w: 4.0, h: 0.5, fontSize: 10, valign: "middle", margin: 0 });
  });

  // Reference
  s.addText("Paper: Radford et al. (2021) — Learning Transferable Visual Models From Natural Language Supervision — ICML 2021", {
    x: 0.4, y: 5.1, w: 9.2, h: 0.22, fontSize: 8.5, fontFace: FONT, color: C.dim, italic: true, margin: 0,
  });
  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 5 — ResNet50
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Model 2: ResNet50 Linear Probe  (Secondary Classifier — A3)", C.green);

  // Left col — specs
  const specs = [
    { k: "Architecture", v: "ResNet50 backbone (frozen, ImageNet pretrained)\n+ nn.Linear(2048 → 5)  replacing fc layer" },
    { k: "Training",     v: "Fine-tuned on QCRI/MEDIC  ·  5 classes  ·  90MB weights\nAdam lr=1e-3  ·  Batch 32  ·  10 epochs  ·  WeightedRandomSampler" },
    { k: "Val Accuracy", v: "~82–85%  (5-class task)" },
    { k: "Weights",      v: "models/resnet50_linear.pth  (90MB)" },
  ];
  specs.forEach((sp, i) => {
    const sy = 0.98 + i * 0.86;
    s.addText(sp.k, { x: 0.4, y: sy, w: 4.65, h: 0.28, fontSize: 10, fontFace: FONT, bold: true, color: C.green, margin: 0 });
    s.addText(sp.v, { x: 0.4, y: sy + 0.28, w: 4.65, h: 0.52, fontSize: 9.5, fontFace: FONT, color: C.text, valign: "top", margin: 0 });
  });

  // Right — class mapping
  s.addText("5-Class Mapping (MEDIC → CrisisLens)", { x: 5.3, y: 0.9, w: 4.3, h: 0.3, fontSize: 11, fontFace: FONT, bold: true, color: C.green, margin: 0 });

  const map5 = [
    { en: "Damaged_Infrastructure", zh: "地震或建築損壞", c: C.amber },
    { en: "Fire_Disaster",          zh: "火災",           c: C.coral },
    { en: "Land_Disaster",          zh: "土石流或坍方",   c: C.teal  },
    { en: "Non_Damage",             zh: "其他或無明顯災害",c: C.muted },
    { en: "Water_Disaster",         zh: "淹水",           c: C.blue  },
  ];
  map5.forEach((m, i) => {
    const my = 1.3 + i * 0.52;
    s.addShape(pres.shapes.RECTANGLE, { x: 5.3, y: my, w: 4.3, h: 0.46, fill: { color: m.c, transparency: 88 }, line: { color: m.c, width: 1 } });
    s.addText([
      { text: m.en + "  →  ", options: { color: C.muted, fontFace: FONT } },
      { text: m.zh, options: { bold: true, color: m.c, fontFace: "Microsoft YaHei" } },
    ], { x: 5.44, y: my, w: 4.0, h: 0.46, fontSize: 9.5, valign: "middle", margin: 0 });
  });

  // Note box
  s.addShape(pres.shapes.RECTANGLE, { x: 5.3, y: 4.0, w: 4.3, h: 0.92, fill: { color: "2D1F00" }, line: { color: C.amber, width: 1.5 } });
  s.addText([
    { text: "Key Design Note:  ", options: { bold: true, color: C.amber } },
    { text: "No Typhoon class (intentional). Typhoon images map to Water_Disaster → model_agreement = 0 → need_review = 1. This educationally demonstrates cross-model class-space mismatch.", options: { color: C.text } },
  ], { x: 5.44, y: 4.0, w: 4.1, h: 0.92, fontSize: 9, fontFace: FONT, valign: "middle", margin: 0 });

  s.addText("Paper: He et al. (2016) — Deep Residual Learning for Image Recognition — CVPR 2016", {
    x: 0.4, y: 5.1, w: 9.2, h: 0.22, fontSize: 8.5, fontFace: FONT, color: C.dim, italic: true, margin: 0,
  });
  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 6 — model_agreement & need_review
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Dual-Model Comparison: model_agreement & need_review  (A4)");

  // Model boxes
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.0, w: 2.6, h: 0.72, fill: { color: C.blue, transparency: 82 }, line: { color: C.blue, width: 1.5 } });
  s.addText(["CLIP ViT-L/14\n", "→ top_class_zh"].map((t, i) => ({ text: t, options: i === 0 ? { bold: true, color: C.blue } : { color: C.muted } })), {
    x: 0.5, y: 1.0, w: 2.6, h: 0.72, fontSize: 10.5, fontFace: FONT, align: "center", valign: "middle", margin: 0,
  });

  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.9, w: 2.6, h: 0.72, fill: { color: C.green, transparency: 82 }, line: { color: C.green, width: 1.5 } });
  s.addText(["ResNet50 LP\n", "→ top_class_zh"].map((t, i) => ({ text: t, options: i === 0 ? { bold: true, color: C.green } : { color: C.muted } })), {
    x: 0.5, y: 1.9, w: 2.6, h: 0.72, fontSize: 10.5, fontFace: FONT, align: "center", valign: "middle", margin: 0,
  });

  // Compare box
  s.addText("→", { x: 3.15, y: 1.52, w: 0.5, h: 0.36, fontSize: 20, color: C.dim, align: "center", margin: 0 });
  s.addText("→", { x: 3.15, y: 2.02, w: 0.5, h: 0.36, fontSize: 20, color: C.dim, align: "center", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 3.65, y: 1.4, w: 2.1, h: 1.1, fill: { color: C.card2 }, line: { color: C.border, width: 1.2 } });
  s.addText("Compare\nChinese Labels", { x: 3.65, y: 1.4, w: 2.1, h: 1.1, fontSize: 10.5, fontFace: FONT, bold: true, color: C.text, align: "center", valign: "middle", margin: 0 });

  // Outcomes
  s.addText("→", { x: 5.8, y: 1.58, w: 0.4, h: 0.35, fontSize: 20, color: C.dim, align: "center", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.2, y: 1.3, w: 3.3, h: 0.6, fill: { color: "0C1F0C" }, line: { color: C.green, width: 1.5 } });
  s.addText("✓  SAME  →  model_agreement = 1", { x: 6.2, y: 1.3, w: 3.3, h: 0.6, fontSize: 10.5, fontFace: FONT, bold: true, color: C.green, align: "center", valign: "middle", margin: 0 });

  s.addText("→", { x: 5.8, y: 2.28, w: 0.4, h: 0.35, fontSize: 20, color: C.dim, align: "center", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.2, y: 2.05, w: 3.3, h: 0.68, fill: { color: "1F0C0C" }, line: { color: C.coral, width: 1.5 } });
  s.addText("✗  DIFFERENT  →  model_agreement = 0\n→  need_review = 1", { x: 6.2, y: 2.05, w: 3.3, h: 0.68, fontSize: 10, fontFace: FONT, bold: true, color: C.coral, align: "center", valign: "middle", margin: 0 });

  // 3 trigger boxes
  s.addText("need_review = 1  triggered by ANY of:", { x: 0.4, y: 3.05, w: 9.2, h: 0.3, fontSize: 11, fontFace: FONT, bold: true, color: C.text, margin: 0 });

  const triggers = [
    { t: "Confidence < 0.50", sub: "CLIP_LOW_CONF_THRESHOLD", c: C.amber },
    { t: "Top-2 gap < 0.15",  sub: "CLIP_TOP2_GAP_THRESHOLD", c: C.amber },
    { t: "model_agreement = 0",sub: "CLIP ≠ ResNet50 label",  c: C.coral },
  ];
  triggers.forEach((tr, i) => {
    const tx = 0.4 + i * 3.15;
    s.addShape(pres.shapes.RECTANGLE, { x: tx, y: 3.42, w: 3.0, h: 0.9, fill: { color: tr.c, transparency: 86 }, line: { color: tr.c, width: 1.5 } });
    s.addText([
      { text: tr.t + "\n", options: { bold: true, color: tr.c, fontSize: 11 } },
      { text: tr.sub, options: { color: C.muted, fontSize: 9 } },
    ], { x: tx, y: 3.42, w: 3.0, h: 0.9, fontFace: FONT, align: "center", valign: "middle", margin: 0 });
  });

  s.addText("All need_review = 1 reports appear in the Admin Dashboard's 'Need Review' filter and the MLOps monitoring page.", {
    x: 0.4, y: 4.48, w: 9.2, h: 0.32, fontSize: 10, fontFace: FONT, color: C.muted, italic: true, margin: 0,
  });

  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 7 — DisasterCNN_v1
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Model 3: DisasterCNN_v1  (Custom-Trained CNN)", C.amber);

  // Left specs
  const specs = [
    { k: "Architecture", v: "4-block CNN  ·  BatchNorm + AdaptiveAvgPool  ·  ~400K params" },
    { k: "Training",     v: "QCRI/MEDIC  ·  6 classes  ·  WeightedRandomSampler\nAdam lr=1e-3  ·  StepLR  ·  5 epochs  ·  Batch 32" },
    { k: "Val Accuracy", v: "68.57%  (6-class task)" },
    { k: "Weights",      v: "models/custom_cnn.pth  (1.5 MB)" },
    { k: "Role",         v: "Standalone auxiliary — 'Custom CNN' mode; CLIP always takes precedence" },
  ];
  specs.forEach((sp, i) => {
    const sy = 0.92 + i * 0.76;
    s.addText(sp.k, { x: 0.4, y: sy, w: 4.7, h: 0.26, fontSize: 10, fontFace: FONT, bold: true, color: C.amber, margin: 0 });
    s.addText(sp.v, { x: 0.4, y: sy + 0.26, w: 4.7, h: 0.45, fontSize: 9.5, fontFace: FONT, color: C.text, valign: "top", margin: 0 });
  });

  // Right — architecture
  s.addText("Architecture", { x: 5.35, y: 0.9, w: 4.2, h: 0.28, fontSize: 11.5, fontFace: FONT, bold: true, color: C.amber, margin: 0 });

  const arch = [
    { t: "Input  (B, 3, 224, 224)",           c: C.muted },
    { t: "Block 1: Conv(3→32) → BN → ReLU → MaxPool  [112×112]",  c: C.amber },
    { t: "Block 2: Conv(32→64) → BN → ReLU → MaxPool  [56×56]",   c: C.amber },
    { t: "Block 3: Conv(64→128) → BN → ReLU → MaxPool  [28×28]",  c: C.amber },
    { t: "Block 4: Conv(128→256) → BN → ReLU → MaxPool  [14×14]", c: C.amber },
    { t: "AdaptiveAvgPool(1×1) → Flatten → Dropout(0.3)",         c: C.blue  },
    { t: "Linear(256 → 6)  →  Softmax",                           c: C.green },
  ];
  arch.forEach((a, i) => {
    const ay = 1.3 + i * 0.46;
    if (i > 0 && i < arch.length) {
      s.addText("↓", { x: 5.35, y: ay - 0.14, w: 0.25, h: 0.18, fontSize: 10, color: C.dim, align: "center", margin: 0 });
    }
    s.addShape(pres.shapes.RECTANGLE, { x: 5.35, y: ay, w: 4.2, h: 0.38, fill: { color: a.c, transparency: 90 }, line: { color: a.c, width: 0.8 } });
    s.addText(a.t, { x: 5.5, y: ay, w: 3.9, h: 0.38, fontSize: 8.5, fontFace: "Courier New", color: a.c, valign: "middle", margin: 0 });
  });

  // Warning note
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.82, w: 9.2, h: 0.42, fill: { color: "1F1500" }, line: { color: C.amber, width: 1 } });
  s.addText("⚠  Typhoon recall ~48% — expected weakness: MEDIC 'hurricane' imagery ≠ Taiwan typhoon visual patterns (domain gap)", {
    x: 0.54, y: 4.82, w: 8.92, h: 0.42, fontSize: 9.5, fontFace: FONT, color: C.amber, valign: "middle", margin: 0,
  });

  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 8 — Citizen Reporting Flow
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "B. Citizen Disaster Reporting Flow");

  // 7-step flow
  const steps = [
    { n: "1", t: "Login /\nRegister",     c: C.muted },
    { n: "2", t: "Upload Photo\n(EXIF stripped)",c: C.green},
    { n: "3", t: "GPS Location",           c: C.blue  },
    { n: "4", t: "Fill Conditions",        c: C.blue  },
    { n: "5", t: "AI Analyse",             c: C.amber },
    { n: "6", t: "Review\nResults",        c: C.amber },
    { n: "7", t: "Submit\nReport",         c: C.coral },
  ];
  const sw = 1.22, sh = 0.68, sy = 0.88, sgap = 0.1;
  const stot = steps.length * sw + (steps.length - 1) * sgap;
  let ssx = (10 - stot) / 2;

  steps.forEach((st, i) => {
    s.addShape(pres.shapes.RECTANGLE, { x: ssx, y: sy, w: sw, h: sh, fill: { color: st.c, transparency: 80 }, line: { color: st.c, width: 1.5 } });
    s.addShape(pres.shapes.OVAL, { x: ssx + 0.04, y: sy + 0.04, w: 0.26, h: 0.26, fill: { color: st.c }, line: { color: st.c, width: 0 } });
    s.addText(st.n, { x: ssx + 0.04, y: sy + 0.04, w: 0.26, h: 0.26, fontSize: 9, fontFace: FONT, bold: true, color: C.bg, align: "center", valign: "middle", margin: 0 });
    s.addText(st.t, { x: ssx, y: sy + 0.3, w: sw, h: sh - 0.3, fontSize: 8.5, fontFace: FONT, bold: true, color: st.c, align: "center", valign: "middle", margin: 0 });
    if (i < steps.length - 1) {
      s.addText("→", { x: ssx + sw, y: sy + 0.18, w: sgap, h: 0.32, fontSize: 14, color: C.dim, align: "center", margin: 0 });
    }
    ssx += sw + sgap;
  });

  // Two-column detail
  // Left — AI does on Step 5
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.74, w: 4.6, h: 2.88, fill: { color: C.card }, line: { color: C.amber, width: 1.2 } });
  s.addText("What AI does (Step 5)", { x: 0.55, y: 1.8, w: 4.3, h: 0.3, fontSize: 10.5, fontFace: FONT, bold: true, color: C.amber, margin: 0 });
  const aiDoes = [
    "CLIP ViT-L/14 classification → Top-3 probabilities",
    "ResNet50 secondary classification (if mode selected)",
    "model_agreement computation (label comparison)",
    "Top-2 gap & confidence threshold checks → need_review",
    "RAG: FAISS retrieval → Gemini 2.0 Flash advisory generation",
    "Safety guard: keyword → Gemini safety API → ShieldGemma",
  ];
  s.addText(aiDoes.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < aiDoes.length - 1, color: C.text } })), {
    x: 0.55, y: 2.16, w: 4.3, h: 2.3,
    fontSize: 9.5, fontFace: FONT, valign: "top", margin: 0, paraSpaceAfter: 5,
  });

  // Right — System does on Step 7
  s.addShape(pres.shapes.RECTANGLE, { x: 5.1, y: 1.74, w: 4.5, h: 2.88, fill: { color: C.card }, line: { color: C.coral, width: 1.2 } });
  s.addText("What system does (Step 7)", { x: 5.25, y: 1.8, w: 4.2, h: 0.3, fontSize: 10.5, fontFace: FONT, bold: true, color: C.coral, margin: 0 });
  const sysDoes = [
    "Rate limit check: max 10 reports/hour/user",
    "EXIF-stripped image stored (Azure Blob / local)",
    "Event aggregation v4: disaster type + location + time window",
    "H3 grid_summary updated (res 9 / district / city fallback)",
    "model_runs record written: all 7 version strings logged",
    "Priority Score calculated: Severity×0.5 + Vuln×0.3 + Cred×0.2",
  ];
  s.addText(sysDoes.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < sysDoes.length - 1, color: C.text } })), {
    x: 5.25, y: 2.16, w: 4.2, h: 2.3,
    fontSize: 9.5, fontFace: FONT, valign: "top", margin: 0, paraSpaceAfter: 5,
  });

  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 9 — Admin Dashboard
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "C. Admin Dashboard & Event Management");

  const boxes = [
    { x: 0.3, y: 0.88, label: "Event Dashboard", c: C.blue,
      body: "Priority Score sorting (High/Medium/Low)\nDisaster type · city · status filters\nNeed Review filter checkbox\n4 stat cards incl. need_review count\nEvent status update buttons" },
    { x: 5.15, y: 0.88, label: "Event Detail", c: C.green,
      body: "Per-report photos + AI predictions\nSafety labels (input_safety / output_safety)\nAdmin Corrections form → admin_corrections table\nneed_review badges per report\nTop-3 confidence breakdown" },
    { x: 0.3, y: 3.12, label: "Priority Score Formula", c: C.amber,
      body: "Score = Severity × 0.50 + Vulnerability × 0.30 + Credibility × 0.20\n\nHigh ≥ 70  ·  Medium 40–69  ·  Low < 40\n\nSeverity: injuries, trapped persons, road block, AI confidence\nVulnerability: estimated affected persons\nCredibility: report count + model_agreement ratio" },
    { x: 5.15, y: 3.12, label: "Event Status Lifecycle", c: C.coral,
      body: "pending_review  →  active  →  resolved  →  archived\n\nEvery transition logged in admin_action_logs\n(admin_user · old_value · new_value · reason · timestamp)\n\nResolved events hidden from H3 heatmap by default" },
  ];

  boxes.forEach(b => {
    s.addShape(pres.shapes.RECTANGLE, { x: b.x, y: b.y, w: 4.55, h: 2.1, fill: { color: C.card }, line: { color: b.c, width: 1.5 }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: b.x, y: b.y, w: 4.55, h: 0.34, fill: { color: b.c, transparency: 75 }, line: { width: 0 } });
    s.addText(b.label, { x: b.x + 0.12, y: b.y + 0.03, w: 4.3, h: 0.28, fontSize: 11, fontFace: FONT, bold: true, color: C.white, margin: 0 });
    s.addText(b.body, { x: b.x + 0.12, y: b.y + 0.42, w: 4.3, h: 1.6, fontSize: 9.5, fontFace: FONT, color: C.text, valign: "top", margin: 0, paraSpaceAfter: 4 });
  });

  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 10 — H3 Heatmap
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "D. H3 Hexagonal Heatmap  (GIS)", C.teal);

  // Left — big stat display
  s.addText("Multi-Scale\nHexagonal\nHeatmap", {
    x: 0.4, y: 1.0, w: 3.8, h: 1.5,
    fontSize: 22, fontFace: FONT, bold: true, color: C.teal,
    align: "center", valign: "middle", margin: 0,
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 2.55, w: 3.8, h: 0.55, fill: { color: C.teal, transparency: 85 }, line: { color: C.teal, width: 1 } });
  s.addText("H3 Res 5 → 7 → 9  (zoom-based)", { x: 0.4, y: 2.55, w: 3.8, h: 0.55, fontSize: 10.5, fontFace: FONT, bold: true, color: C.teal, align: "center", valign: "middle", margin: 0 });

  // Res levels visual
  const resBars = [
    { r: "Res 5", d: "County level  (~100km)", c: C.teal },
    { r: "Res 7", d: "Township level  (~10km)", c: C.blue },
    { r: "Res 9", d: "Neighborhood  (~174m)",   c: C.green },
  ];
  resBars.forEach((rb, i) => {
    const ry = 3.22 + i * 0.46;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: ry, w: 3.8, h: 0.4, fill: { color: rb.c, transparency: 85 }, line: { color: rb.c, width: 1 } });
    s.addText([
      { text: rb.r + "  ", options: { bold: true, color: rb.c } },
      { text: rb.d, options: { color: C.muted } },
    ], { x: 0.55, y: ry, w: 3.5, h: 0.4, fontSize: 10, fontFace: FONT, valign: "middle", margin: 0 });
  });

  // Right — feature list
  const features = [
    { t: "3-Layer Location Fallback", d: "h3 (GPS) → district → city  (no GPS = no heatmap exclusion)", c: C.blue  },
    { t: "Zoom-Based Resolution Switching", d: "Map zoom level determines which H3 resolution layer is active", c: C.teal  },
    { t: "Resolved Event Filter", d: "Sidebar toggle: hide/show archived events (default: hide)", c: C.green },
    { t: "Interactive Tooltip", d: "Report count · Priority level · Estimated affected persons", c: C.amber },
    { t: "Why Hexagons?", d: "H3 topology: equal-distance neighbors in all 6 directions, no edge/corner bias vs. square grids", c: C.purple },
  ];
  features.forEach((f, i) => {
    const fy = 0.88 + i * 0.86;
    s.addShape(pres.shapes.RECTANGLE, { x: 4.5, y: fy, w: 5.1, h: 0.78, fill: { color: C.card }, line: { color: f.c, width: 1.2 } });
    s.addText([
      { text: f.t + "\n", options: { bold: true, color: f.c, fontSize: 10 } },
      { text: f.d, options: { color: C.text, fontSize: 9 } },
    ], { x: 4.64, y: fy, w: 4.82, h: 0.78, fontFace: FONT, valign: "middle", margin: 0 });
  });

  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 11 — MLOps
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "E. MLOps Monitoring & Version Tracking");

  const panels = [
    {
      x: 0.3, y: 0.88, w: 3.0, label: "Version Tracking", c: C.blue,
      body: "Every inference writes to model_runs:\n\nclip-vitl14-v1\nresnet50-linear-probe-medic-5class-v1\ncustom-cnn-medic-6class-v1\nfaiss-multilingual-minilm-v1\ndisaster-group-distance-timewindow-v4\nsvcp-weighted-v2",
    },
    {
      x: 3.5, y: 0.88, w: 3.0, label: "Admin Corrections", c: C.purple,
      body: "Human labels in admin_corrections:\n\n• corrected_by  ·  report_id\n• original_value  →  corrected_value\n• correction_reason\n• used_for_retraining flag (0/1)\n\nMLOps page: pending vs. used counts",
    },
    {
      x: 6.7, y: 0.88, w: 2.9, label: "Retraining Signals", c: C.amber,
      body: "Trigger conditions:\n\nneed_review rate > 30%\nover 100 consecutive reports\n\nmodel_agreement rate < 60%\nover any 7-day window",
    },
  ];

  panels.forEach(p => {
    s.addShape(pres.shapes.RECTANGLE, { x: p.x, y: p.y, w: p.w, h: 3.8, fill: { color: C.card }, line: { color: p.c, width: 1.5 }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: p.x, y: p.y, w: p.w, h: 0.34, fill: { color: p.c, transparency: 74 }, line: { width: 0 } });
    s.addText(p.label, { x: p.x + 0.1, y: p.y + 0.03, w: p.w - 0.2, h: 0.28, fontSize: 10.5, fontFace: FONT, bold: true, color: C.white, margin: 0 });
    s.addText(p.body, { x: p.x + 0.12, y: p.y + 0.42, w: p.w - 0.24, h: 3.28, fontSize: 9, fontFace: "Courier New", color: C.text, valign: "top", margin: 0, paraSpaceAfter: 5 });
  });

  // Retraining triggers in amber
  const trigY = 4.83;
  s.addShape(pres.shapes.RECTANGLE, { x: 6.7, y: trigY, w: 2.9, h: 0.42, fill: { color: "1F1800" }, line: { color: C.amber, width: 1 } });
  s.addText("⚠  need_review > 30%  →  Retrain!", { x: 6.82, y: trigY, w: 2.66, h: 0.42, fontSize: 9, fontFace: FONT, bold: true, color: C.amber, valign: "middle", margin: 0 });

  s.addText("UI: pages/6_MLOps.py — 3 tabs:  Model Runs  |  Admin Corrections  |  Need Review Reports", {
    x: 0.3, y: 5.08, w: 9.2, h: 0.26, fontSize: 9, fontFace: FONT, color: C.muted, italic: true, margin: 0,
  });
  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 12 — Data Card
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "F. Data Card  (MLSecOps Workshop 1 Format)");

  const cols = [
    {
      x: 0.25, label: "QCRI/MEDIC Dataset", c: C.blue,
      lines: [
        "~17,600 images (social media)",
        "7 original → 6 CrisisLens classes",
        "80/20 train/val split (seed=42)",
        "WeightedRandomSampler (38% Other)",
        "Bias: Western hemisphere images",
        "Domain gap: hurricane ≠ typhoon",
        "Geographic coverage: 2012–2020",
        "Pre-processing: Resize(256) →",
        "  CenterCrop(224) → ImageNet norm",
      ],
    },
    {
      x: 3.55, label: "Production Data (CrisisLens)", c: C.green,
      lines: [
        "User-submitted disaster photos",
        "GPS + city/district metadata",
        "EXIF stripped at upload",
        "Key fields:",
        "  disaster_type  ·  clip_confidence",
        "  need_review  ·  model_agreement",
        "  input/output_safety_label",
        "  rag_advice (JSON)",
        "Privacy: GPS coords = High risk",
      ],
    },
    {
      x: 6.85, label: "RAG Knowledge Base", c: C.amber,
      lines: [
        "6 SOP documents (zh-TW)",
        "Taiwan govt disaster guidelines",
        "earthquake / flood / fire",
        "typhoon / landslide / emergency",
        "Chunk: 400 chars / 80 overlap",
        "Embedding: multilingual MiniLM",
        "  (384-dimensional vectors)",
        "Index: FAISS Flat L2",
        "Version: faiss-minilm-v1",
      ],
    },
  ];

  cols.forEach(col => {
    s.addShape(pres.shapes.RECTANGLE, { x: col.x, y: 0.88, w: 3.1, h: 4.35, fill: { color: C.card }, line: { color: col.c, width: 1.5 }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: col.x, y: 0.88, w: 3.1, h: 0.34, fill: { color: col.c, transparency: 74 }, line: { width: 0 } });
    s.addText(col.label, { x: col.x + 0.1, y: 0.91, w: 2.9, h: 0.28, fontSize: 10, fontFace: FONT, bold: true, color: C.white, margin: 0 });
    s.addText(col.lines.join("\n"), {
      x: col.x + 0.14, y: 1.3, w: 2.82, h: 3.82,
      fontSize: 9, fontFace: FONT, color: C.text, valign: "top", margin: 0, paraSpaceAfter: 3,
    });
  });

  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 13 — Model Card Table
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "G. Model Card Summary  (MLSecOps Workshop 1 Format)");

  const hdrFill  = { color: "1C2D42" };
  const cellFill = { color: C.card };
  const boldHdr  = (text) => ({ text, options: { bold: true, color: C.blue,   fontFace: FONT, fontSize: 10 } });
  const cellTxt  = (text, col) => ({ text, options: { color: col || C.text, fontFace: FONT, fontSize: 9 } });

  const tRows = [
    [
      boldHdr("Aspect"),
      boldHdr("CLIP ViT-L/14"),
      boldHdr("ResNet50 LP"),
      boldHdr("DisasterCNN_v1"),
      boldHdr("RAG System"),
    ],
    [
      cellTxt("Role", C.muted),
      cellTxt("Primary classifier"),
      cellTxt("Secondary classifier"),
      cellTxt("Auxiliary (standalone)"),
      cellTxt("Response advisor"),
    ],
    [
      cellTxt("Training", C.muted),
      cellTxt("OpenAI pretrained (zero-shot)"),
      cellTxt("MEDIC fine-tuned\n5-class LP"),
      cellTxt("From scratch\n6-class full train"),
      cellTxt("Static KB +\nGemini LLM"),
    ],
    [
      cellTxt("Params", C.muted),
      cellTxt("431M"),
      cellTxt("~25M (frozen)"),
      cellTxt("~400K"),
      cellTxt("N/A"),
    ],
    [
      cellTxt("Accuracy", C.muted),
      cellTxt("Qualitative: High", C.green),
      cellTxt("Val ~82–85%", C.green),
      cellTxt("Val 68.57%", C.amber),
      cellTxt("N/A"),
    ],
    [
      cellTxt("Failure", C.muted),
      cellTxt("Adversarial\nimages", C.coral),
      cellTxt("Typhoon→Water\n(expected)", C.amber),
      cellTxt("Typhoon 48%\nrecall", C.coral),
      cellTxt("Gemini API\nunavailable"),
    ],
    [
      cellTxt("Mitigation", C.muted),
      cellTxt("Confidence +\ngap thresholds"),
      cellTxt("model_agreement\nflag → review"),
      cellTxt("CLIP always\ntakes precedence"),
      cellTxt("Static fallback\nguidelines"),
    ],
  ];

  s.addTable(tRows, {
    x: 0.3, y: 0.88, w: 9.4,
    colW: [1.4, 2.0, 2.0, 2.0, 2.0],
    border: { pt: 0.8, color: C.border },
    fill: cellFill,
    rowH: 0.56,
    align: "center",
    valign: "middle",
  });

  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 14 — Security
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "H. AI Security & Safety Considerations");

  const secBoxes = [
    {
      x: 0.28, y: 0.88,
      label: "1. Adversarial Attacks",
      c: C.coral,
      threat: "FGSM/PGD pixel perturbations fool CLIP/ResNet50 into classifying real disasters as 'No Disaster'",
      defence: "Dual-model agreement: attacker must fool BOTH independently-trained models simultaneously. Confidence threshold + Top-2 gap → need_review pipeline.",
      refs: "Goodfellow 2015 (FGSM); Madry 2018 (PGD)",
    },
    {
      x: 5.12, y: 0.88,
      label: "2. RAG Poisoning",
      c: C.amber,
      threat: "Malicious document injection into FAISS KB → Gemini generates harmful evacuation advice",
      defence: "Static, version-controlled SOPs (6 files, admin-only rebuild). Index version logged in every model_runs record. Mandatory non-reliance disclaimer on all output.",
      refs: "Zou 2024; Greshake 2023",
    },
    {
      x: 0.28, y: 3.05,
      label: "3. Prompt Injection",
      c: C.purple,
      threat: "Malicious disaster description text hijacks Gemini 2.0 Flash output via embedded instructions",
      defence: "3-layer ShieldGemma guard: keyword filter → Gemini safety API → local ShieldGemma model. User text in <user_report> block, not instruction block. Rate limit: 10 reports/hr.",
      refs: "Perez & Ribeiro 2022; Branch et al. 2022",
    },
    {
      x: 5.12, y: 3.05,
      label: "4. EXIF GPS Leakage",
      c: C.teal,
      threat: "JPEG EXIF GPS tags expose reporter's precise home/workplace coordinates to unauthorized parties",
      defence: "strip_exif() in utils/image_utils.py: pixel-level PIL Image rebuild. Zero EXIF in database or Azure Blob. Called unconditionally in load_image() before analysis or storage.",
      refs: "GDPR Art. 4(1) — location = personal data",
    },
  ];

  secBoxes.forEach(b => {
    s.addShape(pres.shapes.RECTANGLE, { x: b.x, y: b.y, w: 4.55, h: 2.08, fill: { color: C.card }, line: { color: b.c, width: 1.5 }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: b.x, y: b.y, w: 4.55, h: 0.32, fill: { color: b.c, transparency: 75 }, line: { width: 0 } });
    s.addText(b.label, { x: b.x + 0.12, y: b.y + 0.02, w: 4.3, h: 0.28, fontSize: 10.5, fontFace: FONT, bold: true, color: C.white, margin: 0 });
    s.addText([
      { text: "Threat:  ", options: { bold: true, color: C.coral } },
      { text: b.threat + "\n", options: { color: C.text } },
      { text: "Defence:  ", options: { bold: true, color: C.green } },
      { text: b.defence + "\n", options: { color: C.text } },
      { text: "Ref: ", options: { bold: true, color: C.muted } },
      { text: b.refs, options: { color: C.dim, italic: true } },
    ], { x: b.x + 0.12, y: b.y + 0.38, w: 4.3, h: 1.64, fontSize: 8.5, fontFace: FONT, valign: "top", margin: 0, paraSpaceAfter: 4 });
  });

  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 15 — Platform Demo UI Overview
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.bg };
  addTitle(s, "Platform Demo — Key UI Pages");

  const pages = [
    { t: "Citizen Portal",      sub: "app.py",                     d: "Upload photo · AI Analyse · Select model (CLIP / ResNet50 / CNN)\nGPS location · Disaster conditions · Rate-limited submit", c: C.blue   },
    { t: "Model Comparison",    sub: "app.py — sidebar mode",       d: "CLIP vs ResNet50 side-by-side\nmodel_agreement badge · need_review badge · Top-2 gap display", c: C.green  },
    { t: "Event Dashboard",     sub: "pages/2_Event_Dashboard.py",  d: "Priority-sorted event cards · 4 stat counters\nNeed Review filter · Disaster type / city / status filters", c: C.amber  },
    { t: "Event Detail",        sub: "pages/3_Event_Detail.py",     d: "Per-report photos + Top-3 predictions\nSafety labels · Admin Corrections form · need_review badges", c: C.coral  },
    { t: "H3 Heatmap",         sub: "pages/4_H3_Heatmap.py",       d: "Multi-scale hexagonal map over Taiwan\nZoom-based res switching · Resolved event toggle · Tooltips", c: C.teal   },
    { t: "MLOps Dashboard",     sub: "pages/6_MLOps.py",            d: "3 tabs: Model Runs · Admin Corrections · Need Review\nVersion tracking · Retraining signals · need_review rate", c: C.purple },
  ];

  const bw = 4.6, bh = 1.42, bgap = 0.2;
  const positions = [
    { x: 0.25, y: 0.88 }, { x: 5.15, y: 0.88 },
    { x: 0.25, y: 2.42 }, { x: 5.15, y: 2.42 },
    { x: 0.25, y: 3.96 }, { x: 5.15, y: 3.96 },
  ];

  pages.forEach((pg, i) => {
    const pos = positions[i];
    s.addShape(pres.shapes.RECTANGLE, { x: pos.x, y: pos.y, w: bw, h: bh, fill: { color: C.card }, line: { color: pg.c, width: 1.5 }, shadow: mkShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: pos.x, y: pos.y, w: 0.06, h: bh, fill: { color: pg.c }, line: { color: pg.c, width: 0 } });
    s.addText([
      { text: pg.t + "\n", options: { bold: true, color: pg.c, fontSize: 11 } },
      { text: pg.sub + "\n", options: { color: C.dim, fontSize: 8.5, italic: true } },
      { text: pg.d, options: { color: C.text, fontSize: 9 } },
    ], { x: pos.x + 0.18, y: pos.y + 0.1, w: bw - 0.28, h: bh - 0.2, fontFace: FONT, valign: "top", margin: 0, paraSpaceAfter: 3 });
  });

  addFooter(s);
}

// ═══════════════════════════════════════════════════════════
// SLIDE 16 — Conclusion
// ═══════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: "0A1628" };
  addTitle(s, "Conclusion & Future Work", C.blue);

  // Left — achieved
  s.addText("What We Built", { x: 0.4, y: 0.9, w: 4.4, h: 0.32, fontSize: 13, fontFace: FONT, bold: true, color: C.green, margin: 0 });

  const done = [
    "3-model NN pipeline: CLIP + ResNet50 + DisasterCNN",
    "RAG advisory: FAISS + Gemini 2.0 Flash + fallback",
    "Event aggregation v4: type + location + time window",
    "H3 multi-scale heatmap (Res 5/7/9 zoom switching)",
    "MLOps version tracking (model_runs + admin_corrections)",
    "4 AI security mitigations implemented",
    "Data Card + Model Card (MLSecOps Workshop 1 format)",
    "EXIF GPS stripping at point of upload",
    "Admin Corrections → retraining data pipeline",
  ];
  done.forEach((d, i) => {
    s.addText([
      { text: "✓  ", options: { bold: true, color: C.green } },
      { text: d, options: { color: C.text } },
    ], { x: 0.4, y: 1.26 + i * 0.43, w: 4.4, h: 0.38, fontSize: 10, fontFace: FONT, margin: 0 });
  });

  // Right — future work
  s.addText("Future Work", { x: 5.25, y: 0.9, w: 4.3, h: 0.32, fontSize: 13, fontFace: FONT, bold: true, color: C.amber, margin: 0 });

  const future = [
    "Formal adversarial evaluation (AutoAttack / certified defence)",
    "Taiwan-specific fine-tuning dataset collection",
    "Real-time video stream classification",
    "Automated retraining CI/CD pipeline",
    "Multi-label disaster classification",
    "Federated learning for privacy-preserving fine-tuning",
    "GitHub Actions CI + automated pytest coverage",
  ];
  future.forEach((f, i) => {
    s.addText([
      { text: "→  ", options: { bold: true, color: C.amber } },
      { text: f, options: { color: C.text } },
    ], { x: 5.25, y: 1.26 + i * 0.43, w: 4.3, h: 0.38, fontSize: 10, fontFace: FONT, margin: 0 });
  });

  // Bottom tagline
  s.addShape(pres.shapes.RECTANGLE, { x: 1.5, y: 5.08, w: 7.0, h: 0.34, fill: { color: C.blue, transparency: 90 }, line: { color: C.blue, width: 1 } });
  s.addText("SDG 11 + SDG 13  |  CrisisLens v2.0  |  CLIP + ResNet50 + RAG + H3 + MLOps  |  2026", {
    x: 1.5, y: 5.08, w: 7.0, h: 0.34, fontSize: 9, fontFace: FONT, bold: true, color: C.blue, align: "center", valign: "middle", margin: 0,
  });
}

// ── Write file ───────────────────────────────────────────────
pres.writeFile({ fileName: OUT })
  .then(() => console.log("PPT written:", OUT))
  .catch(err => { console.error(err); process.exit(1); });
