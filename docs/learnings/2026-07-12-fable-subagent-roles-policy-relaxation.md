# Fableサブエージェント全面禁止ポリシーへの有界2ロール例外の導入

- 日付: 2026-07-12
- 領域: agents-setup / fable-escalation, claude/agents
- 種別: architecture

## 問題

Lance Martin記事(Cost effective harnesses with Fable, x.com/RLanceMartin/status/2075641284635799865)のadvisor/verifierロールをハーネスに導入したい。しかし既存のfable-escalationは「No subagent is pinned to fable / main-session切替のみ」の厳格ポリシーで、記事のパターン(安価なexecutorがFableサブエージェントに有界相談)と真っ向から矛盾。RED観測では6/6のシナリオ実行で「re-ranking is normal executor judgment」「verification maps to the Opus tier」と合理化され、探索タスクのhill-climbingと高リスク完了主張の無ゲート化が実証された。

## 試して駄目だった道

- 新スキル追加(fable-roles等): トリガー条件がfable-escalationと重複し、スキル数削減方針(121→82監査)に逆行 → 既存スキルの改定に一本化。
- 全面解禁(ポリシー削除): コスト暴走リスク。feedback_no_pipeline_on_fable(量産をFableで回さない)と衝突 → 却下。
- Workflowスクリプト内の禁止を全面維持: /goal型ループの最終ゲートという記事の核心ユースケースを塞ぐ → 有界例外(advisor≦3/run、verifierはclaim単位1回)へ。

## 効いたアプローチ

「3つのFable進入モード」への再構成: (1) Escalation=/model fable(既存・人間承認) (2) Advisor=fable-advisorサブエージェント(計画済みチェックポイント+3連続限界利得トリガー、ハードキャップ3回/run) (3) Verifier=fable-verifierサブエージェント(高コスト着地の完了主張ゲート、claim毎1回)。両ロールとも読み取り専用・相談専用で、executor/workerのFable実行は禁止のまま。writing-skillsのRED-GREEN-REFACTORをハーネス設定に適用し、GREEN 6/6(正しいロール選択)+過剰使用プローブ3/3(通常タスクで不使用)まで検証。

## なぜ効いたか

矛盾の実体は「人間のループ維持」と「タスク中の判断散布」の対立ではなく、**無界な委譲**と**有界な相談**の混同だった。ロールを読み取り専用・回数キャップ・トリガー条件付きの「相談」に限定すれば、コスト規律と人間のループ(escalationは従来どおり人間承認)を保ったまま記事の効果(hill-climbing矯正・完了ゲート)を得られる。裏づけ: baseline 0/6 → GREEN 6/6 → 過剰使用プローブ3/3(sonnetサブエージェント各3反復、構造化出力で機構を判定)。レビュー4レンズ(記事忠実性/整合性/スキル品質/コスト規律red-team)で「効率が使用を正当化する」抜け穴等8件を検出し、tie-breaker限定条項などで封鎖。

## 一般化できる原則

- ポリシーとパターンが矛盾したら、禁止対象を「委譲の無界性」まで分解してから例外を切ること。例外は (a) 読み取り専用 (b) 回数キャップ (c) 観測可能な発火条件、の3点が揃っていること。
- ハーネス設定(スキル/エージェント定義)の変更は、変更前に失敗シナリオを観測(RED)し、変更後に同一シナリオ+過剰使用プローブの両方向で検証すること。片方向(発火する)だけの検証は抜け穴を見逃す。
