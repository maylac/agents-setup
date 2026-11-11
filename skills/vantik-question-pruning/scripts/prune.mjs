// Deactivate stale, unreliable, or duplicate questions for one Vantik exam.
//
// Runs inside the vantik container (stdin-piped), dry-run unless --apply:
//
//   ssh ugnas 'docker exec -i -w /app vantik node --input-type=module - --exam aws-clf-c02 --unreliable --dedupe' < prune.mjs
//
// Questions are never deleted: they get active=0 plus a dated note naming the
// reason, so the admin UI can restore them. Previously missed questions are kept.
// Port of the former prune.py: same arguments, SQL and output. better-sqlite3 is
// resolved from the current directory's package.json (cwd must be /app).
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parseArgs } from "node:util";

const Database = createRequire(join(process.cwd(), "package.json"))("better-sqlite3");

const VOTE_RE = /(?:コミュニティ投票|Community votes): ([^\n]+)/u;

const fail = (message) => {
  process.stderr.write(`${message}\n`);
  process.exit(1);
};

const parseVotes = (text) => {
  const m = VOTE_RE.exec(text);
  return m ? [...m[1].matchAll(/([A-F]+) (\d+)/gu)].map((x) => [x[1], Number.parseInt(x[2], 10)]) : [];
};

// Python repr() of a str, so the printed dicts and lists match the old output.
const pyStr = (s) => {
  const quote = s.includes("'") && !s.includes('"') ? '"' : "'";
  let out = "";
  for (const ch of s) {
    if (ch === "\\") out += "\\\\";
    else if (ch === quote) out += `\\${ch}`;
    else if (ch === "\n") out += "\\n";
    else if (ch === "\r") out += "\\r";
    else if (ch === "\t") out += "\\t";
    else if (ch < " " || ch === "\x7f") out += `\\x${ch.codePointAt(0).toString(16).padStart(2, "0")}`;
    else out += ch;
  }
  return quote + out + quote;
};
const pyDict = (entries) => `{${[...entries].map(([k, v]) => `${pyStr(k)}: ${v}`).join(", ")}}`;
const pyList = (items) => `[${items.map(pyStr).join(", ")}]`;
const counter = (values) => {
  const counts = new Map();
  for (const v of values) counts.set(v, (counts.get(v) ?? 0) + 1);
  return counts;
};

// Python round(): half to even.
const pyRound = (x) => {
  const floor = Math.floor(x);
  const diff = x - floor;
  if (diff < 0.5) return floor;
  if (diff > 0.5) return floor + 1;
  return floor % 2 === 0 ? floor : floor + 1;
};

const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const slice80 = (s) => Array.from(s).slice(0, 80).join("");

const toInt = (name, value) => {
  if (!/^\s*[+-]?\d+\s*$/u.test(value)) fail(`prune.mjs: error: argument ${name}: invalid int value: ${pyStr(value)}`);
  return Number.parseInt(value, 10);
};
const toFloat = (name, value) => {
  const n = Number(value);
  if (value.trim() === "" || Number.isNaN(n)) fail(`prune.mjs: error: argument ${name}: invalid float value: ${pyStr(value)}`);
  return n;
};

const parseCli = () => {
  let parsed;
  try {
    parsed = parseArgs({
      args: process.argv.slice(2),
      strict: true,
      options: {
        db: { type: "string", default: "/app/data/vantik.db" },
        exam: { type: "string" },
        source: { type: "string", default: "past_exam" },
        unreliable: { type: "boolean", default: false },
        "min-share": { type: "string", default: "0.6" },
        "stale-terms": { type: "string" },
        dedupe: { type: "boolean", default: false },
        "max-low-vote": { type: "string", default: "0" },
        target: { type: "string", default: "0" },
        weights: { type: "string", default: "" },
        apply: { type: "boolean", default: false },
        list: { type: "boolean", default: false },
      },
    }).values;
  } catch (err) {
    fail(`prune.mjs: error: ${err.message}`);
  }
  if (parsed.exam === undefined) fail("prune.mjs: error: the following arguments are required: --exam");
  if (!["past_exam", "original", "all"].includes(parsed.source)) {
    fail(`prune.mjs: error: argument --source: invalid choice: ${pyStr(parsed.source)} (choose from 'past_exam', 'original', 'all')`);
  }
  return {
    db: parsed.db,
    exam: parsed.exam,
    source: parsed.source,
    unreliable: parsed.unreliable,
    minShare: toFloat("--min-share", parsed["min-share"]),
    staleTerms: parsed["stale-terms"],
    dedupe: parsed.dedupe,
    maxLowVote: toInt("--max-low-vote", parsed["max-low-vote"]),
    target: toInt("--target", parsed.target),
    weights: parsed.weights,
    apply: parsed.apply,
    list: parsed.list,
  };
};

