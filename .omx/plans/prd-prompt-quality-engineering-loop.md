# Prompt Quality Engineering Loop リファクタリング計画

Status: Locally approved by Architect and Critic; implementation not started
Planning mode: RALPLAN-DR short consensus
Supersedes: `prd-female-protagonist-natural-prompts.md`
Scope: 計画のみ。実装は別の承認済み実行レーンで行う。

## 1. 提案の結論

提案されたループは組み込める。既存の `tools/analyze_context_workflow_diversity.py` は、`ComfyUI-workflow-context.json` を読み、実際のnode classをworkflow順に実行し、prompt・context・execution traceを収集している。この実行経路を共通ライブラリへ抽出し、次の反復を標準開発プロセスにする。

```text
workflow同等経路で80件生成
  → 自動品質解析
  → evidence付きissue ranking
  → 1つの改善仮説を選択
  → 回帰テストを追加
  → 小さいコード/データ修正
  → 同一seed群でA/B再生成
  → 改善ならpromote、悪化ならpatchを戻す
  → 次の仮説へ
```

Pythonスクリプト自身にはrepository codeを自己書換えさせない。生成・解析・比較・判定は決定論的ツールが担当し、修正は計画を読んだcoding agentが明示的なissue dossierとテストを根拠に行う。

## 2. 要求概要

- 主役はsupported natural modeで単一の女性とする。
- subject、character、clothing、location、action、emotion、garnishにhard contradictionがない。
- promptは自然な英語文で、断片、冗長な言い直し、タグ列化を減らす。
- semantic、scene、lexical、syntactic diversityを別々に改善する。
- 50–100件の実サンプルを毎iteration評価し、改善を数値とpaired reviewで確認する。
- seed再現性、public node I/O、context JSON、workflow round-tripを維持する。

## 3. RALPLAN-DR

### Principles

1. **同じworkflow経路を測る** — 評価専用の簡略pipelineを作らず、ComfyUI workflowが呼ぶnode classとwidget値を使う。
2. **一度に1仮説だけ変える** — consistency、naturalness、diversityを同じpatchで混在させない。
3. **固定seedと探索seedを分ける** — A/B比較の再現性と、未知の失敗を探すランダム性を両立する。
4. **hard gateを改善値より優先する** — diversityが増えても女性主体、一貫性、決定性、互換性が悪化した変更は採用しない。
5. **改善が証明できない変更はpromoteしない** — ファイル整理や抽象化だけの変更も、loop指標または保守性contractで根拠を持つ。

### Decision drivers

1. 実際のprompt出力に対する変更効果を短いcycleで観測できること。
2. 乱数差と実装差を分離し、悪化時に原因とpatchを特定できること。
3. 既存の豊富なunit test・audit・workflow fixtureを再利用できること。

### Options

#### Option A: 大規模設計変更を先に完了して最後に評価

- 長所: 理想的な内部構造を一括設計できる。
- 短所: 品質効果が遅く、複数変更のどれが改善・悪化要因か分離できない。

#### Option B: 語彙追加と目視確認を反復

- 長所: 始めやすい。
- 短所: seed差、選択bias、矛盾率、重複率を定量比較できず、主観的な修正になりやすい。

#### Option C: workflow-faithful evaluation loop（採用）

- 長所: 実際のnode経路、固定seed A/B、trace、統計gateを組み合わせられる。小差分で進められる。
- 短所: 初期にrunner、artifact schema、quality policyを整備する必要がある。80件だけでは稀な問題を完全には捉えられない。

#### Option D: スクリプトが解析からsource code修正まで自動実行

- 長所: 無人反復が可能。
- 短所: 誤ったmetric最適化、広範囲な自己変更、テストの形骸化が起きやすい。採用しない。

## 4. 1 iterationの標準契約

### 4.1 Generate

既定sample数は80件とする。

