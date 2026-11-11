# Codex 向け実装ブリーフ: スマホ運用 Phase 0（2026-11-01）

このファイルは Codex に渡すプロンプトの保存版です。本文をそのまま Codex に貼ります。

---

agents-setup で、スマホ運用の設計 2 本の「Phase 0（承認不要の範囲）」を実装し、PR を 3 本開いてください。merge はしません。

## 最初に読む
- `~/AGENTS.md`（Hard Stops、Single command path、Core Principles）
- `~/workspace/maylac/agents-setup/AGENTS.md`
- branch `docs/phone-agents-harness-design` の `docs/plans/2026-11-01-phone-agents-harness-design.md`（役割設計）と `docs/plans/2026-11-01-approval-boundary-design.md`（権限境界）。`git fetch origin docs/phone-agents-harness-design` して `git show origin/docs/phone-agents-harness-design:<path>` で読めます。
- `slack-bridge/bridge.py`、`harness.py`、`mission_hub.py`、`doctor.py`、`test_bridge.py`、`test_mission_hub.py`、`test_doctor.py`（既存テストは fake executable 方式。同じ方式で足す）

## 作業の前提
- 作業は `~/workspace/maylac/agents-setup` の worktree で行い、各 PR は `origin/main` から分岐した別 branch にする。canonical checkout の既存の未コミット差分（`skills/exam-trap-choices/`、`skills/unslop/`、`docs/plans/2026-11-01-*.md`）には触れない。
- 設定ファイル（`~/.claude/settings.json`、`~/.codex/config.toml`、`~/AGENTS.md`、`~/.config/slack-bridge/env`、`~/Library/LaunchAgents/*`）は変更しない。launchd の bootstrap / bootout、bridge と Remote Control の再起動、GitHub account や token の作成、Grok / Duet / Muse 側の設定もしない。これらは PR body の「本人の判断待ち」に列挙する。
- 秘密値（env の値、token、鍵）を出力やコミットに含めない。パスは `$HOME` 表記にする（`scripts/validate.sh` が `/Users/<user>` を検出する）。
- 同じ問題で 2 回失敗したら、その項目は blocked として報告し、残りを進める。

## PR 0: 設計ドキュメントの PR を開く
branch `docs/phone-agents-harness-design`（push 済み、8 コミット）に対して `gh pr create --base main` する。title は `docs: phone-side agents and approval-boundary design`。body は 2 文書の要約 5 行と「コードと設定は未変更」の一文。merge しない。

## PR 1: bridge（`slack-bridge/`）
設計 1 の 7.1〜7.3、4.2、7.6 を実装する。

1. **needs-approval で assignee を付ける（7.1）。** `poll_github_once` の `needs-approval` 分岐で、env `BRIDGE_APPROVAL_ASSIGNEE` があれば `gh issue edit <n> -R <repo> --add-assignee <login>` を実行する。未設定なら何もしない。
2. **`APPROVED:` コメントで再開する（7.2）。**
   - `needs-approval` にするとき、bridge のコメントに worktree の path と branch を機械可読な行（例 `worktree: <path>` と `branch: <name>`）で残す。
   - 毎 poll で `--label needs-approval --state open` の Issue も読む。bridge の `NEEDS-APPROVAL:` コメントより後の top-level コメントのうち、author login が env `BRIDGE_APPROVERS`（カンマ区切り。未設定ならこの機能は無効）に含まれ、最初の非空行が `APPROVED:` で始まるものを承認とみなす。`BRIDGE_ALLOWED_SENDERS` とは別の集合にする。
   - 再開時は `needs-approval` label を外し、本文の先頭に `Approved action: <APPROVED: 以降の本文>` を 1 行足して、記録された worktree で `run_task` 相当を実行する。新しい worktree を切らない。記録が無い、または path が存在しない場合は `blocked (worktree missing)` をコメントして close する。
   - `harness.PREAMBLE` に「`Approved action:` にある操作だけ、一度だけ実行してよい。deny された操作は回避せず、その行を報告して止まる」を足す。
3. **scope 重複の拒否（7.3）。**
   - 契約本文の `Owned files:` 行（次の `Key:` 行まで、カンマ・改行・空白区切り）を path の集合として読む。無ければ実行前に `failed (no owned files)` をコメントして close する。
   - 実行前に、(a) open の `needs-approval` Issue と (b) `$HOME/.local/state/slack-bridge/scopes.json`（Issue 番号、path、記録時刻。24 時間で失効）に記録された直近の close 済み Issue の path と照合する。同一か、片方が他方の親ディレクトリなら重複。重複なら実行せず `blocked (duplicate scope #N)` をコメントして close する。
   - 実行した契約の path は完了時に scopes.json へ記録する。
