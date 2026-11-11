# 承認ストレスを最小化する権限境界の設計（Claude Code と Codex を同じ境界に揃える）

- 日付: 2026-11-01
- 状態: 設計案。設定ファイルは未変更。
- 対象: Mac mini 上の Claude Code（Remote Control と bridge）と Codex（app / `codex exec`）。スマホから使うときに「許可しますか」を聞かれる回数と、黙って止まる回数を減らす。
- 前提: [スマホ発・Mac mini ハーネスの摩擦レス設計](2026-11-01-phone-agents-harness-design.md) の承認経路（GitHub Mobile から `APPROVED:`）を使う。

## 0. 結論

承認は三種類に分け、それぞれ別の方法で減らす。

| 種類 | 例 | 目標 | 手段 |
|---|---|---|---|
| ① ツール権限 | コマンド実行、ファイル書き込み、ネットワーク先 | **0 回** | 境界を設定ファイルに一度書き、境界の内側は無承認にする |
| ② 業務判断（Hard Stop） | merge、本番 deploy、daemon 再起動、外部送信 | 1 日数回以下、1 タップ | GitHub Mobile に集約し、保守は「保守窓」で束ねる。条件付きの常設許可を明文化する |
| ③ 規約・課金・認証 | 追加規約、プラン変更、OAuth scope | 本人のみ | 変えない |

境界は一つにする。**「workspace-write + 固定ネットワーク許可 + 秘密の読み取り禁止」** を Claude と Codex に同じ値で置く。境界の内側は聞かない。外側は「聞く」ではなく「止めて理由を報告」（非対話）か「1 タップで許可し、繰り返すものは週次でルールに昇格」（対話。1 タップの許可はそのセッション限りで設定には残らない）にする。

今日の Codex は境界なし（`sandbox_mode = "danger-full-access"`、`approval_policy = "never"`）で、ストレスは 0 だが防波堤も 0。2026-07-17 に却下された構成の再発（監査 A2）。Claude をそこへ揃える案は 6 に書くが推奨しない。推奨は Codex を共通境界へ戻すこと。

## 1. 今日のストレス源（観測）

| # | 事象 | 根拠 | 種類 |
|---|---|---|---|
| S1 | PR 作成のために `git credential fill` を使おうとして auto mode の分類器に拒否された。branch は push 済みなのに PR が作れない | 本セッション 14:05 | ① |
| S2 | sandbox 内では `gh` が keyring を読めず `gh auth status` が invalid、API 呼び出しは TLS エラー | 本セッション | ① |
| S3 | ネットワーク先をコマンドごとに `allowed_domains` で申告しないと拒否される | `sandbox.network.allowedDomains` 未設定 | ① |
| S4 | `~/tasks`、`~/.claude.json`、`~/Library/LaunchAgents` に書けない | `sandbox.filesystem.allowWrite` 未設定、`denyWrite: ~/.claude` | ① |
| S5 | `Bash(launchctl:*)` が allow に入っているので、daemon の再起動（Hard Stop）が無承認で通る | `~/.claude/settings.json` | ②の抜け |
| S6 | Remote Control の `vantik` host が workspace trust dialog で起動失敗。対話前提の承認 | `$HOME/.claude/remote-control/vantik-stderr.log` | ① |
| S7 | 以前の Dispatcher（Dots）が小さな判断ごとに承認を求めた | 監査 B5 | ② |
| S8 | Codex は `danger-full-access` + `never`。境界も承認も無い | `~/.codex/config.toml` | ①②の欠落 |

S1〜S4 は「境界が未定義なので、都度判断になっている」という同じ原因。S5 と S8 は逆に「境界が緩すぎて Hard Stop が設定で守られていない」。

## 2. 共通の権限境界（両ハーネス同じ値）

