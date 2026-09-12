# V150 完了引き継ぎ — 2026-09-06

**V150 は本体反映済み。終端 `PROMOTED`、rollback保護内のpostcheck `pass` を確認した。**
2026-09-05の中断引き継ぎは履歴。そこにあるprepare/applyを再実行しない。

## 現在の本体

| 項目 | 反映前 | 反映後・実測 |
| --- | ---: | ---: |
| subjects | 120 | 135 |
| locations | 90 | 109 |
| compatibility rows | 5,806 | 8,227 |
| base variations | 103,212 | 150,184 |

欠落action poolは0。27ファイルのtransactionでデータを反映した。
既存の多数の編集・未追跡ファイルは維持。stage・commitは行っていない。
V250/V350/V500は今回の対象外で、未着手。

## 今回の追加修正

- `vocab/garnish/logic.py`：skyline/horizon/ceilingを直接見る動作に、任意の下向き視線を重ねない。
  expression枠由来の`downcast eyes`にも共通判定を適用。請求書・雨量計などを見下ろす動作は維持。
- `assets/test_personality_garnish.py`：回帰テスト2件。修正前22サブテスト失敗を再現し、修正後の関連23テスト成功。
  独立レビューで対象16ケースのRNG最終状態一致、対象外5ケースの出力・RNG一致も確認。
- `verification/frontend/customNodeWorkflowCompatibility.test.ts` と
  `customNodeWorkflowRoundtrip.test.ts`：object caseを`it.for`へ統一し、型importを独立。
  callbackとassertionは維持。実Vitest 4件、対象5ファイルのoxlint、frontend vue-tscが成功。
- 新依存なし。整理計画は `.omx/plans/v150-resume-cleanup.md`。

## 棄却と新しい正式評価

`assets/results/v150-release-20260905-resume/` は最初の再開試行。
872 Python / 4 frontend / 2 browserと自動比較は成功したが、v7レビューで
`checking the skyline beyond the tables` と `downcast eyes` の候補固有の矛盾1件を報告し棄却。
投票・review.jsonは変更していない。`superseded.json`が新しい実験を指す。

修正後の正式authoring：
`docs/variation_expansion/experiments/v150-gaze-release-20260905/`

正式評価出力（以下 `OUT`）：
`assets/results/v150-gaze-release-20260905/`

| 検証 | 結果 |
| --- | --- |
| action pools / compatibility / data / full flow / widgets | 5ゲートpass |
| 候補の全Python | 874件成功、skipなし |
| 実frontend / Chrome browser | 4件 / 2件成功、候補の読み込み元をsentinelで拘束 |
| 固定64+16自動比較・意味比較 | pass |
| 新規独立2名×20組のv7レビュー | pass、候補固有の重大欠陥0 |
| g004 / g005 / g006 confirmation | 各256件、すべてpass |
| 十一ゲート集約 | pass |
| 実activeに対するpromote-check / preflight | promote、独立読み取りレビュー承認 |
| apply / rollback保護内postcheck | PROMOTED / pass |

正式reviewerは新規contextの `gpt-6-astra`：
`/root/v150_gaze_blind_1`、`/root/v150_gaze_blind_2`。
各laneのみを見て評価。旧reviewerや旧投票は再利用していない。

| 評価項目 | 改善 | 悪化 | 同等 |
| --- | ---: | ---: | ---: |
| naturalness | 31 | 2 | 7 |
| image_prompt_suitability | 31 | 1 | 8 |
| consistency | 18 | 1 | 21 |
| redundancy | 17 | 3 | 20 |
| protagonist_clarity | 0 | 0 | 40 |

承認済みv7の改善・非回帰閾値は維持。diversityはcorpus confirmationでpass。
未使用seedはリポジトリ外の
`C:/Users/inott/Downloads/v150-gaze-release-20260905-confirmation-seeds.json`。
今後このseedを未使用holdoutとして再利用しない。

## 反映後の証拠

- [promotion-receipt.json](../../assets/results/v150-gaze-release-20260905/promotion-receipt.json)
- [verification-receipt.json](../../assets/results/v150-gaze-release-20260905/verification-receipt.json)
- [preflight.json](../../assets/results/v150-gaze-release-20260905/preflight.json)
- [review/review.json](../../assets/results/v150-gaze-release-20260905/review/review.json)
- [confirmation-bundle.json](../../assets/results/v150-gaze-release-20260905/confirmation/confirmation-bundle.json)
- [post-apply/executions.json](../../assets/results/v150-gaze-release-20260905/post-apply/executions.json)

本体上で5データチェックと正確な件数、全Python 874件、frontend 4件、browser 2件が成功。
frontend/browserのsentinelは本体rootを指し、`loaded_active_plugin=true`。
固定80件のrecords.jsonlは候補と本体でbytes完全一致：

`7cc3cec3bb8ac4b43faa3a95b353743f6cb9028eaa5c01bac5e53c6dad117871`

凍結候補および反映時のsource hash：

`02897749003c121007083258c4f3d53e187949c9c93ea10a0208f8b79f786806`

凍結候補content hash：

`0828e685845c58c0518559fbf103845e01669a14f0cf1d06284499106aa3176d`

promotion receipt内部hash：

`31c1f1a006d32e8c8e49426ced2249d3ba228a1d89ce6b89122288d7a1dd7fd9`

README/tasks/progressとこの引き継ぎは**昇格成功後**に更新した。
source hashとdocsを含むcontent hashは区別する。凍結receiptは検証時点の証拠であり、
更新後docsまで同一contentと主張しない。更新後の照合記録は
`OUT/post-documentation-identity.json` に保存する。
snapshotの`.verification-inputs.json`は本体へコピーしていない。

昇格後、Windowsの兄弟stagingからの置換で27ファイルが保護ACLを継承し、
sandboxの読み取りとGit差分検査が拒否された。実postcheckは昇格用権限で成功していた。
対象27ファイルだけを配置先フォルダの継承ACLへ戻し、全ファイルの変更前後SHA256一致を確認。
`OUT/acl-normalization.json` にSDDLとhashを保存した。独立担当者も通常sandboxからの
全27ファイルの読み取り・import・hash一致を再確認済み。データbytesの変更はない。

## 残る注意点

V150完了を阻む既知の問題はない。全自然言語の視線推論を実装したわけではなく、
今回の修正は明示的な対象と方向の競合に限定している。
汎用promoter CLIのROLLED_BACK時の終了コードと、staging生成途中失敗時の一時ディレクトリ残存は
独立レビューで非阻害の保守事項として記録した。今回のdriverはPROMOTED以外を失敗にし、
実transactionは成功済み。これらを理由にV150を再applyしない。
Windowsで今後同じ昇格経路を使う場合は、兄弟stagingから置換したファイルの配置先ACL継承も確認する。

実成果物と5本の作業driverは `assets/results/` 配下のignoredファイル。
履歴・証拠・transaction journal/backupと併せて保持する。将来のcommitには自動では含まれない。
実行環境・driverの注意点は旧 [中断引き継ぎ](./HANDOFF_2026-09-05_V150_RESUME.md) の環境節を参照。
新しい拡張は現在のactiveをbaselineとして別実験にし、過去receiptを使い回さない。