- control cohort: 64件。version管理された固定seedと固定workflowを使用し、全iterationで同一。
- exploration cohort: 16件。`experiment_seed + iteration_id` から決定論的に派生し、iterationごとに入れ替える。
- promotion comparisonはcontrol 64件を主判定とし、exploration 16件は新規issue発見とstop判定に使う。
- experiment manifestはtarget metric scopeを `control64` / `paired80` / `repro_cohort` のいずれかに固定する。通常はcontrol64、exploration由来issueはrare-event contractを使う。
- 必要に応じて `--samples 50..100` を許すが、正式promotionは80件未満では行わない。

canonical recordに次を保存する。

- workflow hash、source tree hash、candidate patch hash、policy/analyzer version
- run seedと各nodeのresolved seed
- raw prompt、cleaned prompt、final context JSON
- node execution traceとDebugInfo
- pipeline/config/data schema version
- context JSON byte size

非決定情報は分離する。

- `run-manifest.json`: run id、iteration、timestamp、host、dirty-state marker、artifact hashes
- `telemetry.json`: node/run duration、resource measurement
- byte-identical gateはcanonical `records.jsonl` とdeterministic `metrics.json` だけを対象にする。
- telemetryは同一性判定に使わず、許容差を持つ性能比較だけに使う。

### 4.2 Analyze

自動解析を5群に分ける。

1. Identity
   - supported inputにおけるsingle female coverage
   - male pronoun、other-person、subject drift、duplicate protagonist mention
2. Consistency
   - location/action/object conflict
   - clothing/TPO/weather conflict
   - mood/action/garnish conflict
   - hard/soft constraint reason codes
3. Naturalness proxy
   - sentence fragment、dangling modifier、重複主語
   - repeated 2/3/4-gram、comma density、punctuation anomaly
   - semantic familyの同一prompt内重複
   - prompt length p50/p95
4. Diversity
   - exact/normalized unique ratio
   - character/location/action/object/mood signature coverage
   - verb/object/template/syntax/semantic-family entropy
   - top-1/top-5 concentrationとfallback rate
5. Runtime/compatibility
   - deterministic replay mismatch
   - warning/error count
   - context JSON p50/p95/max bytes
   - widget/workflow/data generation checks

### 4.3 Diagnose

解析器は `issues.json` を出力し、各issueを以下でrankする。

```json
{
  "issue_code": "duplicate_subject_action",
  "severity": "high",
  "frequency": 0.1375,
  "confidence": 0.92,
  "affected_seeds": [3, 18, 42],
  "trace_nodes": ["ContextGarnish", "ContextPromptBuilder"],
  "suspected_owners": ["vocab/garnish/logic.py", "prompt_renderer.py"],
  "evidence": ["..."],
  "recommended_test_surface": "assets/test_prompt_renderer.py"
}
```

coding agentは上位issueから1件を選び、experiment manifestへ次を固定してから編集する。

- hypothesis
- target metric
- guard metrics
- owned files
- expected behavior change
- expected unchanged behavior
- new/updated regression test
- rollback condition

### 4.4 Modify

- 修正前に再現testを追加する。
- 1 iterationは1 smell / 1 behavior hypothesisに限定する。
- 新依存は追加しない。
- data変更ではauthoring sourceを編集し、generated runtime fileは既存builderで再生成する。
- public node I/O、widget順、legacy contextを変える修正は通常loopから除外し、別contract gateへ送る。

### 4.5 Re-evaluate and decide

同一control cohortをbefore/afterで生成し、seed単位paired comparisonを行う。

Promotion条件:

- hard gatesがすべて成功。
- target defect countが2件以上減る、またはtarget rateが相対10%以上改善する。
- targeted diversity metricの場合、entropyまたはcoverageが相対5%以上改善する。
- guard metricの悪化が絶対2 percentage points以内で、かつ既存policy thresholdを超えない。
- exact duplicate率とfallback rateが悪化しない。
- Python regression suiteとdata checksが成功。
- 20組のstratified paired sampleを2つの独立review laneが評価し、自然さ/一貫性の改善支持が65%以上、明確な悪化判定が10%以下。

Qualitative aggregation:

- 2 laneの各reviewerが同じ20 pairすべてをblind評価し、最大40 lane-pair votes / dimensionとする。
- A/B sideはlaneごとに決定論的にrandomizeし、candidate sideと実装情報を隠す。
- `consistency` と `naturalness` は各dimension別に、non-abstain voteの65%以上が改善支持、全valid voteの10%以下が悪化判定であることを必須とする。
- `protagonist_clarity` と `image_prompt_suitability` は悪化vote 10%以下かつhard defect 0を必須とする。
- tie/abstainは分母から除外するが、required dimensionごとに36 valid votes未満ならreview failureとする。
- 2 laneのdimension別多数方向が一致しない場合もreview failureとし、sourceを変えず新review transitionで再審査する。
- rubric version、review prompt hash、reviewer type/model version、side assignment、raw voteを保存する。reviewer不足、hash欠落、invalid voteはpromotion failureとする。

Reject条件:

- hard contradiction、determinism mismatch、public contract regressionが1件でも発生。
- target improvementが最小効果量に届かない。
- 自動metricは改善してもpaired reviewで属性保持、自然さ、画像prompt適合性が悪化。

Reject時は隔離candidate snapshotを破棄対象としてmarkし、artifact summaryとhashは失敗例として保持する。共有worktreeへreverse patch、checkout、resetは行わない。`promote-check` はverdict artifactだけを生成し、git/sourceを変更しない。

## 5. 成果物とコマンド設計

### 5.1 再利用・抽出する既存実装

- `tools/analyze_context_workflow_diversity.py`
  - seed導出、link/widget解決、現行record/summary fixtureを再利用する。
  - 現在の `execute_custom_workflow()` / `build_run_record()` はstrict runnerとして直接再利用しない。
  - 新runnerを呼ぶcompatibility adapterへ変更し、既存report shapeを維持する。
- `workflow_widget_validation.py`
  - widget値、link、seed controlの解決を唯一のcontractとして利用。
- `tools/audit_prompt_repetition.py`
  - repetition、semantic family集計を共通analyzerへ移植または関数再利用。
- `tools/audit_template_diversity.py`
- `tools/run_bias_audit.py`
- `core/solo_safety.py`
- `rules/consistency_rules.json`

### 5.2 新規または整理するtool surface

- `tools/workflow_prompt_runner.py`
  - supported-workflow profileで許可node、必須output、final context/raw/cleaned promptのnode-id/slot selectorを宣言する。
  - configured output node/slotから逆向きにancestor closureを計算し、そのclosureだけを実行する。
  - `PreviewAny` のようなclosure外external terminalはprofileの `excluded_terminal_nodes` にtype/id/reasonを明示し、recordへ残す。closure内unknown nodeはfailureとする。
  - link DAGをtopological executionし、workflow `order` は同順位のstable tie-breakにだけ使う。
  - unknown/unsupported/duplicate ambiguous output/missing upstream/cycleを黙ってskipせずstable failure envelopeで終了する。
  - workflow実行とcanonical record生成だけを担当する。
- `tools/analyze_prompt_quality.py`
  - recordsからmetricsとissuesを生成。source codeは変更しない。
- `tools/compare_prompt_quality.py`
  - before/afterのseed-paired comparisonとpromotion判定。
- `tools/prompt_quality_loop.py`
  - `baseline`、`generate`、`analyze`、`compare`、`promote-check` を統合するCLI。
- `vocab/data/prompt_quality_policy.json`
  - cohort、hard gate、effect size、guard threshold、review条件をversion管理。
- `verification/environment.json`
  - L0から使うComfyUI / ComfyUI_frontend commit、配置、依存復元、実行command、verification-only sink versionを固定。
- `verification/comfyui_sink/`
  - test ComfyUI instanceだけに追加するsink。final context/raw/cleaned promptを取得可能にし、product `NODE_CLASS_MAPPINGS` には登録しない。
- `verification/fixtures/prompt_parity_workflow.json`
  - sink接続済み8-seed parity専用workflow。
- `assets/fixtures/prompt_quality_control_seeds.json`
  - control cohortと層化条件を固定。
- `assets/test_prompt_quality_*.py`
  - runner、analyzer、comparison、policy schemaのunit/integration tests。
