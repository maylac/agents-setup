// Locates ffmpeg / ffprobe / Chrome without touching global config.
// Order: explicit env var -> project-local npm binary -> PATH.
import { existsSync, readdirSync } from "node:fs";
import { createRequire } from "node:module";
import { homedir } from "node:os";
import { delimiter, join } from "node:path";
import { spawn } from "node:child_process";

const require = createRequire(import.meta.url);

function onPath(name) {
  for (const dir of (process.env.PATH || "").split(delimiter)) {
    const candidate = join(dir, name);
    if (dir && existsSync(candidate)) return candidate;
  }
  return null;
}

function tryRequire(fn) {
  try {
    const p = fn();
    return p && existsSync(p) ? p : null;
  } catch {
    return null;
  }
}

export function findFfmpeg() {
  return (
    (process.env.FFMPEG_PATH && existsSync(process.env.FFMPEG_PATH) && process.env.FFMPEG_PATH) ||
    tryRequire(() => require("ffmpeg-static")) ||
    onPath("ffmpeg")
  );
}

export function findFfprobe() {
  return (
    (process.env.FFPROBE_PATH && existsSync(process.env.FFPROBE_PATH) && process.env.FFPROBE_PATH) ||
    tryRequire(() => require("@ffprobe-installer/ffprobe").path) ||
    onPath("ffprobe")
  );
}

// Reuse an already-downloaded headless Chrome so renders work offline.
export function findBrowser() {
  if (process.env.HYPERFRAMES_BROWSER_PATH) return process.env.HYPERFRAMES_BROWSER_PATH;
  const roots = [
    [join(homedir(), ".cache/puppeteer/chrome-headless-shell"), "chrome-headless-shell-mac-arm64/chrome-headless-shell"],
    [join(homedir(), ".cache/puppeteer/chrome-headless-shell"), "chrome-headless-shell-mac-x64/chrome-headless-shell"],
    [join(homedir(), ".cache/puppeteer/chrome-headless-shell"), "chrome-headless-shell-linux64/chrome-headless-shell"],
  ];
  for (const [root, rel] of roots) {
    if (!existsSync(root)) continue;
    const versions = readdirSync(root).sort().reverse();
    for (const v of versions) {
      const p = join(root, v, rel);
      if (existsSync(p)) return p;
    }
  }
  return null; // let HyperFrames resolve/download its own browser
}

export function hyperframesBin() {
  return join(import.meta.dirname, "..", "node_modules", "hyperframes", "bin", "hyperframes.mjs");
}

export function toolEnv() {
  const env = {
    ...process.env,
    HYPERFRAMES_NO_TELEMETRY: "1",
    DO_NOT_TRACK: "1",
    HYPERFRAMES_NO_UPDATE_CHECK: "1",
    HYPERFRAMES_NO_AUTO_INSTALL: "1",
  };
  const ffmpeg = findFfmpeg();
  const ffprobe = findFfprobe();
  const browser = findBrowser();
  if (ffmpeg) env.HYPERFRAMES_FFMPEG_PATH = ffmpeg;
  if (ffprobe) env.HYPERFRAMES_FFPROBE_PATH = ffprobe;
  if (browser) env.HYPERFRAMES_BROWSER_PATH = browser;
  return env;
}

export function run(cmd, args, { capture = false, quiet = false, cwd } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd,
      env: toolEnv(),
      stdio: capture ? ["ignore", "pipe", "pipe"] : ["ignore", quiet ? "ignore" : "inherit", "inherit"],
    });
    let out = "";
    let err = "";
    if (capture) {
      child.stdout.on("data", (d) => (out += d));
      child.stderr.on("data", (d) => (err += d));
    }
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve({ out, err });
      else reject(new Error(`${cmd.split("/").pop()} ${args.slice(0, 3).join(" ")} … exited ${code}\n${(err + out).slice(-4000)}`));
    });
  });
}

export async function probe(file) {
  const ffprobe = findFfprobe();
  if (!ffprobe) throw new Error("ffprobe not found (run npm install in production/)");
  const { out } = await run(
    ffprobe,
    ["-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,sample_rate,channels,duration", "-of", "json", file],
    { capture: true },
  );
  return JSON.parse(out);
}