| 層 | 値 | Claude Code の設定 | Codex の設定 |
|---|---|---|---|
| 書き込み | cwd、`$TMPDIR`、`~/tasks`、`~/.local/state/slack-bridge` | `sandbox.filesystem.allowWrite` | `[sandbox_workspace_write] writable_roots` |
| 書き込み禁止 | `~/.claude`、`~/.codex`、`~/Library/LaunchAgents`、`~/.config` | `sandbox.filesystem.denyWrite` | workspace-write の既定（cwd 外は不可） |
| 読み取り禁止 | `~/.ssh`、`~/.codex/auth.json`、`~/.claude/.credentials.json`、`~/.config/slack-bridge/env`、`~/.config/gh` | `sandbox.filesystem.denyRead`（Bash 用）と `permissions.deny` の `Read(...)`（Read ツール用。`denyRead` だけでは Read ツールを止められない） | experimental の permission profile（`filesystem.<path> = "deny"`）。安定するまでは `AGENTS.md` の禁止と bridge の `harness.PREAMBLE` で補う |
| ネットワーク | 固定の許可リスト（`github.com`、`api.github.com`、`objects.githubusercontent.com`、`api.anthropic.com`、`registry.npmjs.org`、`pypi.org`、`files.pythonhosted.org`、`code.claude.com`） | `sandbox.network.allowedDomains`（acceptEdits では外は prompt、auto では分類器が認めれば通る、dontAsk では拒否） | `[sandbox_workspace_write] network_access = true`（安定版に host 単位の制限は無い。experimental の permission profile に `network.domains` があるが `sandbox_mode` と併用しない前提なので、当面は `AGENTS.md` の「未確認の外部送信は Hard Stop」で補う） |
| 境界の外へ出る出口 | `gh`（keyring が要る）、`ssh ugnas`（sandbox 内からは `allowedDomains` に入れても接続できず、`~/.ssh` の鍵も隠される）、`codex`（`auth.json` が要る） | `sandbox.excludedCommands` + allow / ask / deny rule（excluded でも rule は効くが、通ったコマンドは full access で動く） | 該当なし |
| 承認モード（対話） | 境界内は無承認、外は 1 タップ | `permissions.defaultMode: "acceptEdits"` + `autoAllowBashIfSandboxed: true` | `approval_policy = "on-request"` |
| 承認モード（非対話） | 境界内は無承認、外は止めて報告 | bridge は `--permission-mode dontAsk`（prompt になる操作をすべて自動拒否し、agent は拒否行を報告して止まる）。分類器の柔軟さが欲しければ `auto`（未許可の host も分類器が認めれば通る） | `codex exec` は `never`（exec は質問できない） |
| Hard Stop の防波堤 | force push、merge、daemon 再起動、repo 削除 | `permissions.deny` と `permissions.ask`。Bash rule は prompt を減らす仕組みで、プログラムを囲う security boundary ではない。force push の本当の防波堤は GitHub ruleset | experimental の `~/.codex/rules/*.rules`（`decision = "forbidden"` で prompt なしに拒否）。安定するまでは `AGENTS.md` と bridge の `PREAMBLE` |

### この境界で何が起きるか
- `git push`、`gh issue comment`、`npm test`、`~/tasks` へのメモ書き、NAS への読み取り SSH は無承認で通る。
- `git push --force`（引数の位置を問わず）、`gh pr merge`、`gh issue delete`、`gh repo delete`、`launchctl bootout` は deny で即停止し、理由が出る。聞かれない。main への force push は GitHub ruleset でも禁止する。Bash rule は書き方次第で回避され得るので二重にする。
- `launchctl bootstrap`（新しい daemon の登録）と `codex exec` は ask。対話なら 1 タップ、bridge（dontAsk）なら拒否されて `NEEDS-APPROVAL:` か blocked で報告される。
- 許可リストに無い host へのアクセスは、対話なら 1 タップで許可できるが、その許可はそのセッション限りで `allowedDomains` には残らない。恒久化は 3 の 4（週次の昇格）で設定に足す。bridge（dontAsk）では拒否され、blocked として報告される。

## 3. ストレスを減らす七つの仕組み

1. **境界は設定ファイルに一度だけ。** コマンドごとに聞かない。S1〜S4 は 2 の値を入れるだけで消える。
2. **外に出る定番操作に出口を作る。** `gh` は `excludedCommands` で sandbox 外に出し、`Bash(gh issue:*)`、`Bash(gh pr create:*)`、`Bash(gh pr view:*)`、`Bash(gh run:*)` を allow、`Bash(gh auth:*)`、`Bash(gh secret:*)`、`Bash(gh repo delete:*)`、`Bash(gh issue delete:*)`、`Bash(gh pr merge:*)` を deny にする（評価順は deny → ask → allow）。`gh api` は範囲が広いので allow に入れない。`ssh ugnas *` も excluded にする（sandbox 内からは SSH が通らない）。`codex *` は `auth.json` を読む必要があるので excluded にするが、excluded は full access で動くため allow ではなく ask にし、`--dangerously-bypass-approvals-and-sandbox` を deny する。
3. **既知の悪は deny。** 聞かずに止める。止まった理由がそのまま報告になる。
4. **灰色は週に一度まとめて白黒にする。** `/fewer-permission-prompts` が transcript から頻出の read-only コマンドと MCP 呼び出しを集めて allow を提案する。`self-improve` の週次 rot 点検に「先週の prompt と classifier 拒否を allow / deny に昇格」を足す。
5. **業務判断は GitHub Mobile に集約する。** bridge の `needs-approval` は assignee で push、返答は `APPROVED:` コメント（前文書 7.1 / 7.2）。Grok や Duet のチャットで承認を求めない。
6. **保守は窓で束ねる。** bridge の env 変更、host の再起動、plist の更新は「保守窓」として 1 本の Issue にまとめ、承認 1 回で順に実施する。bridge は `inflight.json` が空であることを確認してから実行する。
7. **常設許可を明文化する。** `AGENTS.md` の Hard Stops の直後に「条件を満たせば聞かずに実行してよい操作」を書く。候補:
   - bridge の再起動: 実行中の契約が無く、直前の `doctor.py` が健全で、変更が env の allowlist か routing だけのとき。
   - Remote Control host の再起動: その host に active な session が無いとき。
   - `com.maylac.*` の plist 更新: `launchd/*.template` から生成し、差分が PR で merge 済みのとき。
   - 条件を満たさない場合は従来どおり `NEEDS-APPROVAL:`。沈黙は承認にしない。