// Python's re accepts a leading (?i); JavaScript takes it as a flag.
const compile = (pattern) => (pattern.startsWith("(?i)") ? new RegExp(pattern.slice(4), "i") : new RegExp(pattern));

const main = () => {
  const args = parseCli();

  const conn = new Database(args.db, { readonly: !args.apply, fileMustExist: true });
  conn.pragma("busy_timeout = 10000");
  const exam = conn.prepare("select id from exams where code=?").get(args.exam);
  if (exam === undefined) fail(`unknown exam ${args.exam}`);
  const srcSql = args.source === "all" ? "" : "and qv.source_classification = ?";
  const params = args.source === "all" ? [exam.id] : [exam.id, args.source];
  const rows = conn
    .prepare(
      `
        select q.id, q.source_question_id, qv.id, qv.prompt, q.note, coalesce(d.name, '')
        from questions q join question_versions qv on qv.id = q.current_version_id
        left join domains d on d.id = qv.domain_id
        where q.exam_id = ? and q.active = 1 ${srcSql}`,
    )
    .raw()
    .all(...params);

  let stale = {};
  if (args.staleTerms) stale = JSON.parse(readFileSync(args.staleTerms, "utf8"));

  const choicesStmt = conn.prepare("select label, body from choices where question_version_id=?").raw();
  const correctStmt = conn
    .prepare("select c.label from correct_answers a join choices c on c.id=a.choice_id where a.question_version_id=?")
    .raw();
  const explStmt = conn.prepare("select source, body from explanations where question_version_id=?").raw();
  const wrongStmt = conn
    .prepare(
      `select count(*) from attempts a join question_versions v on v.id=a.question_version_id
                                where v.question_id=? and a.is_correct=0`,
    )
    .raw();

  const items = [];
  for (const [qid, sqid, vid, prompt, note, domain] of rows) {
    const choices = choicesStmt.all(vid);
    const correct = correctStmt.all(vid).map((r) => r[0]).sort();
    const answer = choices
      .filter(([label]) => correct.includes(label))
      .map(([, body]) => body.trim())
      .sort()
      .join(" / ");
    const expl = explStmt.all(vid);
    const votes = parseVotes(expl.map(([, body]) => body).join(" "));
    const wrong = wrongStmt.get(qid)[0];
    items.push({
      id: qid,
      sq: sqid,
      note,
      domain,
      answer,
      labels: correct.join(""),
      prompt,
      hasAi: expl.some(([source]) => source === "ai_generated"),
      votes,
      total: votes.reduce((sum, [, n]) => sum + n, 0),
      wrong,
    });
  }

  const drop = new Map();
  for (const it of items) {
    const reasons = [];
    if (args.unreliable) {
      if (!it.hasAi) reasons.push("解説不十分: 選択肢別のAI解説なし");
      if (it.votes.length > 0) {
        const top = it.votes.reduce((best, v) => (v[1] > best[1] ? v : best));
        if (top[0] !== it.labels) reasons.push(`解説不十分: 投票最多${top[0]}≠表示回答${it.labels}`);
        else if (top[1] / it.total < args.minShare) reasons.push(`解説不十分: 投票割れ${top[1]}/${it.total}`);
      }
    }
    for (const [pattern, why] of Object.entries(stale)) {
      if (compile(pattern).test(`${it.prompt} ${it.answer}`)) reasons.push(`古い: ${why}`);
    }
    if (reasons.length > 0) drop.set(it.id, [it, reasons.join("; ")]);
  }

  if (args.dedupe) {
    const groups = new Map();
    for (const it of items) {
      if (drop.has(it.id)) continue;
      const key = it.answer.toLowerCase();
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(it);
    }
    for (const members of groups.values()) {
      members.sort((x, y) => cmp(x.wrong === 0, y.wrong === 0) || cmp(-x.total, -y.total) || cmp(x.sq, y.sq));
      const rep = members[0];
      for (const it of members.slice(1)) {
        if (it.wrong === 0) drop.set(it.id, [it, `重複: 正答「${slice80(rep.answer)}」は ${rep.sq} で代表`]);
      }
    }
    if (args.maxLowVote) {
      for (const it of items) {
        if (!drop.has(it.id) && it.wrong === 0 && it.votes.length > 0 && it.total <= args.maxLowVote) {
          drop.set(it.id, [it, `低優先: 投票${it.total}票のみ`]);
        }
      }
    }
  }

  if (args.target) {
    // Quotas follow the official weights; missed questions always stay, the rest go newest first
    // (a higher source number was added to the source later, so it is closer to the current exam).
    const weights = new Map();
    for (const pair of args.weights.split(",")) {
      if (!pair) continue;
      const cut = pair.lastIndexOf(":");
      if (cut < 0) fail(`not enough values to unpack (expected 2, got 1): ${pyStr(pair)}`);
      const value = Number(pair.slice(cut + 1));
      if (pair.slice(cut + 1).trim() === "" || Number.isNaN(value)) fail(`could not convert string to float: ${pyStr(pair.slice(cut + 1))}`);
      weights.set(pair.slice(0, cut).trim(), value);
    }
    if (weights.size === 0) fail("--target needs --weights");
    const bucket = (domain) => [...weights.keys()].find((k) => domain.includes(k)) ?? "";
    const number = (sq) => {
      const digits = (sq || "").match(/\d+/gu);
      return digits ? Number.parseInt(digits[digits.length - 1], 10) : 0;
    };
    const unmatched = [...new Set(items.filter((it) => bucket(it.domain) === "").map((it) => it.domain))].sort();
    if (unmatched.length > 0) {
      // An unmatched domain would get a zero quota and lose every question in it.
      fail(`--weights does not cover these domains: ${pyList(unmatched)}`);
    }
    const total = [...weights.values()].reduce((a, b) => a + b, 0);
    const quota = new Map([...weights].map(([k, w]) => [k, pyRound((args.target * w) / total)]));
    const pool = new Map();
    for (const it of items) {
      if (drop.has(it.id)) continue;
      const key = bucket(it.domain);
      if (!pool.has(key)) pool.set(key, []);
      pool.get(key).push(it);
    }
    for (const [key, members] of pool) {
      members.sort((x, y) => cmp(x.wrong === 0, y.wrong === 0) || cmp(-number(x.sq), -number(y.sq)));
      const limit = Math.max(quota.get(key) ?? 0, members.filter((m) => m.wrong).length);
      for (const it of members.slice(limit)) {
        drop.set(it.id, [it, `件数調整: 目標${args.target}問に向け分野内で古い番号から除外`]);
      }
    }
  }

  const kept = items.filter((it) => !drop.has(it.id));
  console.log(`${args.apply ? "APPLY" : "DRY-RUN"} exam=${args.exam} source=${args.source}`);
  console.log(`before=${items.length} drop=${drop.size} keep=${kept.length} missed_kept=${kept.filter((k) => k.wrong).length}`);
  console.log(`reasons ${pyDict(counter([...drop.values()].map(([, why]) => why.split(":")[0])))}`);
  console.log(`domain before ${pyDict(counter(items.map((i) => i.domain)))}`);
  console.log(`domain after  ${pyDict(counter(kept.map((k) => k.domain)))}`);
  if (args.list) {
    for (const [it, why] of [...drop.values()].sort((x, y) => cmp(x[0].sq ?? "", y[0].sq ?? ""))) {
      console.log(`  ${it.sq ?? "None"}\t${why}`);
    }
  }

  if (args.apply) {
    const today = new Date();
    const date = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    const tag = `[${date} 問題絞り込み]`;
    const update = conn.prepare("update questions set active=0, note=? where id=?");
    conn.transaction(() => {
      for (const [it, why] of drop.values()) {
        update.run((it.note ? `${it.note}\n` : "") + `${tag} ${why}`, it.id);
      }
    })();
    console.log("applied");
  }
};

main();
