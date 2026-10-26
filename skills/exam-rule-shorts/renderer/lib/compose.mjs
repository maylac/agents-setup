// Turns one episode object into a self-contained HyperFrames project directory:
//   build/<id>/index.html   (static, stable ids, editable)
//   build/<id>/styles.css   (copied from template/)
//   build/<id>/motion.js    (copied from template/; builds the GSAP timeline)
//   build/<id>/gsap.min.js  (vendored, no CDN at render time)
//   build/<id>/audio/episode.wav (written by audio.mjs)
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join, relative, resolve, sep } from "node:path";
import { visualLength } from "./validate.mjs";

const require = createRequire(import.meta.url);
const TEMPLATE_DIR = join(import.meta.dirname, "..", "template");
const PROJECT_DIR = resolve(import.meta.dirname, "../..");
const ICON_MAP_PATH = join(PROJECT_DIR, "icon-map.json");
const ICON_MAP = existsSync(ICON_MAP_PATH) ? JSON.parse(readFileSync(ICON_MAP_PATH, "utf8")) : { nodes: {} };
const ICON_CACHE = new Map();

export const W = 1080;
export const H = 1920;
const STAGE_W = 936;
const STAGE_H = 720;
const ICON_DIR = join(PROJECT_DIR, "assets", "icons");
const ACCENTS = ["blue", "green", "orange", "ink"];

const esc = (s = "") =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const r1 = (n) => Math.round(n * 10) / 10;

// Box layouts inside the diagram stage (stage-local px).
function layoutNodes(count) {
  const h = 290;
  const y2 = STAGE_H - h - 10;
  // Two nodes sit side by side so both icons can stay large.
  if (count === 2) return [{ x: 0, y: 150, w: 440, h: 400 }, { x: STAGE_W - 440, y: 150, w: 440, h: 400 }];
  const w = 360;
  if (count === 3) return [{ x: 0, y: 10, w, h }, { x: STAGE_W - w, y: 10, w, h }, { x: (STAGE_W - w) / 2, y: y2, w, h }];
  return [{ x: 0, y: 10, w, h }, { x: STAGE_W - w, y: 10, w, h }, { x: STAGE_W - w, y: y2, w, h }, { x: 0, y: y2, w, h }];
}

// Distance from a box centre to its border along unit vector (dx, dy).
function borderDist(box, dx, dy) {
  const tx = Math.abs(dx) > 1e-6 ? box.w / 2 / Math.abs(dx) : Infinity;
  const ty = Math.abs(dy) > 1e-6 ? box.h / 2 / Math.abs(dy) : Infinity;
  return Math.min(tx, ty);
}