## 4. 設定案（そのまま使える差分）

### 4.1 `~/.claude/settings.json`
既存の `permissions.allow` と `sandbox` に足す。`Bash(launchctl:*)` の包括 allow は外し、deny と ask に分ける。

```json
{
  "permissions": {
    "defaultMode": "acceptEdits",
    "allow": [
      "Bash(git push:*)",
      "Bash(git fetch:*)",
      "Bash(git worktree:*)",
      "Bash(gh issue:*)",
      "Bash(gh pr create:*)",
      "Bash(gh pr view:*)",
      "Bash(gh pr list:*)",
      "Bash(gh run:*)",
      "Bash(python3 -m unittest:*)",
      "Bash(npm test:*)",
      "Bash(npm run:*)",
      "Edit(~/tasks/**)",
      "Edit(~/.local/state/slack-bridge/**)",
      "WebFetch(domain:code.claude.com)",
      "WebFetch(domain:support.claude.com)",
      "WebFetch(domain:github.com)"
    ],
    "ask": [
      "Bash(launchctl bootstrap:*)",
      "Bash(launchctl load:*)",
      "Bash(codex exec:*)"
    ],
    "deny": [
      "Bash(git push *--force*)",
      "Bash(git push *-f *)",
      "Bash(git push *+*)",
      "Bash(launchctl bootout:*)",
      "Bash(launchctl unload:*)",
      "Bash(launchctl kickstart:*)",
      "Bash(gh pr merge:*)",
      "Bash(gh issue delete:*)",
      "Bash(gh repo delete:*)",
      "Bash(gh auth:*)",
      "Bash(gh secret:*)",
      "Bash(codex *--dangerously*)",
      "Read(~/.ssh/**)",
      "Read(~/.codex/auth.json)",
      "Read(~/.claude/.credentials.json)",
      "Read(~/.config/slack-bridge/env)",
      "Read(~/.config/gh/**)"
    ]
  },
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": false,
    "failIfUnavailable": true,
    "excludedCommands": ["gh *", "codex *", "ssh ugnas *"],
    "network": {
      "allowedDomains": [
        "github.com", "api.github.com", "objects.githubusercontent.com",
        "api.anthropic.com", "code.claude.com", "support.claude.com",
        "registry.npmjs.org", "pypi.org", "files.pythonhosted.org"
      ],
      "allowLocalBinding": true
    },
    "filesystem": {
      "allowWrite": ["~/tasks", "~/.local/state/slack-bridge"],
      "denyWrite": ["~/.claude", "~/.codex"],
      "denyRead": ["~/.ssh", "~/.codex/auth.json", "~/.claude/.credentials.json", "~/.config/slack-bridge/env", "~/.config/gh"]
    }
  }
}
```

- `excludedCommands` の `gh` は sandbox の外で動くが、deny / ask / allow の rule は効く。`gh api` は rule に無いので対話では prompt、bridge（dontAsk）では拒否になる。
- `allowLocalBinding` は Playwright と `vite preview` のため。不要なら外す。
- NAS の SSH は既存の allow（コマンド全文一致）をそのまま残し、`ssh ugnas *` を `excludedCommands` に入れる。sandbox 内からは `allowedDomains` に host を足しても SSH は接続できず、`~/.ssh` の鍵も見えない。
- `~/tasks` への書き込みは、Bash なら `allowWrite`、Write / Edit ツールなら `Edit(~/tasks/**)` の allow が要る。acceptEdits の自動承認は作業ディレクトリと `additionalDirectories` の内側だけに効く。
- `denyRead` は Bash にしか効かない。`auth.json` と `.credentials.json` は `Read(...)` の deny でも守る（現行設定にはこれが無く、bridge の `-p` 実行では作業ディレクトリ外の Read も確認なしで通る）。
- `denyWrite` は sandbox がもともと書けない場所には何もしない。`~/Library/LaunchAgents` と `~/.config` は cwd 外なので書けず、追加の指定は不要。
- 本セッションでは sandbox 内の HTTPS `git push` は成功した（credential helper が動いた）。失敗する環境なら `git push *` も excluded にする。
- Bash rule は前方一致と `*` の文字列一致で、プログラムを囲う security boundary ではない。force push の本当の防波堤は GitHub の ruleset（7）。

