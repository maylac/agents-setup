// Joins per-scene WAVs into one episode track. Each scene is padded with
// silence (or trimmed) to exactly its `duration`, so audio scene boundaries
// match the visual scene starts sample-for-sample.
import { findFfmpeg, run } from "./tools.mjs";

export const SAMPLE_RATE = 48000;

export async function buildEpisodeAudio(ep, outWav) {
  const ffmpeg = findFfmpeg();
  if (!ffmpeg) throw new Error("ffmpeg not found (run npm install in production/)");
  const args = ["-y", "-v", "error"];
  for (const sc of ep.scenes) args.push("-i", sc.audio_path);
  const chains = ep.scenes.map((sc, i) => {
    const samples = Math.round(sc.duration * SAMPLE_RATE);
    return `[${i}:a]aresample=${SAMPLE_RATE},aformat=sample_fmts=s16:channel_layouts=stereo,apad=whole_len=${samples},atrim=end_sample=${samples},asetpts=N/SR/TB[a${i}]`;
  });
  const inputs = ep.scenes.map((_, i) => `[a${i}]`).join("");
  const filter = `${chains.join(";")};${inputs}concat=n=${ep.scenes.length}:v=0:a=1[out]`;
  args.push("-filter_complex", filter, "-map", "[out]", "-c:a", "pcm_s16le", outWav);
  await run(ffmpeg, args);
  return outWav;
}