- `docs/prompt_quality/ledger.jsonl`
  - promoted/rejected/aborted iterationのstate、source/cohort/artifact hash、verdict summaryをappend-onlyで保持する。raw artifactsはignore可能だが、判断証拠のhashとsummaryはtrackする。

想定CLI:

```powershell
python tools/prompt_quality_loop.py baseline --workflow ComfyUI-workflow-context.json --samples 80
python tools/prompt_quality_loop.py analyze --run-id <baseline-run-id>
python tools/prompt_quality_loop.py generate --experiment <experiment.json>
python tools/prompt_quality_loop.py compare --before <baseline-run-id> --after <candidate-run-id>
python tools/prompt_quality_loop.py promote-check --comparison <comparison.json>
```

### 5.3 Artifact layout

```text
assets/results/prompt_quality_loop/<experiment-id>/
  experiment.json
  iteration-001/
    state/
      0001-hypothesis-locked.json
      0002-baseline-ready.json
    incumbent/
      run-manifest.json
      records.jsonl
      metrics.json
      issues.json
      telemetry.json
    candidate/
      run-manifest.json
      records.jsonl
      metrics.json
      issues.json
      telemetry.json
    comparison.json
    review.json
    summary.md
```

`assets/results/` はgit ignore対象とする。正式なpolicy、control seeds、承認済みthreshold、append-only ledger、各iteration summary/artifact hashだけをtrackする。

Canonical artifact formatはschema version付きJSON/JSONL、UTF-8 without BOM、LF、object key昇順、余分な空白なし、末尾LFありとし、SHA-256でhashする。浮動小数の丸め桁はmetric schemaごとに固定する。

### 5.4 Iteration transactionとsource isolation

state machine:

```text
DRAFT
→ HYPOTHESIS_LOCKED
→ BASELINE_READY
→ CANDIDATE_SNAPSHOT_LOCKED
→ GENERATED
→ ANALYZED
→ COMPARED
→ REVIEWED
→ VERIFIED
→ PROMOTED | REJECTED | ABORTED
```

- hypothesis、target/guard metrics、owned files、policy/cohort versionはsource編集前の `HYPOTHESIS_LOCKED` でimmutableにする。
- 各transitionはprevious state、baseline source tree hash、candidate source tree/patch hash、workflow/config/policy/runner/analyzer/cohort/artifact hashesを検証し、append-only `state/<sequence>-<transition-id>.json` としてcommitする。`state.jsonl` は生成可能なread-only viewでありsource of truthにしない。
- main/shared worktreeはexperiment中read-onlyとする。candidate修正はworkspace-ownedのiteration専用git worktreeまたは内容hashを固定した隔離snapshotで行う。
- incumbentもcandidateも隔離snapshotから生成し、candidate patch hashがlock後に変わった場合はABORTする。
- dirty baselineはcommit hashだけで表さない。tracked tree、binary diff、対象untracked filesを含むsource snapshot manifestでhash化できない場合はobjectiveを開始しない。
- PROMOTEDはartifact verdictでありmainへのpatch適用ではない。実sourceへの統合は別のreviewed controller/agent actionとする。
- REJECTED snapshotは次baselineとして参照できない。

Atomicity/resume contract:

- experimentごとにOS-level exclusive single-writer lockを取得する。lock owner、host、process、transition idを記録し、取得失敗は非ゼロ終了する。
- artifactは同一volumeの `.staging/<transition-id>/` にcanonical形式で書き、全hash検証後に最終pathへatomic renameする。
- state recordのatomic renameをtransition commit markerとする。commit recordのないorphan artifactは未commitとして無視し、`recover` commandがhash確認後にABORT記録または隔離する。
- transition idをidempotency keyとし、同一id/同一payloadは既存結果を返し、同一id/異なるpayloadは拒否する。
- 1 transition 1 canonical JSON fileとし、partial JSONL tailを持たない。破損JSON、sequence gap、hash mismatchは自動resumeせずABORT/recovery対象にする。
- source manifestはroot runtime `.py`、`core/`、`pipeline/`、`vocab/`、`rules/`、`tools/`、`assets/test_*.py`、workflow/verification fixturesを含む。`.git/`、`.omx/`、`assets/results/`、cache/bytecode、外部checkoutを除外し、規則自体をversion/hash化する。
- incumbent/candidate comparisonは同一policy、runner、analyzer、workflow profile/versionを必須とする。いずれかが変わればcomparisonを拒否し、新versionでincumbentを再baselineする。

