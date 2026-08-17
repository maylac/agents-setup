# Macのlive設定とSurface用portable snapshotを同一視しない

- 日付: 2026-08-17
- 領域: agents-setup / backup・install・audit
- 種別: architecture

## 問題

MacのClaude/Codex設定をSurface WSLへ再現する際、live設定にはVibe Island、RunCat、Homebrew Moshi、`afplay`、Agent NotchなどMac専用hookが混在していた。一方、backupはliveとの完全一致を正とし、agent/hook実体のinstallerは存在せず、JSONの`\/Users\/name`形式は既存sanitizerを通過していた。このままでは、監査を通すほどSurfaceで存在しないcommandが増える構造だった。

## 試して駄目だった道

- `/Users/name`だけを置換した: JSONエスケープされた`\/Users\/name`の2本目のslashが一致せず、ユーザー名が残った。
- live `hooks.json`をそのままpublic snapshotへ同期した: Vibe IslandとRunCatまでportable設定へ入り、WSLで存在しないcommandを登録する。
- Paseoの実ディレクトリを一般的なmirror driftとしてsymlink化しようとした: Paseoアプリ自身の更新仕様と衝突するため、所有者境界が誤っていた。
- agent/hookは暗号化payloadにあるため手作業で戻せばよいとした: 再現手順と監査証拠がなく、「保全済み」と「利用可能」を区別できなかった。

## 効いたアプローチ

1. home path regexを、各slash直前のbackslashを任意にする`\\?/Users\\?/...`へ変更し、JSONの意味値でも回帰テストした。
2. snapshot生成時にMac専用hookだけをJSON構造として除外し、auditでは同じ既知2種だけをlive-only差分として許容した。
3. Claude templateでもmacOS sound、Homebrew、Vibe Island、Agent Notchを除外し、git push/PR作成を`ask`へ正規化した。
4. `--assets-only`と`--apply-assets`を追加し、public-safe agents/hooksをdry-run、既存backup、copy、冪等再実行できるようにした。
5. Paseoと外部repo正本のcompact-plusは、削除せずintentional differenceとして監査へ明記した。

## なぜ効いたか

liveの完全複製ではなく、`portable canonical subset + 所有者が明確なplatform差分`を不変条件にしたため、Macの機能を保持しながらSurfaceへ無効なcommandを輸出しなくなった。文字列置換ではなくJSON構造でhookを選別したため、書式や配列順序に依存しない。

裏づけ: `scripts/validate.sh`、6本のfixture/regression test、live `scripts/audit-sync.sh`が全PASS。実snapshotは97 canonical skills中96 public-safe skillsを収録し、除外はprivateな`capafy-publisher`のみ。

## 一般化できる原則

- 異なるOSへ設定を移す場合、live完全一致ではなくportable subsetとplatform-owned差分を別々に検証する。
- JSON/YAML等のserialized textは表示文字列ではなく意味値と構造でsanitizationをテストする。
- 「バックアップに存在する」だけでは復元完了ではない。dry-run可能なinstallerとlive parity auditの両方を用意する。