function layoutEdges(edges, boxes) {
  const pairs = new Set(edges.map((e) => `${e.from}>${e.to}`));
  return edges.map((e, i) => {
    const a = boxes[e.from];
    const b = boxes[e.to];
    let ax = a.x + a.w / 2, ay = a.y + a.h / 2, bx = b.x + b.w / 2, by = b.y + b.h / 2;
    const len0 = Math.hypot(bx - ax, by - ay);
    const dx = (bx - ax) / len0, dy = (by - ay) / len0;
    // Two-way edges are pushed apart so both arrows stay visible.
    const paired = pairs.has(`${e.to}>${e.from}`);
    const ox = -dy, oy = dx; // this edge's offset side (unit normal)
    if (paired) {
      const off = 26;
      ax += ox * off; ay += oy * off; bx += ox * off; by += oy * off;
    }
    const gap = 18;
    const x1 = ax + dx * (borderDist(a, dx, dy) + gap);
    const y1 = ay + dy * (borderDist(a, dx, dy) + gap);
    const x2 = bx - dx * (borderDist(b, dx, dy) + gap);
    const y2 = by - dy * (borderDist(b, dx, dy) + gap);
    const len = Math.max(40, Math.hypot(x2 - x1, y2 - y1));
    const angle = (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI;
    // Label sits beside the line, never on top of packets. Paired edges put it
    // on their outward side so it cannot collide with the partner arrow.
    const vertical = Math.abs(dy) > 0.9;
    let sx = ox, sy = oy;
    if (!paired && sy > 0) { sx = -sx; sy = -sy; } // prefer above the line
    const labelOff = vertical ? 0 : paired ? 52 : 46; // vertical lines: side placement via CSS
    const mx = Math.max(132, Math.min(STAGE_W - 132, (x1 + x2) / 2 + sx * labelOff));
    const my = Math.max(30, Math.min(STAGE_H - 30, (y1 + y2) / 2 + sy * labelOff));
    const side = sx < 0 ? "left" : "right";
    return { i, from: e.from, to: e.to, label: e.label || "", x1, y1, len, angle, mx, my, vertical, side };
  });
}

function titleSize(t) {
  const n = visualLength(t);
  return n <= 20 ? 88 : n <= 30 ? 76 : n <= 40 ? 66 : 58;
}
// Largest size at which the label fits on one line of the box (bold Latin ~0.66-0.8em,
// full-width ~1em); below the floor it wraps to two lines at the floor size.
function labelSize(t, wide, icon = false) {
  let em = 0;
  for (const ch of String(t)) em += ch.charCodeAt(0) > 0xff ? 1.02 : ch === " " ? 0.3 : /[A-Z]/.test(ch) ? 0.8 : 0.66;
  const inner = icon ? (wide ? 420 : 340) : (wide ? 400 : 300);
  const max = icon ? (wide ? 52 : 42) : (wide ? 56 : 52);
  return Math.max(icon ? 28 : 30, Math.min(max, Math.floor(inner / Math.max(em, 1))));
}
// Official AWS Architecture Icons named on the node itself ("icon": "Arch_Amazon-CloudFront_64"
// or a list of up to two), falling back to the per-batch icon-map.json.
function serviceIcon(ep, sc, nodeIndex, node = {}) {
  const key = `${ep}/${sc}/${nodeIndex}`;
  if (node.icon) {
    const names = Array.isArray(node.icon) ? node.icon : [node.icon];
    const sources = names.map((name) => {
      if (!/^[A-Za-z0-9][A-Za-z0-9_.-]+$/.test(name)) throw new Error(`${key}: icon must be an official asset name, got ${name}`);
      // Dark theme: use the official dark variant of line icons when the package ships one.
      const dark = name.endsWith("_Light") ? join(ICON_DIR, `${name.slice(0, -6)}_Dark.svg`) : null;
      const path = dark && existsSync(dark) ? dark : join(ICON_DIR, `${name}.svg`);
      if (!existsSync(path)) throw new Error(`${key}: icon not found in the official package: ${name}`);
      if (!ICON_CACHE.has(path)) ICON_CACHE.set(path, `data:image/svg+xml;base64,${readFileSync(path).toString("base64")}`);
      return { asset: name, src: ICON_CACHE.get(path) };
    });
    return { key, service: node.service || node.label, sources };
  }
  const entry = ICON_MAP.nodes?.[key];
  if (!entry) return null;
  const assets = Array.isArray(entry.assets) && entry.assets.length ? entry.assets : [entry.asset];
  if (assets.some((asset) => !asset)) throw new Error(`${key}: icon mapping has an empty asset path`);
  const sources = assets.map((assetValue) => {
    const asset = String(assetValue);
    if (!asset.startsWith("assets/icons/")) throw new Error(`${key}: icon asset must be under assets/icons/`);
    const path = resolve(PROJECT_DIR, asset);
    const rel = relative(join(PROJECT_DIR, "assets", "icons"), path);
    if (rel === ".." || rel.startsWith(`..${sep}`) || !existsSync(path)) throw new Error(`${key}: icon asset escapes assets/icons or is missing: ${asset}`);
    if (!ICON_CACHE.has(path)) {
      const svg = readFileSync(path);
      ICON_CACHE.set(path, `data:image/svg+xml;base64,${svg.toString("base64")}`);
    }
    return { asset, src: ICON_CACHE.get(path) };
  });
  return { ...entry, key, sources };
}
function captionSize(t) {
  const n = visualLength(t);
  return n <= 22 ? 46 : n <= 32 ? 40 : 34;
}
function shortUrl(u = "") {
  return u.replace(/^https?:\/\//, "").replace(/\/$/, "").slice(0, 64) + (u.length > 72 ? "…" : "");
}

export function sceneTimings(ep) {
  let t = 0;
  return ep.scenes.map((s) => {
    const start = t;
    t += s.duration;
    return { start: Math.round(start * 1000) / 1000, duration: s.duration };
  });
}

function sceneHtml(ep, sc, si, timing) {
  const sid = `s${si + 1}`;
  const accent = ACCENTS[si % ACCENTS.length];
  const boxes = layoutNodes(sc.nodes.length);
  // Unboxed icon nodes: arrows stop at the drawn icon and label, not at the invisible layout box.
  const edgeBoxes = boxes.map((b, i) => (sc.nodes[i]?.icon ? { ...b, x: b.x + (b.w - Math.min(b.w, 270)) / 2, w: Math.min(b.w, 270) } : b));
  const edges = layoutEdges(sc.edges || [], edgeBoxes);
  const wide = sc.nodes.length === 2;
  const bodyLines = String(sc.body || "").split("\n").map(esc).join("<br />");
  const chunks = Array.isArray(sc.caption_chunks) && sc.caption_chunks.length ? sc.caption_chunks : null;
  const captionHtml = chunks
    ? chunks.map((c, ci) => `<span id="${sid}-caption-chunk-${ci}" class="caption-chunk">${esc(c.text || "")}</span>`).join("")
    : esc(sc.caption);

  const nodesHtml = sc.nodes
    .map((n, ni) => {
      const b = boxes[ni];
      const icon = serviceIcon(ep.id, sc.id, ni, n);
      const fontSize = labelSize(n.label, wide, Boolean(icon));
      const label = `<strong class="node-label${!icon && fontSize > 30 ? " one-line" : ""}" style="font-size:${fontSize}px">${esc(n.label)}</strong>`;
      const sub = n.sub ? `<span class="node-sub">${esc(n.sub)}</span>` : "";
      const content = icon
        ? `<span class="node-icons ${icon.sources.length > 1 ? "multiple" : "single"}" aria-label="${esc(icon.service)}">${icon.sources.map((source, iconIndex) => `<img class="service-icon" data-icon-key="${esc(icon.key)}" data-icon-index="${iconIndex}" data-service="${esc(icon.service)}" alt="" aria-hidden="true" src="${source.src}">`).join("")}</span><span class="node-copy">${label}${sub}</span>`
        : `${label}${sub}`;
      return `
          <div id="${sid}-node-${ni}" class="node accent-${ACCENTS[ni % ACCENTS.length]}${icon ? ` has-service-icon icon-column${wide ? " wide" : ""}` : ""}" style="left:${r1(b.x)}px;top:${r1(b.y)}px;width:${b.w}px;height:${b.h}px">
            <span class="node-index">${ni + 1}</span>
            ${content}
          </div>`;
    })
    .join("");

  const edgesHtml = edges
    .map(
      (e) => `
          <div id="${sid}-edge-${e.i}" class="edge" style="left:${r1(e.x1)}px;top:${r1(e.y1)}px;width:${r1(e.len)}px;transform:rotate(${r1(e.angle)}deg)">
            <div class="edge-line"></div>
            <div class="edge-head"></div>
            <div id="${sid}-edge-${e.i}-pkt-a" class="packet"></div>
            <div id="${sid}-edge-${e.i}-pkt-b" class="packet"></div>
            ${e.i === 0 && sc.wrong ? `<div id="${sid}-wrong-pkt" class="packet packet-wrong"></div><div class="pin" style="left:${r1(e.len / 2)}px;transform:rotate(${r1(-e.angle)}deg)"><div id="${sid}-wrong-x" class="block-x">✕</div></div>` : ""}
          </div>${
            e.label
              ? `
          <div class="pin label-pin${e.vertical ? ` side side-${e.side}` : ""}" style="left:${r1(e.mx)}px;top:${r1(e.my)}px"><div id="${sid}-edge-${e.i}-label" class="edge-label">${esc(e.label)}</div></div>`
              : ""
          }`,
    )
    .join("");

  const verdicts = [
    sc.wrong
      ? `<div id="${sid}-wrong" class="verdict verdict-wrong"><span class="verdict-tag">${esc(sc.wrong_tag || "✕ ありがちな誤答")}</span><p><span id="${sid}-strike" class="strike-wrap">${esc(sc.wrong)}</span></p></div>`
      : "",
    sc.rule ? `<div id="${sid}-rule" class="verdict verdict-rule"><span class="verdict-tag">${esc(sc.rule_tag || "✓ 正解ルール")}</span><p>${esc(sc.rule)}</p></div>` : "",
  ].join("");

  return {
    html: `
      <section id="scene-${sid}" class="scene clip accent-${accent}${si === 0 ? " scene-first" : ""}" data-scene-id="${esc(sc.id)}" data-start="${timing.start}" data-duration="${timing.duration}" data-track-index="${si + 1}">
        <div class="text-block">
          <div class="kicker-row">
            <span id="${sid}-kicker" class="kicker">${esc(sc.kicker || "")}</span>
            <span class="step">${String(si + 1).padStart(2, "0")}<small> / ${String(ep.scenes.length).padStart(2, "0")}</small></span>
          </div>
          <h1 id="${sid}-title" class="title" style="font-size:${titleSize(sc.title)}px">${esc(sc.title)}</h1>
          ${sc.body ? `<p id="${sid}-body" class="body">${bodyLines}</p>` : ""}
        </div>
        <div id="${sid}-stage" class="stage nodes-${sc.nodes.length}">${edgesHtml}${nodesHtml}
        </div>
        <div id="${sid}-verdicts" class="verdicts${sc.wrong && sc.rule ? "" : " single"}">${verdicts}</div>
        <div id="${sid}-caption" class="caption" style="font-size:${chunks ? 46 : captionSize(sc.caption)}px">${captionHtml}</div>
        ${sc.source_url ? `<div id="${sid}-source" class="source">出典: ${esc(shortUrl(sc.source_url))}</div>` : ""}
      </section>`,
    timing: {
      sid,
      start: timing.start,
      duration: timing.duration,
      hasWrong: Boolean(sc.wrong),
      hasRule: Boolean(sc.rule),
      nodeCount: sc.nodes.length,
      edges: edges.map((e) => ({ i: e.i, len: Math.round(e.len), to: e.to, hasLabel: Boolean(e.label) })),
      captionChunks: chunks?.map((c, i) => ({ i, start: Number(c.start) || 0, end: Number(c.end) || 0 })) || [],
    },
  };
}

export function composeEpisode(ep, buildDir, { fps = 30 } = {}) {
  mkdirSync(join(buildDir, "audio"), { recursive: true });
  const timings = sceneTimings(ep);
  const total = Math.round(ep.scenes.reduce((a, s) => a + s.duration, 0) * 1000) / 1000;
  const compId = `sap-${ep.id}`.toLowerCase().replace(/[^a-z0-9-]/g, "-");
  const scenes = ep.scenes.map((sc, si) => sceneHtml(ep, sc, si, timings[si]));
  const qChips = (ep.question_numbers || []).map((n) => `<span class="qchip">Q${n}</span>`).join("");
  const dots = ep.scenes.map((_, si) => `<i id="dot-${si + 1}" class="dot"></i>`).join("");
  const timelineData = { compId, total, fps, scenes: scenes.map((s) => s.timing) };

  const html = `<!doctype html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=${W}, initial-scale=1.0" />
    <title>${esc(ep.title)}</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <!-- Generated by production/render.mjs from content/episodes.json (episode "${esc(ep.id)}"). Edit template/ for global changes. -->
    <div id="root" data-composition-id="${compId}" data-start="0" data-width="${W}" data-height="${H}" data-duration="${total}" data-fps="${fps}">
      <audio id="voiceover" data-start="0" data-duration="${total}" data-track-index="40" data-volume="1" src="audio/episode.wav"></audio>

      <div id="progress" class="progress"><i id="progress-fill"></i></div>
      <header id="header" class="header">
        <div class="brand"><b>${esc(ep.exam_label || "AWS SAP-C02")}</b><span>${esc(ep.series_label || "ミス復習")}</span></div>
        <div class="qchips">${qChips}</div>
      </header>
      <div id="episode-title" class="episode-title">
        <span>${esc(ep.title)}</span><span class="dots">${dots}</span>
      </div>
${scenes.map((s) => s.html).join("\n")}
      <div id="voice-credit" class="voice-credit">音声：VOICEVOX ずんだもん</div>
    </div>

    <script src="gsap.min.js"></script>
    <script src="motion.js"></script>
    <script>
      const timing = ${JSON.stringify(timelineData)};
      const timeline = gsap.timeline({ paused: true });
      window.buildEpisodeTimeline(timeline, timing);
      window.__timelines = window.__timelines || {};
      window.__timelines["${compId}"] = timeline;
    </script>
  </body>
</html>
`;
  writeFileSync(join(buildDir, "index.html"), html);
  copyFileSync(join(TEMPLATE_DIR, "styles.css"), join(buildDir, "styles.css"));
  copyFileSync(join(TEMPLATE_DIR, "motion.js"), join(buildDir, "motion.js"));
  copyFileSync(require.resolve("gsap/dist/gsap.min.js"), join(buildDir, "gsap.min.js"));
  return { compId, total, timings };
}