### 5.5 CLI write-scope

- loop CLIの書込先は指定experiment artifact rootだけとする。
- CLIはgit apply/revert/commit、source formatter、data builder、agent launch、source editを行わない。
- generate/analyze/compare/promote-check前後でprotected roots (`core/`, `pipeline/`, `vocab/`, root runtime modules, tests, workflow fixtures) のcontent hashが不変であることを検証する。
- candidate patch、authoring data変更、runtime JSON再生成、隔離snapshotの作成/廃棄はcoding-agent/controller責務とする。

## 6. 導入フェーズ

### L0: Loop harnessをbehavior-neutralに構築

- supported-workflow profile、DAG execution、node-id/slot output selector、stable failure envelopeを持つstrict runnerを作る。
- 現行workflow diversity analyzerはstrict runnerのcompatibility adapterへ変更する。
- 現行 `analyze_context_workflow_diversity.py` の出力を維持するadapterを残す。
- canonical artifact / run manifest / telemetry分離、80件生成、deterministic replayを実装する。
- code modification機能は実装しない。
- `verification/environment.json`、verification-only sink、parity workflow fixtureをL0成果物として追加する。sinkはtest ComfyUIのcustom-node pathにだけ配置し、product registryへ露出しない。

Exit:

- 同一source/workflow/seed/configでcanonical recordsとdeterministic metricsがbyte-identical。
- 既存workflow diversity testが回帰しない。
- current full-flow promptとrunnerの同seed出力が一致。
- unknown node、cycle、missing upstream、ambiguous outputをstable failureとして検出する。

L0 parity gate:

- pinned実ComfyUI環境にverification専用sinkをtest-onlyで登録し、8件のsentinel seedでraw prompt、cleaned prompt、final contextを取得する。
- strict in-process runnerと実ComfyUIのcanonical outputsを照合する。
- parityを確認できない場合、品質iterationを開始しない。
- environment checkout未配置、commit不一致、sink registration失敗、required output欠落はいずれもL0 failureとする。

### L1: Quality analyzerとbaseline contract

- identity、consistency、naturalness proxy、diversity、runtime analyzerを追加する。
- 既存auditロジックを重複実装せず純粋関数として再利用する。
- baselineを取得し、`prompt_quality_policy.json` の閾値をレビューして凍結する。
- baseline contractが承認されるまでbehavior変更へ進まない。
- generic promotion automationの前に、source-isolatedなmanual agent-driven experimentを2件実施し、metric precision、artifact負荷、review負荷を検証する。

Exit:

- 全issueがaffected seedとtrace evidenceを持つ。
- analyzer自身のprecision fixtureがある。
- hard gate、effect size、guard thresholdがversion管理される。
- 2件のmanual experimentでstate/source/cohort/artifact hashがledgerから再構成できる。

### L2: 女性主人公・identity loop

優先issue:

- profile/prompts/default入力のsingle female coverage
- subject/pronoun drift
- other-person / solo conflict
- duplicate protagonist mention

想定owner:

- `pipeline/character_profile_pipeline.py`
- `character_service.py`
- `core/solo_safety.py`
- `core/context_state.py`

旧explicit JSONは読み込み・round-tripを維持する。natural modeのcoverage分母はsupported single-female inputに限定する。

### L3: Semantic consistency loop

issue頻度順に、location/action/object、clothing/TPO/weather、mood/action/garnishを1 domainずつ改善する。万能evaluatorは作らず、domain ruleは既存selectorに残し、共通reason-code/report contractだけを共有する。

想定owner:

- `pipeline/action_generator.py`
- `pipeline/location_builder.py`
- `pipeline/clothing_candidate_selector.py`
- `vocab/garnish/logic.py`
- semantic profile JSON群

### L4: Natural-language loop

既存action slotを `ActionFrame` へ型昇格し、並列生成系を作らない。`composition_mode=True` をopt-in experiment surfaceとしてcontent plan、clause order、lexical choice、surface realizationを1層ずつ改善する。

- `composition_mode=False` はlegacy controlとして維持。
- base workflowのFalseは変更しない。L4 experimentはprofileでnode-id/input-nameを指定したimmutable override (`composition_mode=True`) を使う。base workflow hashとoverride canonical hashの組をeffective workflow hashとし、manifest lock後の変更を拒否する。
- template/syntax selectionはPromptBuilderがcontextを返さないため永続memoryにせず、named seed分布で評価。
- `PromptCleaner` は意味修復ではなく軽微なnormalizeへ縮小する。

### L5: Diversity loop

- semantic、scene、lexical、syntacticのうち、metrics上の最弱層を1 iterationずつ改善する。
- 語彙追加前にcanonical concept、semantic family、compatibility tag、rarity weightを要求する。
- source action poolとruntime JSON、variation scope、compatibility CSVを同期検証する。
- 制約強化によるcandidate exhaustion/fallback集中をguard metricにする。

### L6: Adoption and workflow gate

- opt-in natural modeが全promotion gateを満たした後、READMEとsample workflowを `composition_mode=True` 推奨へ更新する。
- widget default変更は別のexpected-diffとしてfrontend/browser round-tripを必須にする。
- explicit Falseはlegacy rollbackとして保持する。

E2E用に `verification/environment.json` を追加し、ComfyUI / ComfyUI_frontendのcommit、配置、依存復元、実行commandを固定する。依存checkoutが未配置、version不一致、test未実行の場合はL6失敗とする。

外部検証は2種類に分ける。

1. frontend compatibility: 現行Vitest/Playwright workflow round-trip。
2. execution parity: verification専用sinkを使う8-seed sentinelで実ComfyUIとstrict runnerのraw/cleaned/contextを比較。

execution parityはL0完了時、最初のpromotion前、L6で必須とする。

## 7. Loop stop conditions

1つのquality objectiveに対し最大6 iterationsとする。以下のいずれかで停止する。

- acceptance target達成。
- 2 iteration連続で最小効果量に届かない。
- 同じhard/guard regressionが2回発生。
- 修正にpublic I/O、context version、外部dependency追加が必要と判明。
- analyzer confidenceが0.8未満で、追加fixtureなしでは原因を絞れない。
- 80件で改善したが、追加256件のconfirmation batchで再現しない。

objective達成時は、control 64 + exploration 16に加えて固定256件confirmation batchを実行し、同じgateを通過して完了とする。

### Cohort lifecycle

- 各iterationでincumbentとcandidateの双方を、同じ64 control + 当該iteration固有16 explorationで生成する。
- 64 control cacheはsource/workflow/config/policy/analyzer hashが完全一致する場合だけ再利用できる。
- 16 explorationはincumbent/candidate双方で毎iteration再生成する。
- control、全iteration exploration、confirmation 256のseed集合は相互disjointにする。
- confirmationはobjective開始時baselineと最終candidateを比較し、累積target改善と全guardを確認する。
- confirmation seedはholdoutとし、途中のhypothesis選択やthreshold調整に使用しない。
- confirmation失敗時はobjectiveを停止する。同じholdoutに合わせた追加修正は禁止し、新objective/policy/cohort versionのreviewから再開する。

### Rare-event contract

- explorationでのみ見つかったissueは、そのseedと最小入力をimmutableなobjective-specific `repro_cohort` へ移し、hypothesis lock前にversion/hash化する。
- deterministic defectはbeforeで再現しafterで消失するregression fixtureをtarget proofとする。64+16と256 confirmationはhard/guard非回帰に使い、baseline event count 0を理由に無効化しない。
- statistical rare issueは最大128件の事前登録repro cohortを構成し、baselineで最低5 eventsを要求する。candidateはevent count 50%以上削減かつhard/guard非回帰を満たす。
- confirmation 256でbaseline/candidate双方が5 events以上なら同じrelative gateを適用する。最低event数に届かなければpopulation improvementは主張せず、deterministic fixture fix + global non-regressionとして記録する。
- control=0、exploration>0、confirmation=0は `rare_deterministic` verdictでのみpromotion可能で、通常のrate-improvement verdictを使わない。

