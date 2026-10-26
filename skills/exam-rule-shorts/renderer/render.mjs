#!/usr/bin/env node
// SAP-C02 mistake-review renderer: episodes.json -> HyperFrames compositions -> MP4.
//
//   node render.mjs validate --all
//   node render.mjs lint     --all                 (validate + build + hyperframes lint)
//   node render.mjs build    --episode ep01        (compositions only, for preview/editing)
//   node render.mjs preview  --episode ep01        (HyperFrames studio preview)
//   node render.mjs render   --episode ep01 --episode ep02 [--concat review-pack]
//   node render.mjs render   --all
//   node render.mjs concat   --episode ep01 --episode ep02 --name review-pack
//   node render.mjs probe    ../videos/ep01.mp4
import { existsSync, mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { parseArgs } from "node:util";
import { buildEpisodeAudio } from "./lib/audio.mjs";
import { composeEpisode } from "./lib/compose.mjs";
import { findBrowser, findFfmpeg, findFfprobe, hyperframesBin, probe, run } from "./lib/tools.mjs";
import { validateEpisodes } from "./lib/validate.mjs";

const HERE = import.meta.dirname;
const COMMANDS = ["validate", "lint", "build", "preview", "render", "concat", "probe", "doctor"];

const { values: opt, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    input: { type: "string", short: "i", default: resolve(HERE, "../content/episodes.json") },
    out: { type: "string", short: "o", default: resolve(HERE, "../videos") },
    episode: { type: "string", short: "e", multiple: true },
    all: { type: "boolean", default: false },
    fps: { type: "string", default: "30" },
    quality: { type: "string", default: "standard" },
    workers: { type: "string" },
    concat: { type: "string" },
    name: { type: "string" },
    "skip-audio-check": { type: "boolean", default: false },
    "keep-going": { type: "boolean", default: false },
    verbose: { type: "boolean", short: "v", default: false },
    port: { type: "string", default: "3010" },
    help: { type: "boolean", short: "h", default: false },
  },
});

const command = COMMANDS.includes(positionals[0]) ? positionals.shift() : "render";
const BUILD_ROOT = join(HERE, "build");
const log = (...a) => console.log("[sap-render]", ...a);

if (opt.help) {
  console.log(readFileSync(new URL(import.meta.url), "utf8").split("\n").slice(1, 12).join("\n").replace(/^\/\/ ?/gm, ""));
  process.exit(0);
}

function loadEpisodes() {
  const input = resolve(opt.input);
  if (!existsSync(input)) throw new Error(`input not found: ${input} (use --input)`);
  const timed = JSON.parse(readFileSync(input, "utf8"));
  if (basename(input) !== "episodes-timed.json") return timed;
  const contentPath = resolve(HERE, "../content/episodes.json");
  if (!existsSync(contentPath)) throw new Error(`visual source not found: ${contentPath}`);
  const current = JSON.parse(readFileSync(contentPath, "utf8"));
  const byEpisode = new Map(timed.map((ep) => [ep.id, ep]));
  if (current.length !== timed.length || current.some((ep) => !byEpisode.has(ep.id)))
    throw new Error("timed/content episode IDs differ; refusing to render stale diagrams");
  return current.map((ep) => {
    const audioEp = byEpisode.get(ep.id);
    const byScene = new Map((audioEp.scenes || []).map((sc) => [sc.id, sc]));
    if (ep.scenes.length !== byScene.size || ep.scenes.some((sc) => !byScene.has(sc.id)))
      throw new Error(`${ep.id}: timed/content scene IDs differ`);
    return { ...ep, scenes: ep.scenes.map((sc) => {
      const audioSc = byScene.get(sc.id);
      const fields = ["audio_path", "duration", "duration_seconds", "caption_chunks", "caption_timing_basis"];
      return { ...sc, ...Object.fromEntries(fields.filter((key) => audioSc[key] !== undefined).map((key) => [key, audioSc[key]])) };
    }) };
  });
}

function selectEpisodes(episodes) {
  if (opt.all) return episodes;
  if (!opt.episode?.length) throw new Error("choose episodes with --episode ID (repeatable, or comma list) or --all");
  const ids = opt.episode.flatMap((s) => s.split(",")).map((s) => s.trim()).filter(Boolean);
  return ids.map((id) => {
    const ep = episodes.find((e) => e.id === id);
    if (!ep) throw new Error(`episode "${id}" not in ${opt.input}`);
    return ep;
  });
}

