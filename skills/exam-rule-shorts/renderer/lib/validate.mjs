// Schema + content checks for content/episodes.json.
// Errors block rendering; warnings are printed but allowed.
import { existsSync } from "node:fs";
import { isAbsolute } from "node:path";
import { probe } from "./tools.mjs";

const ID_RE = /^[A-Za-z0-9][A-Za-z0-9_-]*$/;
const STRING_FIELDS = ["id", "kicker", "title", "body", "caption", "narration", "wrong", "rule", "source_url", "audio_path"];
const REQUIRED_TEXT = ["id", "title", "caption", "audio_path"];

// Rough visual width: full-width chars count 1, ASCII counts ~0.55.
export function visualLength(s = "") {
  let n = 0;
  for (const ch of String(s)) n += ch.charCodeAt(0) > 0xff ? 1 : 0.55;
  return n;
}

export async function validateEpisodes(episodes, { checkAudio = true } = {}) {
  const errors = [];
  const warnings = [];
  const err = (p, m) => errors.push(`${p}: ${m}`);
  const warn = (p, m) => warnings.push(`${p}: ${m}`);

  if (!Array.isArray(episodes)) {
    err("root", "must be an array of episodes");
    return { errors, warnings };
  }
  if (episodes.length > 38) warn("root", `${episodes.length} episodes (brief expects up to 38)`);

  const seen = new Set();
  for (const [ei, ep] of episodes.entries()) {
    const p = `episodes[${ei}]${ep?.id ? `(${ep.id})` : ""}`;
    if (!ep || typeof ep !== "object") {
      err(p, "must be an object");
      continue;
    }
    if (typeof ep.id !== "string" || !ID_RE.test(ep.id)) err(p, "id must match [A-Za-z0-9_-] (used as file name)");
    else if (seen.has(ep.id)) err(p, `duplicate id "${ep.id}"`);
    seen.add(ep.id);
    if (typeof ep.title !== "string" || !ep.title.trim()) err(p, "title required");
    // Fresh concept shorts may map to several source questions; stable IDs are
    // carried separately, so an empty question_numbers array is valid here.
    if (ep.question_numbers !== undefined && (!Array.isArray(ep.question_numbers) || ep.question_numbers.some((n) => !Number.isInteger(n) || n <= 0)))
      err(p, "question_numbers must be an array of positive integers (or empty)");
    if (!Array.isArray(ep.scenes) || ep.scenes.length === 0) {
      err(p, "scenes must be a non-empty array");
      continue;
    }
    if (ep.scenes.length !== 4) warn(p, `${ep.scenes.length} scenes (brief expects 4)`);

    let total = 0;
    const sceneIds = new Set();
    for (const [si, sc] of ep.scenes.entries()) {
      const sp = `${p}.scenes[${si}]`;
      if (!sc || typeof sc !== "object") {
        err(sp, "must be an object");
        continue;
      }
      for (const f of STRING_FIELDS) {
        if (sc[f] !== undefined && sc[f] !== null && typeof sc[f] !== "string") err(sp, `${f} must be a string`);
      }
      for (const f of REQUIRED_TEXT) if (!sc[f] || !String(sc[f]).trim()) err(sp, `${f} required`);
      if (sc.id && !ID_RE.test(sc.id)) err(sp, "id must match [A-Za-z0-9_-]");
      else if (sc.id && sceneIds.has(sc.id)) err(sp, `duplicate scene id "${sc.id}"`);
      sceneIds.add(sc.id);

      if (typeof sc.duration !== "number" || !Number.isFinite(sc.duration) || sc.duration <= 0) err(sp, "duration must be a positive number (seconds)");
      else {
        total += sc.duration;
        if (sc.duration < 3) warn(sp, `duration ${sc.duration}s is very short; animation will be compressed`);
      }

      // Typography budget
      if (visualLength(sc.title) > 36) warn(sp, `title is long (${Math.round(visualLength(sc.title))} chars); will shrink`);
      const bodyLines = String(sc.body || "").split("\n");
      if (bodyLines.length > 2) err(sp, "body must be at most 2 lines");
      if (visualLength(sc.body) > 48) warn(sp, `body is long (${Math.round(visualLength(sc.body))} chars); may wrap past 2 lines`);
      if (visualLength(sc.caption) > 40) warn(sp, `caption is long (${Math.round(visualLength(sc.caption))} chars); keep subtitles short`);
      if (visualLength(sc.wrong) > 44) warn(sp, "wrong text is long; may wrap to 3 lines");
      if (visualLength(sc.rule) > 44) warn(sp, "rule text is long; may wrap to 3 lines");
      for (const f of ["title", "body", "caption", "wrong", "rule"]) {
        if (/(…|\.\.\.)\s*$/.test(sc[f] || "")) warn(sp, `${f} ends with "…" (truncated upstream?)`);
      }
      if (sc.source_url && !/^https?:\/\//.test(sc.source_url)) err(sp, "source_url must be http(s)");

      // Graph
      const nodes = sc.nodes;
      if (!Array.isArray(nodes) || nodes.length < 2 || nodes.length > 4) err(sp, "nodes must have 2-4 items");
      else {
        nodes.forEach((n, ni) => {
          if (!n || typeof n.label !== "string" || !n.label.trim()) err(`${sp}.nodes[${ni}]`, "label required");
          if (n?.sub !== undefined && typeof n.sub !== "string") err(`${sp}.nodes[${ni}]`, "sub must be a string");
          if (visualLength(n?.label) > 16) warn(`${sp}.nodes[${ni}]`, "label is long; will shrink");
          if (visualLength(n?.sub) > 24) warn(`${sp}.nodes[${ni}]`, "sub is long; may be clipped to 2 lines");
        });
      }
      if (!Array.isArray(sc.edges)) err(sp, "edges must be an array");
      else {
        if (sc.edges.length === 0) warn(sp, "no edges: no packet motion in this scene");
        const pairs = new Set();
        sc.edges.forEach((e, k) => {
          const ep2 = `${sp}.edges[${k}]`;
          const n = Array.isArray(nodes) ? nodes.length : 0;
          if (!Number.isInteger(e?.from) || !Number.isInteger(e?.to) || e.from < 0 || e.to < 0 || e.from >= n || e.to >= n)
            err(ep2, `from/to must be node indexes 0..${n - 1}`);
          else if (e.from === e.to) err(ep2, "self-loop not supported");
          else if (pairs.has(`${e.from}>${e.to}`)) err(ep2, "duplicate edge");
          else pairs.add(`${e.from}>${e.to}`);
          if (e?.label !== undefined && typeof e.label !== "string") err(ep2, "label must be a string");
        });
      }

      // Audio
      if (sc.audio_path) {
        if (!isAbsolute(sc.audio_path)) err(sp, "audio_path must be absolute");
        else if (!existsSync(sc.audio_path)) err(sp, `audio_path not found: ${sc.audio_path}`);
        else if (checkAudio) {
          try {
            const info = await probe(sc.audio_path);
            const a = info.streams?.find((s) => s.codec_type === "audio");
            const d = Number(info.format?.duration ?? a?.duration);
            if (!a) err(sp, "audio_path has no audio stream");
            else if (typeof sc.duration === "number") {
              sc._audioDuration = d;
              if (d > sc.duration + 0.05) err(sp, `audio is ${d.toFixed(2)}s but duration is ${sc.duration}s; narration would be cut`);
              else if (sc.duration - d > 3) warn(sp, `${(sc.duration - d).toFixed(1)}s of silence after narration`);
            }
          } catch (e) {
            err(sp, `cannot probe audio: ${e.message.split("\n")[0]}`);
          }
        }
      }
    }
    if (total && (total < 30 || total > 80)) warn(p, `total ${total.toFixed(1)}s outside 30-80s target`);
  }
  return { errors, warnings };
}
