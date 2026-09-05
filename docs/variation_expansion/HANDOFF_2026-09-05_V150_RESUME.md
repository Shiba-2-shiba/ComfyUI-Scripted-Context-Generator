# V150 引き継ぎ — 2026-09-05 チャット終了時点

## 最初に読むこと

**ユーザーの依頼で作業を停止した。V150の本体反映は未実施。完了と扱わない。**

- リポジトリ: `C:\Users\inott\Downloads\ComfyUI-Scripted-Context-Generator`
- フロントエンド: `C:\Users\inott\Downloads\ComfyUI_frontend`
- activeは **120 subjects / 90 locations / 5,806 rows / 103,212 base variations** のまま。
- 必須の到達値は **135 / 109 / 8,227 / 150,184**。候補で実測済み。
- ユーザーは「**一貫性を非回帰の保護項目に変更する**」と明示的に承認済み。再承認は不要。
- 直前の候補は品質・11ゲートを通過したが、昇格時の成果物形式の不一致を修正したため、**修正後の再検証が残っている**。
- 本番データへのapply、commit、stageは実施していない。多数の変更・新規ファイルを維持すること。
- この文書が現在の入口。Q87とREADME/tasks/progressの旧状況は履歴として読む。

停止時のactive source hash:

`2419bb4ef2498dc850cc6f7b185146232f3beb90f19cca1028c573ca23bbdf6e`

HEAD: `b4170ed1638f202d6fac781eb5bf711c6a86ecde`。Git indexは未stage。

## 停止した処理と再開位置

最新authoring:

`docs/variation_expansion/experiments/v150-release-20260905/`

これは冗長さ修正済みauthoringを新しい実験IDへコピーし、現行baselineに結び直したもの。
subject、location、全380 action、互換性、背景修正は直前の合格候補と同じ。

最後に動かしていたコマンド:

```powershell
python tools/prepare_variation_quality_evaluation.py --experiment-dir docs/variation_expansion/experiments/v150-release-20260905 --output-root assets/results/v150-release-20260905-final --stage prepare
```

ユーザーの終了依頼後、実行セッションへCtrl-Cを送り停止した。終了コード1を確認し、
残存pythonプロセスがないことを確認した。停止位置は `materialize calibration` 後の `plan-coverage`。

- 部分成果物: `assets/results/v150-release-20260905-final/`
- ログ: `assets/results/v150-release-final-freeze.log`
- `calibration/`、`logs/`、`coverage-contract.json`のみ。**完成したsnapshot/evidenceとして使わない。**
- その一つ前の `assets/results/v150-release-20260905/` も途中停止。`superseded.json`あり。
- 再開時は既存出力を上書きせず、新しい出力ディレクトリでprepareから実行する。
- authoringは再コピー不要。protected baselineが変わっていなければ上記実験をそのまま使える。

OMXは `.omx/state/ralph-state.json` を非active/cancelledにした。これはユーザー中断であり、
V150完了ではない。MCP stateは以前からTransport closedのため、状態ファイルで代替している。
計画は `.omx/plans/prd-v150-completion.md` と `.omx/plans/test-spec-v150-completion.md` に保存済み。

## 承認済みの品質契約

新規 **v7** のみで、一貫性を改善必須から非回帰の保護項目へ変更した。

- 改善必須: naturalness / image_prompt_suitability。
- 非回帰: consistency / protagonist_clarity / redundancy。
- diversityはcurrent-source corpus confirmationで評価。
- 改善項目: 評価可能36票以上、方向票20票以上、改善支持率65%以上、lane方向一致。
- 非回帰項目: 評価可能36票以上、悪化率10%以下。
- 候補だけの重大欠陥0件、独立2名×20組、固定64+16、3目的×256、11ゲートは維持。
- 旧v4/v5/v6判定は変更しない。失敗したレビューの投票を編集・再解釈しない。

実装:

- `vocab/data/variation_semantic_review_policy_v4.json`（内側の契約がv7）
- `tools/semantic_review_contract.py`
- semantic comparison / blind builder / aggregator / promote check / verificationのschema対応
- `assets/test_variation_semantic_review_v7.py`
- 承認記録: `CONSISTENCY_SCOPE_PROPOSAL_2026-09-05.md`

## 実施した主な修正

### 検証・再現性・作業コスト