### 4.2 Remote Control の plist
`ProgramArguments` に `--permission-mode acceptEdits` を足す。spawn される session が分類器ではなく rule と sandbox で動くようになり、聞かれるのは境界の外だけになる。`workspace` host と `vantik` host の trust は `~/.claude.json` の `projects.<path>.hasTrustDialogAccepted` を `true` にして前倒しする（S6）。

### 4.3 bridge
`BRIDGE_CLAUDE_PERMISSION_MODE=dontAsk` に変える。prompt になる操作（境界の外、未許可 host、ask rule）はすべて自動拒否され、Codex の `exec` + `never` と同じ挙動になる。分類器の柔軟さが欲しければ `auto` のままでもよいが、未許可の host も分類器が認めれば通る点を理解して選ぶ。拒否は `NEEDS-APPROVAL:` か blocked として Issue に残る。`harness.PREAMBLE` に「deny された操作は回避せず、その行を報告して止まる」を一文足す。

### 4.4 `~/.codex/config.toml`
```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
writable_roots = ["~/tasks", "~/.local/state/slack-bridge"]
```
`codex exec` は bridge が `--sandbox workspace-write` を付けて呼んでいるので変更不要。`exclude_tmpdir_env_var` は既定のままにして `$TMPDIR` を書けるようにする。`writable_roots` は docs の例どおり絶対パスで書く（`~` の展開に頼らない）。

Hard Stop を Codex 側でも設定として強制したい場合は、experimental の `~/.codex/rules/*.rules` に `decision = "forbidden"` で force push、`gh pr merge`、`launchctl bootout` を書く。prompt なしに拒否される。`sandbox_mode` と併用しない前提の機能なので、安定を確認してから使う。

### 4.5 `AGENTS.md`
Hard Stops の直後に 3 の 7（常設許可）を追加する。Core Principles の「ask」の定義に「ツール権限は設定で解決し、会話で聞かない」を一文足す。

## 5. 受け入れ確認

対話 session（Remote Control）で:
```sh
gh issue list -R maylac/agent-tasks --limit 1      # 無承認で成功
git push origin HEAD                                # 無承認で成功
printf 'x' > ~/tasks/.write-test && rm ~/tasks/.write-test   # 無承認で成功
git push origin HEAD --force                        # deny で停止（引数の位置を変えても同じ）
launchctl bootstrap gui/$(id -u) /dev/null          # ask になる（実行しない）
codex exec --help                                   # ask になる
```
Read ツールで `~/.codex/auth.json` を開こうとすると deny になること、GitHub の Rules で main の force push が禁止されていることも確認する。
bridge で: `NEEDS-APPROVAL:` を出す契約 1 本と、`gh issue comment` を使う契約 1 本を流し、前者が `needs-approval`、後者が `done` になる。

計測: 1 週間の transcript から prompt 回数と分類器拒否回数を数える（`/fewer-permission-prompts` の集計を流用）。目標は対話 1 session あたり prompt 0〜1 回、bridge の分類器拒否 0 回。達しなければ 3 の 4 で allow / deny に昇格する。

## 6. 選択肢 B: Codex の現状（境界なし）に揃える

Claude を `defaultMode: "bypassPermissions"`、`sandbox.enabled: false` にすると prompt も分類器も消える。失うもの:
- 秘密（SSH 鍵、auth.json、bridge env）の読み取り禁止。
- ネットワーク先の制御。未知の host への送信が止まらない。
- `rm -rf`、force push、daemon 再起動の防波堤。Hard Stop は `AGENTS.md` の文章だけで守ることになる。
- Downloads 取り込みガードは hook なので残る。

この案は推奨しない。承認ストレスの大半（S1〜S4）は 2 の境界を書けば消え、残るのは本来人が決めるべき②③だけになる。

## 7. 本人の判断が必要な項目

- Codex を `workspace-write` + `on-request` に戻すか（監査 A2 の再掲。戻さない場合は Codex 側の Hard Stop が文章だけになる）。
- `allowedDomains` の初期リスト（上の 9 件）。
- main への force push を GitHub ruleset で禁止する（repo 設定の変更）。
- bridge の Claude を `dontAsk` にするか `auto` のままにするか。
- 常設許可の条件（3 の 7）。
- 選択肢 A（共通境界）か B（境界なし）か。
- `~/.claude/settings.json` と plist の変更は設定変更なので、適用は本人の了解の後に行う（適用自体は bridge 契約か Remote Control session で、PC 操作なし）。