4. **原文の添付（4.2）。** ヘッダ行 `source: <GitHub comment URL> sha256:<hex>` があれば、bridge が `gh api` で原文を取得し、UTF-8 の SHA256 を照合して、本文の末尾に `Source comment:` 見出しと原文をそのまま付けて agent に渡す。不一致なら `failed (source mismatch)` をコメントして close する。agent 自身は `gh` を使えない前提。
5. **doctor の追加（7.6）。** `gh auth status` の成否、`gh api user --jq .login` の login 名（token は出さない）、`launchctl print gui/<uid>/local.claude.remote-control-*` の state、`$HOME/.claude/remote-control/stdout.log` の size、scopes.json に 24 時間超の記録が残っていないか。既存の「値を表示しない」方針を守る。

テスト: 上の 1〜5 それぞれに fake executable のテストを足す（承認コメントの検知、worktree 不在、重複 scope、Owned files 欠落、SHA 不一致、assignee 未設定時の無動作）。既存テストは全件 pass のまま。README（`slack-bridge/README.md`）に新しい env（`BRIDGE_APPROVAL_ASSIGNEE`、`BRIDGE_APPROVERS`、`GH_TOKEN` を bot identity で置く運用）を追記する。

## PR 2: publisher と launchd テンプレ（設計 1 の 7.4）
1. `slack-bridge/publish_hub.py`: `mission_hub.py --format json` の出力（`--input-json` で固定 fixture も読める）と、`gh issue list --state open --label needs-approval` の全件から、承認待ち・異常・実行中の件数と一覧、生成時刻（JST）を組み立てる。`docs/grok-bot/ops-hub-header.md` を前置して `gh issue edit 6 -R maylac/agent-tasks --body-file` で更新する。`--now` で時刻を固定でき、07:30〜07:59 JST の回だけ件数と承認待ち一覧を `gh issue comment 6 --body-file` でも投稿する。`--dry-run` で書き込みせず本文を標準出力に出す。
2. `docs/grok-bot/ops-hub-header.md`: issue 6 の手書き部分（「本人の判断待ち」「管理範囲」）を `gh issue view 6 --json body` から写して置く。
3. `launchd/com.maylac.mission-hub-publish.plist.template`: 既存テンプレの形式で、`StartCalendarInterval` を毎時 0 分と 30 分の 2 本、stdout は `/dev/null`、stderr は `$HOME/.local/state/slack-bridge/publish.err.log`。`GH_TOKEN` は env ファイルから読む構成にする。install はしない。
4. `test_publish_hub.py`: fixture で件数・一覧・時刻窓・dry-run を確認する。実際の `gh` は呼ばない。

## PR 3: ドキュメント、skill、設定テンプレ
1. `docs/grok-bot/dispatcher-instructions.md` と `bot-roles.md` を設計 1 の 4.1・4.2・5.5・7.2 に合わせて改訂する: 追加 3 Bot の計画を取り下げる、引き継ぎは URL と SHA256 のみで本文は bridge が添付する、Bot は `APPROVED:` を書かない、承認は本人が GitHub Mobile から書く、運用ハブの routine は issue 6 の本文を書かず読んで報告するだけにする。
2. `skills/phone-dispatcher/SKILL.md` を `dispatcher-instructions.md` から生成する（frontmatter の name と description、本文は同じ内容）。両者がずれていないことを確認するテストか `scripts/validate.sh` のチェックを 1 つ足す。
3. 設計 2 の 4.1 と 4.4 を `templates/claude-settings.permissions.json` と `templates/codex-config.workspace-write.toml` として置き、`docs/restore.md` に「適用は本人の了解の後、適用コマンドはこれ」を書く。live の設定には適用しない。
4. `home/AGENTS.md`（repo snapshot）に設計 2 の 3-7「常設許可」の節と、Core Principles の「ツール権限は設定で解決し、会話で聞かない」の一文を足す。live の `~/AGENTS.md` には反映しない（merge 後に `scripts/install.sh --apply-instructions --instructions-only` で反映する旨を PR body に書く）。

## 受け入れ条件（各 PR で実行し、結果を PR body に書く）
```sh
python3 -m unittest discover -s slack-bridge -p 'test_*.py'   # 既存 44 件 + 追加分がすべて pass
git diff --check
rg -n '/Users/(maylac|gotasasaki)' $(git diff --name-only origin/main)   # 0 件
scripts/validate.sh   # 既存の live parity 11 件（symlink 10 件、RTK hook 1 件）以外に新しい失敗が無いこと
python3 slack-bridge/doctor.py   # PR 1 以降: 新しい check が JSON に出て、秘密値が無いこと
python3 slack-bridge/publish_hub.py --input-json <fixture> --now 2026-11-02T07:35:00+09:00 --dry-run   # PR 2: 07:30 窓でコメント本文も出る
```

## 報告
PR ごとに: status（done / blocked / failed）、変更ファイル、各チェックコマンドと pass / fail、PR URL、notes 5 行以内。最後に「本人の判断待ち」を 1 か所にまとめる: bot account と token、`BRIDGE_APPROVAL_ASSIGNEE` / `BRIDGE_APPROVERS` の値、bridge の再起動、publisher の bootstrap、`agents-setup` host の plist 変更、設定テンプレの適用、`home/AGENTS.md` の live 反映、Grok routine の読み取り専用化。