## 8. Context/history size gate

SelectionMemoryを導入する場合はverb/object/locationだけを固定長にする。template/syntaxは永続化しない。`PromptContext.history` はtrace互換のため残るので、各loopでcontext JSON byte sizeを測る。

- control cohortのp95がbaselineから10%以上増えたらpromotion停止。
- max context sizeがbaselineの1.25倍を超えたらpromotion停止。
- いずれかを超える改善が必要な場合、history retention/compactionを別計画として先に実施する。

## 9. Verification gates

各candidate iteration:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest <targeted regression modules>
python tools/prompt_quality_loop.py generate --experiment <experiment.json>
python tools/prompt_quality_loop.py compare --before <baseline> --after <candidate>
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python tools/build_compatibility_review.py --check
python tools/build_action_pools.py --check
```

L6のみ追加:

- frontend Vitest schema/round-trip
- browser Playwright import/save/reload
- pinned environment manifest verification

## 10. 受け入れ基準

- runnerが実際のworkflow node class、links、widget values、seed controlを使用する。
- runnerがDAG、supported profile、node-id/slot selectorを検証し、unsupported workflowを黙って実行しない。
- 80件のbaseline/candidate比較がseed-pairedで再現可能。
- supported natural-mode outputのsingle female coverage 100%。
- hard contradiction、determinism mismatch、invalid workflow 0件。
- 各accepted iterationが事前宣言したtarget metricの最小効果量を満たす。
- guard metric、exact duplicates、fallback rate、context size gateに回帰がない。
- 2つの独立review laneによる20 paired sampleで改善支持65%以上、悪化10%以下。
- required qualitative dimensionごとに最大40 votes、最低36 valid votesを満たす。
- objective完了時の256件confirmation batchで改善が再現する。
- 全Python tests、data/source checks、必要なfrontend/browser E2Eが成功する。
- rejected patchとその失敗artifactが追跡可能で、次iterationへ混入しない。
- state/source/policy/analyzer/cohort/artifact hashからpromotion判断を再構成できる。
- loop CLI実行前後でprotected source rootsが不変。
- 8-seed実ComfyUI execution parityがL0、first promotion、L6で成功する。
- current sample workflowのclosure外 `PreviewAny` がexcluded terminalとして記録され、natural experiment overrideがeffective workflow hashに含まれる。
- transition crash/concurrency/idempotency/recovery contractが検証される。
- exploration-only deterministic issueとstatistical rare issueの両方に一意なpromotion判定がある。

## 11. Risks

| Risk | Mitigation |
|---|---|
| metric gaming | hard/guard gate、paired review、画像prompt適合性、1仮説制限 |
| 80件の過学習 | rotating exploration cohort、objective完了時256件confirmation |
| analyzer false positive | confidence、affected seed、trace evidence、precision fixture |
| 自動修正の暴走 | scriptはsource codeを書換えず、agent editとtestを分離 |
| 制約強化でdiversity低下 | survivor count、fallback、entropyを同時guard |
| random consumptionによる比較崩壊 | control seeds固定、named seed stream、pipeline version記録 |
| history/context肥大 | p95 +10%、max 1.25x gate |
| E2E環境不在 | pinned verification manifest。未実行はL6 failure |
| experiment platformの過剰構築 | strict runner/state schema後にmanual experimentを2件行い、有効性確認後だけgeneric promotionを自動化 |
| crash/二重writerでartifactとstateが乖離 | exclusive lock、staging+atomic rename、transition id、commit marker、explicit recover |

## 12. ADR

### Decision

実際のComfyUI workflow node経路を再利用し、80件の固定/探索cohortを生成・解析・比較するPrompt Quality Engineering Loopをリファクタリングの中心にする。

### Drivers

- 実出力を根拠に修正優先度を決めたい。
- 一貫性、自然さ、多様性の改善と回帰をseed-pairedで識別したい。
- 大規模な先行再設計を避け、1仮説ずつ安全に進めたい。

### Alternatives considered

- 大規模設計変更後の一括評価。
- 語彙追加と目視確認。
- source codeまで自動変更するself-editing loop。

### Why chosen

既存workflow executor、audit、testsを利用でき、変更効果と原因をiteration単位で分離できるため。

### Consequences

- 最初の成果はprompt品質変更ではなく、runner/analyzer/policy基盤になる。
- 改善速度はissueの再現性とmetric品質に依存する。
- 大きな内部設計変更もloopで必要性が証明されたものだけ実施する。

### Follow-ups

- naturalness proxyの限界をpaired reviewで補う。
- public context schema変更、history compaction、performance最適化は必要時に独立計画化する。

## 13. Execution staffing guidance

将来の承認済み実行では、`$ultragoal` をdurable ledger ownerとし、並行化する場合は `$team` を組み合わせる。

- `executor` 1名: strict DAG runner、artifact/state transaction。
- `executor` 1名: analyzer/compare CLI。
- `test-engineer` 1名: fixtures、metric tests、promotion gates。
- `executor` 1名: iterationごとの限定実装修正。runner ownerとは分離可能。
- `verifier` 1名: artifact、A/B、confirmation、E2Eの完了証拠。
- `critic` または `code-reviewer` 2 lane: paired qualitative review。実装laneと分離。

App外のtmux OMX runtimeを使う場合の将来launch hint:

```text
$ultragoal <approved plan path>
$team 3:executor "Implement the approved prompt-quality loop plan; preserve public contracts and return checkpoint evidence"
```

Teamは各laneの変更と検証証拠を返し、Ultragoalがiteration/result/confirmationをcheckpointする。`$ralph` は単一ownerによる継続修正を明示的に選ぶ場合だけのfallbackとする。

### Goal-mode follow-up suggestions

- Default: `$ultragoal` — objective、iteration、promotion、confirmationをdurable ledgerとして追跡する。
- Parallel delivery: `$ultragoal` + `$team` — strict runner/analyzer/test lanesをTeamで並行し、Ultragoalがcheckpointを所有する。
- `$autoresearch-goal` — 本件はresearch deliverable中心ではないため非推奨。naturalness evaluator研究を独立project化する場合のみ使用する。
- `$performance-goal` — loop runtimeや大量batch性能を測定最適化する独立objectiveが生じた場合のみ使用する。
- `$ralph` — legacy-styleの単一owner持続loopを明示的に選ぶ場合だけのfallback。

### RALPLAN execution boundary

- Architect review: APPROVE
- Critic review: APPROVE
- `ralplan_consensus_gate.complete`: false
- blocked reason: `documented_host_consensus_receipt_unavailable`
- このlocal approvalは計画品質の証拠であり、source実装開始の権限ではない。

## 14. Planning changelog

- Static phased refactor plan replaced with a workflow-faithful 80-sample generation/analyze/edit/re-evaluate loop.
- Incorporated prior Architect findings: reuse existing slots/selectors, versioned state only when evidence requires it, no universal constraint god object, no persistent template/syntax memory.
- Incorporated prior Critic findings: explicit promotion effect sizes, E2E environment manifest, schema sequencing deferred to evidence-led iterations, context size gate.
- Architect loop review applied: strict runner boundary、canonical/manifest/telemetry split、content-addressed state machine、isolated source snapshots、paired exploration lifecycle、holdout confirmation、CLI write-scope、external execution parity、two manual experimentsを追加。
- Critic loop review applied: workflow ancestor closure/PreviewAny、immutable natural-mode override、L0 environment/sink、rare-event verdicts、atomic resume semantics、qualitative vote aggregationを追加。
- Final Architect and Critic verdicts: APPROVE. Execution gate remains closed pending an official host-issued consensus receipt.
