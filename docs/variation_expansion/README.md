# Variation Expansion: 現在の作業入口

更新: 2026-09-06。**P13 / V150 は本体反映・反映後検証まで完了。**
[最新の引き継ぎ](./HANDOFF_2026-09-06_V150_PROMOTED.md) を先に読む。
Q87と2026-09-05の中断記録は履歴であり、再applyの指示として扱わない。

## 現在地

- active: **135 subjects / 109 locations / 8,227 rows / 150,184 base variations**。
- `v150-gaze-release-20260905` の11ゲート、独立2名のv7レビュー、3目的×256件のconfirmationがpass。
- 27ファイルをrollback保護付きで反映し、終端 `PROMOTED`・postcheck `pass` を確認。
- 候補・本体それぞれPython 874件、frontend 4件、browser 2件が成功。本体の固定80出力は候補とbytes一致。
- [昇格証拠](../../assets/results/v150-gaze-release-20260905/promotion-receipt.json)と
  [全ゲート証拠](../../assets/results/v150-gaze-release-20260905/verification-receipt.json)は検証時点の凍結記録。
  反映後に更新したdocsのcontentまで凍結候補と同一とは扱わない。
- V250以降は未着手。stage・commitは実施していない。

## GPT-6 Astra での進め方

目的、対象ファイル、維持する挙動、完了条件を短く固定し、実装方法はコードと失敗事例から
判断する。対象の回帰テストを先に確認し、一つの原因を修正して必要な検証まで進める。
数値集計・hash 照合・定型検証は既存 CLI に任せ、Astra は原因分析・修正・意味の評価に使う。
通常の修正ごとに新しい計画・承認会議・役割別レビューを増やさない。
独立した調査やレビューが有効なときだけ native subagent に範囲を限定して委任し、
モデルは実行セッションの設定を継承する。正式な blind review の二 lane は維持する。

検証は下表のタイミングで行う。同じ変更・同じ入力の合格済み検証を理由なく繰り返さず、
新たな変更、失敗、未解決の懸念がある場合に範囲を広げる。
報告は変更点・検証結果・残る問題を簡潔に記す。

この運用は Astra の指示感度と過剰な検証を調整する
[OpenAI の公式ガイド](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra)
を、このリポジトリに適用したもの。料金・速度の改善率は未測定。

## 実行順序

| 段階 | 実施する確認 | 次へ進む条件 |
| --- | --- | --- |
| 資料・ツールの修正 | 変更対象の回帰テスト、差分検査、該当する静的検査 | 対象挙動が維持される |
| candidate の修復 | 失敗原因の再現テスト、snapshot 入力・docs・外部実行環境の確認 | 既知の環境不備が解消する |
| 候補の確定 | candidate 上の action pools、compatibility、data、full flow、widgets、全 Python tests、frontend、browser | 八つの実行 gate が通る |
| 品質評価 | 固定 64+16 自動比較、semantic pairs、比較に結び付いた v7 blind review、g004/g005/g006 各 256 seeds | 現行品質契約が通る |
| 昇格判定 | 同一 candidate root/source/content hash の十一 gate の evidence/v2 を集約 | full verification receipt が pass |

candidate を凍結してから得た実行 gate の結果は、品質評価後も root/hash と証拠が一致すれば
再実行せず集約できる。修正中の試走は正式な合格証拠にしない。
凍結後に source/content が変わった場合は、新しい snapshot と対応する証拠が必要。
docs のみの編集でも、変更がどの hash に含まれるかは現行 manifest の規則で判断する。

confirmation はコードによる生成・解析であり、LLM の三重レビューではない。
正式な品質比較・二つの blind lane・三 objective・十一 gate の条件を弱めて
実行費用を減らさない。

## 検証基盤と次の候補

[検証基盤の修復](./VERIFICATION_REPAIR_2026-09-05.md)で、LF の固定、自己完結する
テスト入力、snapshot の検証用ファイル、候補と外部 runtime のパス分離を実装した。
新しい baseline は三つの計画・分析・snapshot ツールに同じ `--baseline-manifest` を渡す。
過去の壊れた hash を現在の入力へ暗黙に読み替えない。

V150ではcompatibility driftと視線の競合を修正し、外部frontend・実browserを含む全ゲートを通した。
以後の変更では新しいactive baselineを明示し、必要な段階だけを実行する。
V150の凍結receiptを、変更後のsource/contentやV250以降の合格証拠に流用しない。

## 必要なときだけ読む資料

- [今回の整理方針・検証記録](./WORKFLOW_CLEANUP_2026-09-05.md)
- [Task Board](./tasks.md): 作業 ID と過去の証拠リンク。
- [Progress](./progress.md): 過去の経緯。古い「次の作業」を再実行しない。
- [500k Loop Plan](./500k_loop_plan.md): V150 以降の目標と stage 契約。
- [L3 Snapshot Contract](./candidate_l3_contract.md): snapshot の変更時。
- [Prompt Quality Baseline](../prompt_quality/README.md): 受入済み品質契約。
- [Semantic Review Policy v4](../../vocab/data/variation_semantic_review_policy_v4.json):
  comparison/v5 と review/v7。一貫性を非回帰の保護項目とする
  [ユーザー承認済み変更](./CONSISTENCY_SCOPE_PROPOSAL_2026-09-05.md)。旧 v6 の棄却は保存する。

`.omx/plans/` の初期設計書、完了済み context refactor、過去の rejected attempt は履歴。
その時点の「未実装」「承認待ち」を現在の作業指示として読み直さない。
履歴 artifact・hash・schema の解釈は保持する。
