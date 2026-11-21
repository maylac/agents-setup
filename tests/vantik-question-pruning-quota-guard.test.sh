#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE="$(command -v node)"
"$NODE" -e "require('node:sqlite')" 2>/dev/null || {
  printf 'SKIP: Node.js with node:sqlite is required\n' >&2
  exit 77
}

TEST_TMP="$(mktemp -d)"
DB="$TEST_TMP/quota-fixture.sqlite"
SHIM="$TEST_TMP/better-sqlite3-shim.mjs"
cleanup() {
  rm -f -- "$DB" "$DB-journal" "$DB-wal" "$DB-shm" "$SHIM"
  rmdir "$TEST_TMP"
}
trap cleanup EXIT

cat > "$SHIM" <<'SHIM'
import Module from 'node:module';
import { DatabaseSync } from 'node:sqlite';

class BetterSqliteCompat {
  constructor(path, options = {}) {
    this.db = new DatabaseSync(path, { readOnly: Boolean(options.readonly) });
  }
  prepare(sql) {
    const stmt = this.db.prepare(sql);
    const query = {
      all: (...args) => stmt.all(...args),
      get: (...args) => stmt.get(...args),
      run: (...args) => stmt.run(...args),
      raw() { stmt.setReturnArrays(true); return this; },
    };
    return query;
  }
  pragma() {}
  transaction(fn) {
    return (...args) => {
      this.db.exec('BEGIN');
      try {
        const result = fn(...args);
        this.db.exec('COMMIT');
        return result;
      } catch (error) {
        this.db.exec('ROLLBACK');
        throw error;
      }
    };
  }
}

const load = Module._load;
Module._load = function (request, parent, isMain) {
  return request === 'better-sqlite3' ? BetterSqliteCompat : load.call(this, request, parent, isMain);
};
SHIM

"$NODE" --input-type=module - "$DB" <<'FIXTURE'
import { DatabaseSync } from 'node:sqlite';
const db = new DatabaseSync(process.argv[2]);
db.exec(`
  create table exams(id integer primary key, code text);
  create table domains(id integer primary key, name text);
  create table questions(id integer primary key, source_question_id text, current_version_id integer, exam_id integer, active integer, note text);
  create table question_versions(id integer primary key, question_id integer, prompt text, domain_id integer, source_classification text);
  create table choices(id integer primary key, question_version_id integer, label text, body text);
  create table correct_answers(question_version_id integer, choice_id integer);
  create table explanations(question_version_id integer, source text, body text);
  create table attempts(question_version_id integer, is_correct integer);
  insert into exams values(1, 'quota-fixture');
  insert into domains values(1, 'Domain');
`);
for (let id = 1; id <= 4; id++) {
  db.prepare('insert into questions values(?, ?, ?, 1, 1, null)').run(id, `Q${id}`, id);
  db.prepare('insert into question_versions values(?, ?, ?, 1, ?)').run(id, id, `Synthetic question ${id}`, 'past_exam');
  db.prepare('insert into choices values(?, ?, ?, ?)').run(id * 2 - 1, id, 'A', 'yes');
  db.prepare('insert into choices values(?, ?, ?, ?)').run(id * 2, id, 'B', 'no');
  db.prepare('insert into correct_answers values(?, ?)').run(id, id * 2 - 1);
  if (id === 1) db.prepare('insert into attempts values(?, 0)').run(id);
}
db.close();
FIXTURE

CLI=("$NODE" --import "$SHIM" "$ROOT/skills/vantik-question-pruning/scripts/prune.mjs" --db "$DB" --exam quota-fixture --source all)

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
state() {
  "$NODE" --input-type=module - "$DB" <<'STATE'
import { DatabaseSync } from 'node:sqlite';
const db = new DatabaseSync(process.argv[2], { readOnly: true });
const stmt = db.prepare('select q.id, q.active, count(a.question_version_id) as missed from questions q left join attempts a on a.question_version_id=q.current_version_id and a.is_correct=0 group by q.id order by q.id');
stmt.setReturnArrays(true);
console.log(JSON.stringify(stmt.all()));
db.close();
STATE
}

set +e
zero_output="$("${CLI[@]}" --target 1 --weights Domain:0 --apply 2>&1)"
zero_status=$?
set -e
[ "$zero_status" -ne 0 ] || fail 'all-zero quota weights unexpectedly applied successfully'
[[ "$zero_output" == *'weights total must be finite and greater than zero'* ]] || fail "all-zero failure was not the quota guard: $zero_output"
zero_state="$(state)"
[ "$zero_state" = '[[1,1,1],[2,1,0],[3,1,0],[4,1,0]]' ] || fail "all-zero apply changed fixture state: $zero_state"

positive_output="$("${CLI[@]}" --target 2 --weights Domain:1 --apply 2>&1)" || fail "positive control failed: $positive_output"
positive_state="$(state)"
[ "$positive_state" = '[[1,1,1],[2,0,0],[3,0,0],[4,1,0]]' ] || fail "positive control did not retain missed and only quota-kept unmissed questions: $positive_state"
printf 'quota guard regression passed (all-zero rejected without mutation; valid quota retained missed Q1 and Q4 only).\n'