- READMEと500k手順を縮約。数値/hash/定型検証は既存CLIに任せ、通常の修正ごとに会議や計画を増やさない方針。
- confirmationのseed新規作成時の重複走査を除去。生成後の再確認は維持。
- `.gitattributes`でLFを明示。元々差分のなかった831ファイルをGitと同じLFへ戻した。
- Windows Git indexの見かけだけの変更は、内容差分のないパスだけ `git update-index --refresh -- <paths>` で解消した。stageはしていない。
- 過去の120/90/5806算術テストを `assets/fixtures/variation_baseline/` と `assets/variation_test_fixtures.py` へ隔離。実候補の整合性チェックは実候補データのまま。
- snapshotへ必要なテスト/設定/限定docsをコピーし、`.verification-inputs.json`とcontent hashで拘束。過去のmarkerなし契約は維持。
- UTF-8子プロセス、実import sentinel、候補root/source/contentの実行前後一致を検証。
- `tools/run_variation_verification.py`は6 Pythonゲートと実Vitest/Playwright JSON、直接成果物のbindingを収集。成功結果は実行記録から生成し、捏造しない。
- `tools/prepare_variation_candidate.py`と`tools/prepare_variation_quality_evaluation.py`で、実authoringから新しいprospective実験を準備する。古いreceiptを新実験の合格証拠にしない。
- prospective quality contract v2で、実coverage snapshot、実witness replay、実prompt corpusと固定cohortを拘束。

### データ・プロンプト生成

- materializerが元のprompt-only pairとCSV98行を失う問題を修正。元の104 baseline promptを保持する`baseline_prompt_mode="active"`を追加し、CSVを再生成して完全一致させた。
- 11 subjectのcostume `casual`を既存の`street_casual`へ修正。禁止背景表現を除去。
- `character_service.py`でstreet_casualの代表をstreet girlにし、新規nurseがRin/Zaraの名前解決を奪う問題を修正。明示nurseは維持。
- 衣装のintrinsic materialと汎用materialの二重表現を除去。同じRNG drawを消費する。
- reading/inspecting等と競合する視線garnishを抑制。
- 19場所の長い環境ラベルを短くし、設備名やreadiness等の重複をbackgroundの役割ごとに整理。必要な情報量・alias・件数・全380 actionsを保持。
- `prompt_renderer.py`で、行動/視線が既に注意の向きを表す場合だけ、任意語尾 `, her attention fixed on it` を省く。テンプレート選択・RNG・姿勢・気分は維持。報告された元入力の再現でその語尾だけが消えることを確認。
- 最後のrenderer修正は52関連テストと独立レビュー42テストで成功。背景authoringは3テスト成功。

### フロントエンド・実ブラウザ

- supplied frontendでVitest4件、Chromeで実workflow import/save/reload/UI reopenの2件を実行できるよう修正。
- 古いCSS依存の大きなテストを既存ComfyPage fixtureへ整理。全link tupleとcustom node widget/input/outputを比較。
- workflowのContextGarnish widgetを `[0,3,"random"]` から `[0,"fixed",3,"random"]` に修正。欠けていたseed controlの位置を直し、seed0/max_items3/emotionrandomを保持。
- frontendのdevtoolsを隔離ComfyUIへmountし、その実ファイルhashとfrontend revisionを保存。
- `-TestResultPath` / `-SourceSentinelPath`で実結果とロード元を保存。supplied `frontend/dist`をserveする。
- frontend typecheckも成功済み。古いprobeによる再syncで修正済みTSを上書きしないこと。

### 昇格処理と最後に直した不一致

- `apply_promotion(..., postcheck=...)`で、apply後の実確認をlock・rollbackの内側で実行。非pass/例外はrollback、無関係なsource mutationはRECOVERY_REQUIRED。
- activeのcontent検証に、snapshotのsupport manifestを仮想的に使用。markerをactiveへコピーしない。復旧時もjournal内の固定manifestを使用。
- stagingを`shutil.copytree(active)`から既存`_copy_filtered_source`へ変更。.git、巨大results、browser junction再帰をコピーしない。
- **最新変更1**: `compare_prompt_quality.py`は、repo内へ解決される絶対automatic comparison pathも受理。repo外・`..`・hash不一致は拒否。
- **最新変更2**: 実semantic比較はgeneric `status/verdict`を出さず`automatic_comparison_verdict`を持つ。promoterをこの実形式へ対応。
- ただし`status/verdict/quality_verdict/validation_verdict`が存在する場合は、**すべて**成功値の文字列でなければ拒否。fail/unknown/nullをautomatic passで隠せない。4項目ともない場合だけfallbackする。後段のautomatic hash/DAGの合格要求も維持。
- 最新変更の関連36件＋追加1件成功。独立レビュー承認済み。
- 保存済み実成果物で`promote_check=promote, failures=[]`を確認。凍結baseline-rootをactive代わりにした**読み取り専用診断preflight**も27ファイルでpass。実activeへのpreflight/apply成功を意味しない。

