# Q87 後の作業手順・スクリプト整理

対象はリファクタリングを進めるための運用資料と confirmation ツール。
生成ロジック、active variation data、品質閾値、過去の判定は対象外。

追記: 下記で残した検証基盤の問題は、後続の
[修復記録](./VERIFICATION_REPAIR_2026-09-05.md)で対応した。以下の失敗数は修復前の記録。

## 着手前の整理方針

1. README の古い進捗説明・実験一覧の重複を削り、q87 と現在の実行順序に集約する。
   tasks / progress / 500k plan の古い「次の作業」は履歴と区別する。
2. 不完全な snapshot で品質レビュー・confirmation を先に実行する手順を改める。
   修正中は対象テスト、候補を凍結する前は実行環境と決定的な検証、最後に品質評価を行う。
   昇格前の十一 gate と厳密な source/content hash の照合は維持する。
3. confirmation cohort 作成直後の同一履歴の再走査を削る。
   生成処理を挟んだ後の履歴読み直しは維持し、実行間のキャッシュは導入しない。
4. confirmation の結果に adapter 名を記録するだけのために、親プロセスの
   renderer を monkey-patch する処理を削る。baseline の改変は生成子プロセスに限定する。
5. 回帰テスト、全 Python suite、差分検査、利用可能な静的検査で確認する。

## 維持する契約

- 256 unique holdout seeds、過去 cohort との重複拒否、三つの objective と比較条件。
- comparison/v4、review/v6、verification evidence/v2 と歴史的 v4/v5 判定。
- 子プロセスの source isolation、実行後の hash 検査、昇格前の十一 gate。
- q87 の証拠はその snapshot にだけ有効。今回の tools/tests の変更は source hash を変える。

## 検証基準

変更前の関連テスト: 62 件 PASS。
追加する確認: cohort の再現性・重複拒否・実行間の履歴再読込、結果作成による
親 renderer の汚染がないこと。性能は履歴走査回数の削減を検証し、料金や所要時間の
未測定の改善率は主張しない。

## 見送る削減

三 lane の candidate 生成共有、source hash の永続キャッシュ、旧 schema の削除は、
実行独立性や証拠の検証に影響するため今回行わない。README から除く実験リンクの
参照先は tasks / progress と既存 experiments に残す。

## 実施結果

- README と 500k plan から重複した旧進捗を削除し、tasks / progress の入口を q87 に更新。
- cohort 新規作成時の履歴走査を 2 回から 1 回に削減。生成後の再走査は維持。
- adapter 名の記録には既存の `ablation_contract()` を使用し、親 renderer の変更と
  不要な動的 import を削除。
- 関連テストは追加 3 件を含め 65 件 PASS。独立レビューも APPROVE。
- 変更した Python 2 ファイルの AST/compile、資料リンク、`git diff --check` は PASS。
  Ruff / mypy / pyright はこの環境に未導入のため未実行。依存は追加していない。

作業ツリーの全 suite は 716 tests、38 failures、29 errors。固定証拠の CRLF 化を確認した。
例: L0 `manifest.json` は Git 内では期待値
`7bb90af6b124b724c484034fddbe1dad05006fc897947ce359d6f5a769acae54` と一致するが、
`core.autocrlf=true` の作業ツリーでは
`ed2eccd0ef3717ce7899e6d1a1e24648fb61808aee270c50b60057c8dd24f100`。
LF に戻した bytes の hash は期待値と一致した。今回の変更で固定 hash は更新していない。

改行変換を無効にした `git -c core.autocrlf=false archive --format=zip HEAD` の
一時コピーでも別の既存 artifact / 入力 hash 不一致が残るため、同じ環境で変更前後を比較した。

| 検証対象 | tests | failures | errors |
| --- | ---: | ---: | ---: |
| 変更前 `b4170ed1638f202d6fac781eb5bf711c6a86ecde` | 725 | 31 | 26 |
| 同じ LF コピー + 今回の差分 | 728 | 31 | 26 |

失敗・error のテスト ID（subtest を含む）と種別は全件一致し、追加 3 tests は PASS。
全体合格を意味しない。固定証拠の入力依存と candidate 実行環境の修復は次の作業として残る。
frontend/browser と正式な再レビュー・confirmation・promotion は未実行。

比較結果とログ（ローカル生成物）:

- [変更前後の比較 JSON](../../assets/results/workflow-cleanup-20260905-regression-comparison.json)
- [変更前ログ](../../assets/results/workflow-cleanup-20260905-baseline-tests.log)
- [変更後ログ](../../assets/results/workflow-cleanup-20260905-lf-tests.log)

変更ファイル:

- `tools/build_prompt_quality_confirmation.py`: 重複走査と不要な副作用を除去。
- `assets/test_variation_candidate_gates.py`: 上記の回帰テスト 3 件。
- `docs/variation_expansion/README.md`: Astra 向けの現行手順。
- `docs/variation_expansion/500k_loop_plan.md`: 過去の進捗説明の重複を除去。
- `docs/variation_expansion/tasks.md`, `progress.md`: 現在地を訂正。
- このファイル: 整理方針、独立レビュー、検証結果と残る問題。
