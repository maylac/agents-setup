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

境界は一つにする。**「workspace-write + 固定ネットワーク許可 + 秘密の読み取り禁止」** を Claude と Codex に同じ値で置く。境界の内側は聞かない。外側は「聞く」ではなく「止めて理由を報告」（非対話）か「1 タップで許可してルールに昇格」（対話）にする。

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
| 読み取り禁止 | `~/.ssh`、`~/.codex/auth.json`、`~/.claude/.credentials.json`、`~/.config/slack-bridge/env`、`~/.config/gh` | `sandbox.filesystem.denyRead` | `[sandbox_workspace_write]` に同等の設定が無い場合は、`AGENTS.md` の禁止と bridge の `harness.PREAMBLE` で補う |
| ネットワーク | 固定の許可リスト（`github.com`、`api.github.com`、`objects.githubusercontent.com`、`api.anthropic.com`、`registry.npmjs.org`、`pypi.org`、`files.pythonhosted.org`、`code.claude.com`、NAS の Tailscale host） | `sandbox.network.allowedDomains` | `[sandbox_workspace_write] network_access = true`（Codex は host 単位の制限が無いので、`AGENTS.md` の「未確認の外部送信は Hard Stop」で補う） |
| 境界の外へ出る出口 | `gh`（keyring が要る）、`codex`、`ssh ugnas` | `sandbox.excludedCommands` + allow rule | 該当なし |
| 承認モード（対話） | 境界内は無承認、外は 1 タップ | `permissions.defaultMode: "acceptEdits"` + `autoAllowBashIfSandboxed: true` | `approval_policy = "on-request"` |
| 承認モード（非対話） | 境界内は無承認、外は止めて報告 | bridge は `--permission-mode auto`（分類器が判定、拒否は `NEEDS-APPROVAL:` か blocked で報告） | `codex exec` は `never`（exec は質問できない） |
| Hard Stop の防波堤 | force push、merge、daemon 再起動、repo 削除 | `permissions.deny` と `permissions.ask` | `AGENTS.md` と bridge の `PREAMBLE`（Codex に deny rule の仕組みが無い） |

### この境界で何が起きるか
- `git push`、`gh issue comment`、`npm test`、`~/tasks` へのメモ書き、NAS への読み取り SSH は無承認で通る。
- `git push --force`、`gh pr merge`、`gh repo delete`、`launchctl bootout` は deny で即停止し、理由が出る。聞かれない。
- `launchctl bootstrap`（新しい daemon の登録）は ask。対話なら 1 タップ、bridge なら `NEEDS-APPROVAL:`。
- 許可リストに無い host へのアクセスは、対話なら 1 タップで許可して `allowedDomains` に足す。bridge なら blocked として報告する。

## 3. ストレスを減らす七つの仕組み

1. **境界は設定ファイルに一度だけ。** コマンドごとに聞かない。S1〜S4 は 2 の値を入れるだけで消える。
2. **外に出る定番操作に出口を作る。** `gh` は `excludedCommands` で sandbox 外に出し、`Bash(gh issue:*)`、`Bash(gh pr create:*)`、`Bash(gh pr view:*)`、`Bash(gh run:*)` を allow、`Bash(gh auth:*)`、`Bash(gh secret:*)`、`Bash(gh repo delete:*)`、`Bash(gh pr merge:*)` を deny にする。`gh api` は範囲が広いので allow に入れない。
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
      "Bash(codex exec:*)",
      "Bash(python3 -m unittest:*)",
      "Bash(npm test:*)",
      "Bash(npm run:*)",
      "WebFetch(domain:code.claude.com)",
      "WebFetch(domain:support.claude.com)",
      "WebFetch(domain:github.com)"
    ],
    "ask": [
      "Bash(launchctl bootstrap:*)",
      "Bash(launchctl load:*)",
      "Bash(gh pr merge:*)"
    ],
    "deny": [
      "Bash(git push --force:*)",
      "Bash(git push -f:*)",
      "Bash(launchctl bootout:*)",
      "Bash(launchctl unload:*)",
      "Bash(launchctl kickstart:*)",
      "Bash(gh repo delete:*)",
      "Bash(gh auth:*)",
      "Bash(gh secret:*)",
      "Read(~/.ssh/**)",
      "Read(~/.config/slack-bridge/env)",
      "Read(~/.config/gh/**)"
    ]
  },
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": false,
    "failIfUnavailable": true,
    "excludedCommands": ["gh *", "codex *"],
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
      "denyWrite": ["~/.claude", "~/.codex", "~/Library/LaunchAgents", "~/.config"],
      "denyRead": ["~/.ssh", "~/.codex/auth.json", "~/.claude/.credentials.json", "~/.config/slack-bridge/env", "~/.config/gh"]
    }
  }
}
```

- `excludedCommands` の `gh` は sandbox の外で動くが、deny と allow の rule は効く。`gh api` は rule に無いので対話では prompt、bridge では分類器判定になる。
- `allowLocalBinding` は Playwright と `vite preview` のため。不要なら外す。
- NAS の SSH は既存の allow（コマンド全文一致）をそのまま残す。sandbox 内から通すには NAS の Tailscale host を `allowedDomains` に足す。

### 4.2 Remote Control の plist
`ProgramArguments` に `--permission-mode acceptEdits` を足す。spawn される session が分類器ではなく rule と sandbox で動くようになり、聞かれるのは境界の外だけになる。`workspace` host と `vantik` host の trust は `~/.claude.json` の `projects.<path>.hasTrustDialogAccepted` を `true` にして前倒しする（S6）。

### 4.3 bridge
`BRIDGE_CLAUDE_PERMISSION_MODE=auto` は維持する。非対話では prompt に答えられないので、分類器が灰色を判定し、拒否は `NEEDS-APPROVAL:` か blocked として Issue に残る。`harness.PREAMBLE` に「deny された操作は回避せず、その行を報告して止まる」を一文足す。

### 4.4 `~/.codex/config.toml`
```toml
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
writable_roots = ["~/tasks", "~/.local/state/slack-bridge"]
```
`codex exec` は bridge が `--sandbox workspace-write` を付けて呼んでいるので変更不要。`exclude_tmpdir_env_var` は既定のままにして `$TMPDIR` を書けるようにする。

### 4.5 `AGENTS.md`
Hard Stops の直後に 3 の 7（常設許可）を追加する。Core Principles の「ask」の定義に「ツール権限は設定で解決し、会話で聞かない」を一文足す。

## 5. 受け入れ確認

対話 session（Remote Control）で:
```sh
gh issue list -R maylac/agent-tasks --limit 1      # 無承認で成功
git push origin HEAD                                # 無承認で成功
printf 'x' > ~/tasks/.write-test && rm ~/tasks/.write-test   # 無承認で成功
git push --force origin HEAD                        # deny で停止（実行されない）
launchctl bootstrap gui/$(id -u) /dev/null          # ask になる（実行しない）
```
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
- `allowedDomains` の初期リスト（上の 9 件 + NAS）。
- 常設許可の条件（3 の 7）。
- 選択肢 A（共通境界）か B（境界なし）か。
- `~/.claude/settings.json` と plist の変更は設定変更なので、適用は本人の了解の後に行う（適用自体は bridge 契約か Remote Control session で、PC 操作なし）。