## 品質評価の履歴（改変しない）

| 出力ディレクトリ（assets/results以下） | 結果・扱い |
| --- | --- |
| `v150-final-evaluation-02` | 旧v6レビューで一貫性の改善証拠不足。独立レビューは実投票。不合格のまま保存。 |
| `v150-final-v7-release` | 859 Python/4 frontend/2 browser、自動比較pass。v7レビューで冗長さ7/40悪化（17.5%）のため不合格。 |
| `v150-v7-redundancy-evaluation` | 冗長さ修正後。**865 Python/4 frontend/2 browser、実独立レビュー、3×256確認、11ゲートすべてpass**。最後の昇格tool修正前なので、現コードの証拠には再利用不可。 |
| `v150-release-20260905` | 途中停止。superseded。 |
| `v150-release-20260905-final` | ユーザーの終了依頼でprepare途中停止。再開時は新しい出力へ生成。 |

最後に全ゲート合格した`v150-v7-redundancy-evaluation/review.json`:

- naturalness: 改善31 / 悪化0 / 同等9
- image_prompt_suitability: 28 / 0 / 12
- consistency: 6 / 0 / 34
- redundancy: 18 / 0 / 22
- protagonist_clarity: 0 / 0 / 40
- 候補だけの重大欠陥0。
- 実reviewerは別contextのgpt-6-astra、`/root/v150_remediation_blind_1`と`..._2`。
- 候補source: `2b9452465b34e8fed20052c0c86f9ab1a0220fb79e1ba73887163c4cdcf73ac8`
- 候補content: `d0cfcc67185134b59cb725c5ba01444420fdb08a683088bbf5c13fdd25d91af7`
- 合格review原本はこの旧試行だけ`OUT/review.json`。診断用にkey/lane原本5ファイルの同一bytesコピーをOUT直下にも置いた。
- **今後のdriverは`OUT/review/review.json`を出力**し、key/laneと同じdirectoryにする。これがpromote-checkの期待配置。

## 再開手順

1. Git差分、active shape、上記最新修正を維持。必要な追加修正がなければコードを固定。
2. 新しい出力でprepare。例（未使用であることを確認）:

```powershell
python tools/prepare_variation_quality_evaluation.py --experiment-dir docs/variation_expansion/experiments/v150-release-20260905 --output-root assets/results/v150-release-20260905-resume --stage prepare
```

3. 6 Pythonゲートと実外部ゲートを独立に実行。出力ログを保存する。

```powershell
python tools/run_variation_verification.py --candidate-root assets/results/v150-release-20260905-resume/quality/candidate-root --output-dir assets/results/v150-release-20260905-resume/evidence --gate all
python assets/results/run_v150_external_gates.py assets/results/v150-release-20260905-resume
```

4. 自動比較・semantic比較と盲検入力を生成。

```powershell
python tools/prepare_variation_quality_evaluation.py --experiment-dir docs/variation_expansion/experiments/v150-release-20260905 --output-root assets/results/v150-release-20260905-resume --stage automatic
python assets/results/run_v150_semantic_evidence.py assets/results/v150-release-20260905-resume
```

5. **8実行ゲートが通ってから**、新しい独立reviewerを2名起動。`fork_turns="none"`、`model="gpt-6-astra"`。
   各reviewerには指定lane JSONだけを渡し、assignment key・他lane・旧投票・候補実装を見せない。
   20組×6次元を実際に評価し、equal/abstainも正直に使う。通過を指示しない。
   出力は`review/lane-1-result.json` / `lane-2-result.json`。
   result_contractのexact fieldsに従う。`rubric_hash`と`review_prompt_hash`はinputのreview_prompt_hash、
   input_hashはlaneの実bytes SHA256。votesの余分なrationaleキーは禁止。必要なら別notes.md。
   各voteは`pair_id, dimensions, hard_defects`、hard defectはclosed codeとevidence。

```powershell
python assets/results/run_v150_review_aggregate.py assets/results/v150-release-20260905-resume
```

6. reviewがpassのときだけconfirmation。失敗なら本当の原因を直し、新しいfreeze/evidenceへ進む。

```powershell
python assets/results/run_v150_confirmation.py assets/results/v150-release-20260905-resume
```

7. 11項目をbindingし、実promote-check/preflightを実行。

```powershell
python tools/build_prompt_quality_verification.py --comparison assets/results/v150-release-20260905-resume/semantic-comparison.json --review assets/results/v150-release-20260905-resume/review/review.json --evidence-dir assets/results/v150-release-20260905-resume/evidence --output assets/results/v150-release-20260905-resume/verification-receipt.json --candidate-root assets/results/v150-release-20260905-resume/quality/candidate-root
python assets/results/apply_v150_release.py assets/results/v150-release-20260905-resume
```

