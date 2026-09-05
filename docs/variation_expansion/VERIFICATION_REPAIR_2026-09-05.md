# 検証を妨げる依存関係の修復

## 修正前の方針

- 固定 hash の検証は維持し、改行は Git attributes で LF に固定する。
- 過去の receipt を書き換えず、テスト自身が生成する hash-bound fixture へ切り替える。
  存在しない `assets/results` や、過去の環境に依存した単体テストを解消する。
- planner は明示した新しい baseline manifest も検証できるようにする。
  過去の manifest を暗黙に現在の入力へ再束縛しない。
- snapshot に検証用 docs・補助スクリプトを含め、その追加ファイルも content hash に束縛する。
  外部 ComfyUI / frontend / node_modules は snapshot に複製しない。
- frontend/browser は candidate source と active plugin / external runtime のパスを分ける。
  テスト自身にも candidate パスを伝え、異なる source の検証を合格扱いにしない。
- 変更前の再現テスト、各修正の回帰テスト、全 Python suite、静的検査を行う。
  実際の frontend/browser 検証は利用可能な外部 runtime がある場合に実行する。

対象は検証・計画ツールとそのテスト。active variation の内容、品質閾値、歴史的判定は保持する。

## 変更内容

- `.gitattributes`: text を LF に固定。既存の未編集ファイルは Git 内と同じ LF bytes に戻した。
- `assets/variation_test_fixtures.py` と六つの variation テスト:
  一時ディレクトリで入力・参照 hash を生成し、一回のテストプロセスで共用する。
  無視された過去のローカル出力への依存と、テスト自身の過去 hash を固定する一件を除去した。
  実際の hash 検証・改ざん検出・witness replay は維持している。
- `tools/plan_variation_target.py`, `analyze_variation_candidates.py`,
  `materialize_variation_candidate_snapshot.py`: 明示的な baseline を計画から snapshot まで伝達する。
- snapshot は docs、assets の補助ファイル、限定した旧 baseline 参照をコピーし、
  `.verification-inputs.json` で追加ファイルを content hash に束縛する。
  marker のない旧 snapshot の hash 規則は変えない。
- `promote_variation_candidate.py`: 昇格前後と rollback でも同じ検証用 manifest 本文を使う。
  本文は preflight/journal に固定し、候補削除後の復旧にも利用する。
  marker を active にコピーしたり、昇格の変更許可リストを広げたりしない。
  `POSTCHECK` で停止した場合も新しい apply を拒否し、rollback-only recovery を許可する。
- 三つの PowerShell runner/sync と三つの frontend/browser TS テスト:
  candidate の明示的パスを使用。外部 runtime の不足を実行前に検出し、終了時に環境変数を戻す。
  corepack の間接呼び出しを除去し、インストール済み Vitest を直接使う。
  browser 出力と junction を候補から分離し、走査前に生成物・外部 runtime を除外する。
- snapshot / confirmation 子プロセスの入出力を UTF-8 に固定。日本語パスで UTF-8 の JSON や
  非 ASCII 文字を出力した場合の CP932 decode エラーを解消した。
  Vitest の `@` alias も、ドライブ直下の `/src` から設定ファイル配下の `src` へ修正した。

テスト内で生成する snapshot/receipt は fixture であり、実際の品質合格や昇格の証拠ではない。

## 実行方法

通常の回帰確認:

```powershell
python -m unittest discover -s assets -p 'test_*.py'
```

新しい実験の baseline は現行 protected inputs と pool policy の hash を明示的に束縛し、
別ファイルとして保存する。scenario 側もその manifest の hash に束縛する。
`plan_variation_target.py`、`analyze_variation_candidates.py`、
`materialize_variation_candidate_snapshot.py` は同じ `--baseline-manifest <path>` を受け取る。
省略時は従来の L0 に対する厳密な検証を維持し、不整合な履歴は拒否する。

frontend/browser runner は以下を受け取る:

- `-CustomNodeRoot`: 凍結した候補の root。
- `-ActivePluginRoot`: 元のリポジトリ root（gate inventory が設定）。
- `-FrontendRoot` または `VSCG_FRONTEND_ROOT`: 依存関係を導入済みの frontend checkout。
- browser の `-ComfyRoot` または `VSCG_COMFYUI_ROOT`: 外部 ComfyUI checkout。
- browser の `-Python` と `-Port`: ComfyUI 用 Python と未使用ポート。

ローカルの ComfyUI Desktop 本体は確認できたが、稼働中サーバーと frontend 開発用 workspace は
見つからなかった。実 frontend/browser gate は未実行。制御した subprocess/PowerShell テストで
候補パス、環境復元、実行失敗、ポートの取り違え、空白を含むパスを確認している。

## 最終検証

| 確認 | 結果 |
| --- | --- |
| 全 Python regression | **802 tests PASS、failure/error/skip なし** |
| `validate_prompt_data.py` | ERROR / WARNING ともに 0 |
| `build_compatibility_review.py --check` | 5,806 rows、missing / extra / pair drift すべて 0 |
| `build_action_pools.py --check` | runtime / source ともに 96、ERROR / WARNING 0 |
| 変更 Python の構文検査、PowerShell AST、`git diff --check` | PASS |
| 独立レビュー | support hash と promotion の不整合を検出して修正、修正後の整合を確認 |
| 実 frontend/browser・TypeScript 全体 typecheck | 開発用 workspace / 依存関係がなく未実行 |

[全体テストログ](../../assets/results/verification-repair-final-tests.log)はローカル生成物。
変更前に再現した日本語パスの decode 失敗と POSTCHECK 復旧漏れにも、回帰テストを追加した。
Git の状態情報を更新し、LF 統一だけのファイルは変更一覧から除去済み。ステージング・コミットは未実施。

次の候補で必要なのは、候補データ固有の compatibility / prompt 品質の確認と、
実 frontend/browser を含む正式な十一 gate の証拠作成。今回の 802 件は active repository の
開発用回帰検証であり、q87 や新しい V150 候補の昇格判定には代用しない。