async function validateSelected(selected) {
  const { errors, warnings } = await validateEpisodes(selected, { checkAudio: !opt["skip-audio-check"] });
  for (const w of warnings) console.warn(`  warn  ${w}`);
  for (const e of errors) console.error(`  ERROR ${e}`);
  log(`validated ${selected.length} episode(s): ${errors.length} error(s), ${warnings.length} warning(s)`);
  if (errors.length) throw new Error("validation failed");
}

function fps() {
  const f = Number(opt.fps);
  if (![24, 30].includes(f)) throw new Error("--fps must be 24 or 30");
  return f;
}

async function buildEpisode(ep, { withAudio = true } = {}) {
  const dir = join(BUILD_ROOT, ep.id);
  rmSync(dir, { recursive: true, force: true });
  const meta = composeEpisode(ep, dir, { fps: fps() });
  if (withAudio) await buildEpisodeAudio(ep, join(dir, "audio", "episode.wav"));
  return { dir, ...meta };
}

async function hfLint(dir) {
  const { out, err } = await run(process.execPath, [hyperframesBin(), "lint", dir], { capture: true }).catch((e) => {
    console.error(e.message);
    throw new Error(`hyperframes lint failed for ${dir}`);
  });
  // Known benign warning: scenes are timed clips with nested markup (by design, for Studio editing).
  const lines = (out + err).split("\n").filter((l) => l.trim());
  const shown = opt.verbose ? lines : lines.filter((l) => /✗|◇|error/i.test(l) || (/⚠/.test(l) && !/nested_structure_needs_subcomposition/.test(l)));
  if (shown.length) console.log(shown.map((l) => `  ${l.trim()}`).join("\n"));
}

async function verifyMp4(file, expectedDuration) {
  const info = await probe(file);
  const v = info.streams.find((s) => s.codec_type === "video");
  const a = info.streams.find((s) => s.codec_type === "audio");
  const dur = Number(info.format.duration);
  const problems = [];
  if (!v) problems.push("no video stream");
  else {
    if (v.codec_name !== "h264") problems.push(`video codec ${v.codec_name}`);
    if (v.width !== 1080 || v.height !== 1920) problems.push(`size ${v.width}x${v.height}`);
    if (v.pix_fmt !== "yuv420p") problems.push(`pix_fmt ${v.pix_fmt}`);
  }
  if (!a) problems.push("no audio stream");
  else if (a.codec_name !== "aac") problems.push(`audio codec ${a.codec_name}`);
  if (expectedDuration && Math.abs(dur - expectedDuration) > 0.1) problems.push(`duration ${dur.toFixed(3)}s != ${expectedDuration}s`);
  const summary = `${basename(file)}: ${v?.codec_name} ${v?.width}x${v?.height} ${v?.pix_fmt} ${v?.r_frame_rate}fps + ${a?.codec_name} ${a?.sample_rate}Hz ${a?.channels}ch, ${dur.toFixed(3)}s`;
  return { ok: problems.length === 0, problems, summary };
}