8. 新しい証拠とpreflightの独立した読み取りレビュー後、rollback保護付きでapply。

```powershell
python assets/results/apply_v150_release.py assets/results/v150-release-20260905-resume --apply
```

`apply_v150_release.py`は、actual promote-check→preflight→apply→5データチェック→exact件数→
skipなし全unittest→固定80出力のcandidateとのbytes一致→実frontend/browserとactive sentinel確認を行う。
各summaryは既存閾値で検証し、report/log/sentinelのhashを保存。**終端PROMOTEDとpostcheck passまで完了を宣言しない。**
失敗時はjournalとrollback receiptを読む。RECOVERY_REQUIREDで無理に再applyしない。

9. 完了後にREADME/tasks/progressと新handoffを更新。docs更新後のproduction source hashは確認する。
   凍結receiptは検証時点の証拠として保持し、docsを含むcontent hashが後から変わったのに同一と主張しない。
   commitはユーザーが要求した場合のみ。行うならAGENTSのLore trailersに従う。

## 実行環境・落とし穴

- System Python: `C:\Users\inott\AppData\Local\Programs\Python\Python312\python.exe`
- ComfyUI: `C:\Users\inott\AppData\Local\Programs\ComfyUI\resources\ComfyUI`
- Desktop `.venv` PythonはSSLで`OPENSSL_Applink` crash。**System Pythonを使う**。TLS無効化やDesktop環境の改変は不要。
- Frontend version1.54.4 / HEAD `538b144c591b06e137bce6d4cff812cf1a1d0588`。
- 既存依存はpnpm11.13.1でfrozen install済み。新規dependency追加はしていない。
- Node25.9: `C:\Users\inott\AppData\Local\npm-cache\_npx\1b904144cb84343d\node_modules\node\bin\node.exe`。
  Global Node26はfrontend engine範囲外。driverはNode25をPATH先頭にする。
- `NODE_OPTIONS=--use-system-ca --no-experimental-webstorage --max-old-space-size=8192`
- Frontend distはbuild済み。必要時だけ既存vite configで再build。
- `VSCG_BROWSER_CHANNEL=chrome`、port8191、headless。browser runnerは終了時に隔離backendを終了する。
- 外部frontendへのtest sync、隔離backend/browser起動、repo外seed保存、parentへのstage生成はsandbox外権限が必要。
  依頼範囲としては承認済み。ツールの権限要求が必要な場合だけ具体的なコマンドへescalateする。
- `assets/calc_variations.py`はcwdを使う。候補を測る場合は**cwdをcandidate-rootにする**。
  active cwdから候補scriptの絶対パスだけを起動するとactive件数になる。
- `.verification-inputs.json`、候補source、raw reports、review bytesを生成後に編集しない。
- 作業用driver5本は **`assets/results/`配下のignoredファイル**。次のチャットも同じworkspaceを使い、削除しない:
  `run_v150_external_gates.py`, `run_v150_semantic_evidence.py`, `run_v150_review_aggregate.py`,
  `run_v150_confirmation.py`, `apply_v150_release.py`。
- これらdriverの最新内容は修正・独立レビュー済み。成果物producerの実コマンド/cwd/前後hashを保存する。
- confirmation seedはrepo外の `Downloads/<experiment-id>-confirmation-seeds.json`。
  過去の宣言ファイルすべてと固定/既知cohortを除外し、候補identityに固定する。
  既存seedfileに宣言がない、または同じ実験IDのcandidateが変わっている場合は拒否する。
- 既に露出したholdoutは `Downloads/v150-v7-redundancy-remediation-20260905-confirmation-seeds.json`。
  新しいrelease実験でこれを未使用seedとして再利用しない。driverが除外する。
- native specialist roleの一部は利用不能なgpt-5.4を指定する。通常subagentはmodel継承のdefaultを使う。
  正式blind reviewerは上記の新規gpt-6-astra/forkなし。過去reviewerのcontextを再利用しない。

## 残る作業・リスク

残る作業は、**最後の昇格tool修正を含む新しい全検証と、実activeへの反映・反映後確認**。
最新コード全体の865件超の全unittest、最新snapshotの外部ゲート/品質レビュー/confirmationは未完了。
直前の865件合格と品質合格を、最新sourceの合格として扱わない。

現時点で独立レビューに残る既知の阻害バグはない。ただし実transactionはまだ一度も完了していないため、
その成功を仮定しない。ユーザーの停止依頼により中断しただけで、追加の仕様確認待ちではない。