async function renderEpisode(ep, outDir) {
  const t0 = Date.now();
  const { dir, total } = await buildEpisode(ep);
  await hfLint(dir);
  const silent = join(dir, "render-video.mp4");
  const args = [hyperframesBin(), "render", dir, "--output", silent, "--fps", String(fps()), "--quality", opt.quality, "--quiet"];
  if (opt.workers) args.push("--workers", opt.workers);
  log(`rendering ${ep.id} (${total}s) …`);
  await run(process.execPath, args, { capture: !opt.verbose });

  // Final mux: exact episode WAV -> AAC; guarantee H.264 yuv420p + faststart.
  const vinfo = await probe(silent);
  const v = vinfo.streams.find((s) => s.codec_type === "video");
  const copyVideo = v?.codec_name === "h264" && v?.pix_fmt === "yuv420p" && v?.width === 1080 && v?.height === 1920;
  mkdirSync(outDir, { recursive: true });
  const outFile = join(outDir, `${ep.id}.mp4`);
  const tmp = `${outFile}.part.mp4`;
  const videoArgs = copyVideo
    ? ["-c:v", "copy"]
    : ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-vf", "scale=1080:1920", "-r", String(fps())];
  await run(findFfmpeg(), [
    "-y", "-v", "error",
    "-i", silent, "-i", join(dir, "audio", "episode.wav"),
    "-map", "0:v:0", "-map", "1:a:0",
    ...videoArgs,
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
    "-t", String(total),
    "-movflags", "+faststart",
    tmp,
  ]);
  renameSync(tmp, outFile);
  const check = await verifyMp4(outFile, total);
  log(`${check.ok ? "OK " : "BAD"} ${check.summary} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
  if (!check.ok) throw new Error(`${outFile}: ${check.problems.join(", ")}`);
  return outFile;
}

async function concatFiles(files, outFile) {
  if (files.length < 1) throw new Error("nothing to concatenate");
  for (const f of files) if (!existsSync(f)) throw new Error(`missing episode video: ${f} (render it first)`);
  const list = join(BUILD_ROOT, `concat-${Date.now()}.txt`);
  mkdirSync(BUILD_ROOT, { recursive: true });
  writeFileSync(list, files.map((f) => `file '${resolve(f).replace(/'/g, "'\\''")}'`).join("\n") + "\n");
  // Same pipeline settings for every episode, so stream copy is safe and lossless.
  await run(findFfmpeg(), ["-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", list, "-c", "copy", "-movflags", "+faststart", outFile]);
  rmSync(list, { force: true });
  let expected = 0;
  for (const f of files) expected += Number((await probe(f)).format.duration);
  const check = await verifyMp4(outFile);
  log(`${check.ok ? "OK " : "BAD"} concat ${check.summary} (sum of parts ${expected.toFixed(3)}s)`);
  if (!check.ok) throw new Error(`${outFile}: ${check.problems.join(", ")}`);
  return outFile;
}

async function main() {
  const outDir = resolve(opt.out);
  switch (command) {
    case "doctor": {
      log("ffmpeg ", findFfmpeg() || "MISSING");
      log("ffprobe", findFfprobe() || "MISSING");
      log("browser", findBrowser() || "(HyperFrames default)");
      log("hyperframes", existsSync(hyperframesBin()) ? hyperframesBin() : "MISSING");
      return;
    }
    case "probe": {
      let bad = 0;
      for (const f of positionals) {
        const c = await verifyMp4(resolve(f));
        console.log(`${c.ok ? "OK " : "BAD"} ${c.summary}${c.ok ? "" : ` -> ${c.problems.join(", ")}`}`);
        if (!c.ok) bad++;
      }
      if (bad) process.exitCode = 1;
      return;
    }
    case "concat": {
      const selected = selectEpisodes(loadEpisodes());
      const name = opt.name || opt.concat || "episodes-concat";
      await concatFiles(selected.map((ep) => join(outDir, `${ep.id}.mp4`)), join(outDir, `${name}.mp4`));
      return;
    }
  }

  const selected = selectEpisodes(loadEpisodes());
  await validateSelected(selected);
  if (command === "validate") return;

  if (command === "lint" || command === "build") {
    for (const ep of selected) {
      const { dir } = await buildEpisode(ep);
      if (command === "lint") await hfLint(dir);
      log(`${command === "lint" ? "lint ok" : "built"}: ${dir}`);
    }
    return;
  }

  if (command === "preview") {
    const ep = selected[0];
    const { dir } = await buildEpisode(ep);
    log(`preview ${ep.id} at http://localhost:${opt.port}`);
    await run(process.execPath, [hyperframesBin(), "preview", dir, "--port", opt.port]);
    return;
  }

  // render
  const done = [];
  const failed = [];
  for (const ep of selected) {
    try {
      done.push(await renderEpisode(ep, outDir));
    } catch (e) {
      failed.push(ep.id);
      console.error(`[sap-render] FAILED ${ep.id}: ${e.message}`);
      if (!opt["keep-going"]) throw e;
    }
  }
  if (opt.concat && done.length) await concatFiles(done, join(outDir, `${opt.concat}.mp4`));
  log(`rendered ${done.length}/${selected.length} -> ${outDir}`);
  if (failed.length) {
    log(`failed: ${failed.join(", ")}`);
    process.exitCode = 1;
  }
}

main().catch((e) => {
  console.error(`[sap-render] ${e.message}`);
  process.exit(1);
});
