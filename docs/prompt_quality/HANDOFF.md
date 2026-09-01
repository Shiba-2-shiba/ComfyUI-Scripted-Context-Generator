# Prompt Quality Engineering Loop 引き継ぎ

> Historical in-progress handoff. It was superseded on 2026-08-31 by the
> completed G010 strict aggregate receipt. Use `docs/prompt_quality/README.md`
> for the accepted release baseline; retain this file as audit history.

更新時点: 2026-08-25（Asia/Tokyo）

## 0. 2026-08-25 chat終了時の正確な再開点

ユーザー希望により、このchatはG007を未完了のまま安全に区切る。native aggregate goalとOMX G007はactive/in_progressのまま。`update_goal(complete)`、G007 checkpoint、cancelは実行していない。

- current protected source hash: `3009c2d0407b1a417362f50eb5d9c9a634850ca17377bfaa90ef370f5ed4c15b`
- latest focused verification: `python -m unittest assets.test_prompt_quality_compare assets.test_prompt_quality_review_scope` -> **43 passed**
- `git diff --check`: whitespace errorなし（Windows CRLF予告warningのみ）
- 最新product requirementsは実装済み:
  - 女性主体表現はassembled prompt全体で `girl` に統一
  - `woman` / `women` / `lady` / `female` / `1girl` legacy inputも `girl` へ正規化
  - 人種・民族・肌色・Black-associated hairstyle descriptorを除去
  - `black hair` / `black dress` / 背景色など非demographic色指定は保持
- promotion/recovery hardeningは実装中の最終段階:
  - raw assignment/lane/result/records/source/cohort/prompt binding
  - raw vote aggregate再計算、exact two lanes、side割当再計算
  - exact vote/hard-defect/reviewer/blindness contract
  - explicit frozen review-policy hash
  - path-bound verification v2とG007 gate inventory

### 現在staleで、次chatで再生成が必要な証拠

以下は以前passしたが、current source hash `3009c2...` より前のartifactなのでfinal authorityとして使わない。

- `docs/prompt_quality/confirmation-256.json`
- `docs/prompt_quality/final-review-summary.json`
- `assets/results/prompt_quality_loop/final-blind-review-attempt-009/`
- full Python 498/498、frontend 4/4、browser 2/2の既存pass（regression参考には使えるがstrict final evidenceではない）

### 次chatの最初の作業

1. `get_goal({})` と `omx ultragoal status --json` を確認し、同じaggregate goal / G007を継続する。
2. qualitative scopeを `docs/prompt_quality/final-review-contract.json` と一致させる。current contractはtarget=`consistency,naturalness,image_prompt_suitability`、guard=`protagonist_clarity,redundancy,diversity`。
3. review seed selectionをlocked comparison/contractへhash bindする。任意の「都合の良い20 seed」を許可しない。
4. verification v2の実artifactを生成する。各evidenceはgate/source/result path+hashへ結合し、G007 inventory（full Python、data、full-flow、widgets、compatibility、action pools、frontend、browser、3x256 confirmation、blind review、comparison）を満たす。
5. focused testsをgreenに保ったまま、current sourceで3x256 confirmationを再生成する。
6. final review contractに沿ったblind reviewを新attemptで実施する。consistencyをtargetにするならcombined G004–G006 ablation baselineが必要。別案としてcontractを正式に改訂し、separate G004 reviewを明示的authorityとして結合する。
7. fresh full suite、data checks、frontend、browserを再実行する。
8. independent `code-reviewer=APPROVE` と `architect=CLEAR` が揃った場合のみstrict quality-gate JSONを作り、`update_goal(complete)` -> fresh `get_goal` -> G007 checkpointを行う。

### 未解決の設計論点

- `final-review-contract.json` は consistency をtargetに含むが、attempt-009はG005 punctuation ablation baselineのため consistencyはguardだった。この不一致を解消せずattempt-009を流用しない。
- comparisonへexact review seed cohort（または決定論的selection algorithm + affected seeds）を固定し、assignment key/lane seed setとの一致をpromotionで必須にする。
- verification v2のfull regression minimumは現在505へ更新済み。テスト追加後はfresh discovery countと一致させるか、tracked discovery manifestへ結合する。

## 1. 目的と確定したスコープ

durable objective は次のとおり。

> Complete the durable ultragoal plan in `.omx/ultragoal/goals.json`, including later accepted/appended stories, under the original brief constraints; use `.omx/ultragoal/ledger.jsonl` as the audit trail.

ユーザーが明確化した主成果物は、ComfyUI workflow と同等にnode DAGを実行する独立Python scriptと、そのscriptを使う決定論的test/品質loopである。ComfyUI本体のinstallや実ComfyUI parityは任意の外部E2E checkであり、G004以降をblockしない。これは [goals.json](../../.omx/ultragoal/goals.json) と [OMX ledger](../../.omx/ultragoal/ledger.jsonl) にsteering済み。

## 2. Durable goalの現在地

| Goal | 状態 | 要点 |
| --- | --- | --- |
| G001 L0 strict loop harness | complete | workflow-faithful runner、64+16 cohort、canonical artifact、replay、optional parity harness |
| G002 L1 analyzer/baseline | complete | analyzer/issues/policy v2、comparison、append-only state、manual experiments |
| G003 L2 identity loop | complete | ambient secondary-person / implied crowdを除去し、iteration-002をPROMOTED |
| G004 L3 semantic consistency | complete | location/action time conflictsを除去し、review remediationをPROMOTED |
| G005 L4 natural language | complete | ActionFrame 80/80、punctuation 0、named template streamをPROMOTED |
| G006 L5 diversity | complete | syntax entropyを改善し、single/two sentence familyをPROMOTED |
| G007 L6 adoption gate | **in_progress** | natural default、frontend/browser round-tripはpass。最終review blocker remediation中 |

current source of truth は [goals.json](../../.omx/ultragoal/goals.json) と [ledger.jsonl](../../.omx/ultragoal/ledger.jsonl)。G007をfinal independent reviewと追加confirmationなしでcomplete扱いしないこと。

## 3. G001–G003の完了証拠

### G001

- Runner: [workflow_prompt_runner.py](../../tools/workflow_prompt_runner.py)
- Loop CLI: [prompt_quality_loop.py](../../tools/prompt_quality_loop.py)
- Supported profile: [prompt_quality_supported_profile.json](../../verification/fixtures/prompt_quality_supported_profile.json)
- L0 local artifact: `assets/results/prompt_quality_loop/l0-checkpoint/`
  - `records_sha256`: `aefff07a29eb22e861bc9956e890fb292a242f0200ddda4dbd351e6ea1017d87`
  - replay: 80 checked / 0 mismatch
  - cohort: 64 control + 16 exploration
- `run-manifest.json` SHA-256: `ac79cbe3374725849672a34f735ef5e396b14dcd8e75e108d214c740e4c99c54`
- 実ComfyUI環境定義は [environment.json](../../verification/environment.json) にあるが、現在はoptional。

### G002

- Analyzer: [analyze_prompt_quality.py](../../tools/analyze_prompt_quality.py)
- Comparison: [compare_prompt_quality.py](../../tools/compare_prompt_quality.py)
- Policy: [prompt_quality_policy.json](../../vocab/data/prompt_quality_policy.json)
  - version: `prompt-quality-policy/v2`
  - SHA-256: `ac365527cd6fc014bdc39d3c7c964d3429e61ab868626b84aa9b9c85f6cf24dc`
- Baseline local artifact: `assets/results/prompt_quality_loop/g002-baseline/`
  - `run-manifest.json` SHA-256: `58efd3fa04c78816d7d018e13f4ddb45d928bbb5d397bf88a1f152ed01a1b173`
- Manual experiment fixture: [manual_experiments.json](../../assets/fixtures/prompt_quality/manual_experiments.json)
  - SHA-256: `4339d0350f9e8f2036da7e45e4d2e00a6b31ef65f27a9dd1f1ed647280be5aeb`
- Durable audit: [prompt-quality ledger](./ledger.jsonl)

### G003

- Durable experiment root: [g003-ambient-secondary-person-v1](./experiments/g003-ambient-secondary-person-v1/)
- Final state: [0007-promoted.json](./experiments/g003-ambient-secondary-person-v1/iteration-002/state/0007-promoted.json)
  - terminal state record hash: `03c5bf63c6e5550333c38c08e0cc0a242a464356478702158d9aad3cf0217ae2`
- Formal comparison: `assets/results/prompt_quality_loop/g003-ambient-secondary-person-v1/comparison-iteration-002-final.json`
  - SHA-256: `896d0db794dc4a8db384073497ffda731d9fd44046802a3d58cd1a0bbb817ff2`
  - control64 `identity.other_person_solo_conflict_count`: `8 -> 0`
  - all hard/identity/fallback/context guards: pass
- Blind review attempt-003: `assets/results/prompt_quality_loop/g003-repro-iteration-002/review-attempt-003/review.json`
  - SHA-256: `c60d647a4834a4eb9c40202b154e1bc77b9ab068b116376fbbb34cf0f50e744a`
  - target dimensions: 36 valid、100% candidate support、0 regression
  - guard dimensions: 0 candidate-worse
  - candidate-only hard defects: 0
- Verification: `assets/results/prompt_quality_loop/g003-ambient-secondary-person-v1/verification-iteration-002.json`
  - SHA-256: `2de1645c471b00e5de53f749f42d7101d0fae9614e6aa6629e94f6df30064a59`
- Promotion: `assets/results/prompt_quality_loop/g003-ambient-secondary-person-v1/promotion-iteration-002.json`
  - SHA-256: `a26e757ec5951fc2d7530f0808834ecbc5070c7efb7b846f241e50e0016e3ec5`
  - verdict: `promote`; `source_mutated: false`
- Final candidate/source tree hash: `2d16c41090924257e9fd9ece31deccff752198b6ee33492c219a2f1b2eb88bf3`

`assets/results/` はgitignore対象でlocal-only。durableな判断証拠は `docs/prompt_quality/` のstate/ledger/hashで追跡する。

## 4. G004–G007の現在地

- G004 durable evidence: `docs/prompt_quality/experiments/g004-review-remediation-secondary-person-v1/`
  - formal location conflict `5 -> 0` paired80、seed 179 conflict なし
- G005 durable evidence: `docs/prompt_quality/experiments/g005-natural-action-frame-v4/`
  - ActionFrame 80/80、punctuation anomaly `39 -> 0` control、explicit False rollback
- G006 durable evidence: `docs/prompt_quality/experiments/g006-syntax-family-diversity-v3/`
  - syntax entropy `0.116115 -> 0.895601` control、repetition非回帰
- 256 confirmation: `docs/prompt_quality/confirmation-256.json`
  - G004 `24 -> 0`、G005 `137 -> 0`、G006 `0 -> 0.778828`
- Identity output contract:
  - 女性主体は最終promptで `girl` のみ。`woman` / `women` / `lady` / `female` / `1girl` は legacy input として受理して `girl` に正規化
  - 人種・民族・肌色の人物descriptorは最終promptから除去。`black dress`、髪色、背景色など人物属性でない色指定は保持
  - analyzer hard gate: `identity.non_girl_female_term_count == 0`、`identity.person_demographic_descriptor_count == 0`
- G007 compatibility:
  - Python workflow/sample checks pass
  - frontend Vitest 4/4 pass
  - sibling ComfyUI GUI save/reload 2/2 pass
  - recommended workflow/node defaultは `composition_mode=True`、明示的Falseでrollback

最終blind review attempt-009は、target 40/40 candidate優位、guard非回帰、candidate hard defect 0でpass。tracked authorityは `docs/prompt_quality/final-review-summary.json`。最終stop conditionはindependent code-reviewer/architect再reviewと、その後のfresh full verificationである。

## 5. Worktree差分（現時点）

### Modified — G003 behavior/regression

- `core/solo_safety.py`
- `assets/test_solo_safety.py`
- `assets/test_location_semantics.py`
- `assets/test_solo_duplicate_suppression.py`
- `assets/fixtures/prompt_snapshot_cases.json`

### Modified — G001 compatibility adapter

- `tools/analyze_context_workflow_diversity.py`

### Untracked — runner/parity

- `tools/workflow_prompt_runner.py`
- `tools/verify_prompt_execution_parity.py`
- `assets/test_prompt_execution_parity.py`
- `assets/test_prompt_quality_runner.py`
- `verification/environment.json`
- `verification/comfyui_sink/__init__.py`
- `verification/comfyui_sink/nodes.py`
- `verification/fixtures/prompt_parity_workflow.json`
- `verification/fixtures/prompt_quality_supported_profile.json`
- `assets/fixtures/prompt_quality_control_seeds.json`

### Untracked — analyzer/comparison/review/state

- `tools/analyze_prompt_quality.py`
- `tools/compare_prompt_quality.py`
- `tools/prompt_quality_loop.py`
- `tools/build_blind_prompt_review.py`
- `tools/build_targeted_prompt_review.py`
- `tools/aggregate_blind_prompt_review.py`
- `assets/test_prompt_quality_analyzer.py`
- `assets/test_prompt_quality_compare.py`
- `assets/test_prompt_quality_review_scope.py`
- `assets/test_prompt_quality_state.py`
- `assets/fixtures/prompt_quality/analyzer_precision_cases.json`
- `assets/fixtures/prompt_quality/manual_experiments.json`
- `vocab/data/prompt_quality_policy.json`

### Untracked — durable prompt-quality docs

- `docs/prompt_quality/ledger.jsonl`
- `docs/prompt_quality/experiments/g003-ambient-secondary-person-v1/candidate-run.json`
- `docs/prompt_quality/experiments/g003-ambient-secondary-person-v1/experiment.json`
- `docs/prompt_quality/experiments/g003-ambient-secondary-person-v1/ledger.jsonl`
- `docs/prompt_quality/experiments/g003-ambient-secondary-person-v1/review-contract-v2.json`
- `docs/prompt_quality/experiments/g003-ambient-secondary-person-v1/state/0001-hypothesis-locked.json` ～ `0006-compared.json`
- `docs/prompt_quality/experiments/g003-ambient-secondary-person-v1/review-attempt-002/repro-cohort-lock.json`
- `docs/prompt_quality/experiments/g003-ambient-secondary-person-v1/review-attempt-002/state/0001-review-cohort-locked.json`
- `docs/prompt_quality/experiments/g003-ambient-secondary-person-v1/review-attempt-003/repro-cohort-lock.json`
- `docs/prompt_quality/experiments/g003-ambient-secondary-person-v1/review-attempt-003/state/0001-review-cohort-locked.json`
- `docs/prompt_quality/experiments/g003-ambient-secondary-person-v1/iteration-002/state/0001-candidate-snapshot-locked.json` ～ `0007-promoted.json`

### Untracked — OMX durable plan/state

- `.omx/context/female-protagonist-natural-prompts-20260824T041057Z.md`
- `.omx/plans/prd-female-protagonist-natural-prompts.md`
- `.omx/plans/prd-prompt-quality-engineering-loop.md`
- `.omx/plans/review-architect-prompt-quality-engineering-loop.md`
- `.omx/plans/review-critic-prompt-quality-engineering-loop.md`
- `.omx/plans/test-spec-female-protagonist-natural-prompts.md`
- `.omx/plans/test-spec-prompt-quality-engineering-loop.md`
- `.omx/state/ralplan-prompt-quality-engineering-loop.json`
- `.omx/state/skill-active-state.json`
- `.omx/state/skill-active-state.json.lock.released-14568-1787549876079-bd5994e279e510377f4a6c1a`
- `.omx/state/ultragoal-state.json`
- `.omx/tmux-hook.json`
- `.omx/ultragoal/brief.md`
- `.omx/ultragoal/goals.json`
- `.omx/ultragoal/ledger.jsonl`

`HANDOFF.md` 自身もこの追加後はuntrackedになる。

## 6. 最新のverification

- Full: `python -m unittest discover -s assets -p "test_*.py"` -> **496 passed** (`206.640s`)
- Focused G003 final: 9 modules -> **83 passed**
- G002 integrated checkpoint: **74 passed**
- G001 targeted checkpoint: **44 passed**
- G001以前のfull checkpoint: **414 passed**
- `python tools/validate_prompt_data.py` -> ERROR 0 / WARNING 0
- `python tools/verify_full_flow.py` -> pass
- `python tools/check_widgets_values.py` -> pass
- `python tools/build_compatibility_review.py --check` -> pass
- `python tools/build_action_pools.py --check` -> pass
- frontend Vitest -> **4 passed**
- ComfyUI GUI save/reload Playwright -> **2 passed** (`test_logs/custom-workflow-roundtrip-20260825-135949`)
- final blind review -> pass (`assets/results/prompt_quality_loop/final-blind-review-attempt-009/review.json`、tracked summary: `docs/prompt_quality/final-review-summary.json`)

## 7. 新chatのbootstrap

PowerShell:

```powershell
Set-Location -LiteralPath 'C:\Users\inott\Downloads\新しいフォルダー\ComfyUI-Scripted-Context-Generator'

git -c safe.directory='C:/Users/inott/Downloads/新しいフォルダー/ComfyUI-Scripted-Context-Generator' status --short
git -c safe.directory='C:/Users/inott/Downloads/新しいフォルダー/ComfyUI-Scripted-Context-Generator' diff --stat

omx ultragoal status --json
omx ultragoal complete-goals --json
```

`complete-goals` はcurrent story handoffを取得するために使う。G007をfinal review evidenceなしでcheckpoint completeしてはならない。

Native goal同期:

1. 最初に `get_goal({})` を呼ぶ。
2. 同じaggregate objectiveがactiveなら、そのままG007を継続し、`create_goal` は呼ばない。
3. active goalがnullなら、次のpayloadで `create_goal` を1回だけ呼ぶ（token budgetは指定しない）。

```json
{
  "objective": "Complete the durable ultragoal plan in .omx/ultragoal/goals.json, including later accepted/appended stories, under the original brief constraints; use .omx/ultragoal/ledger.jsonl as the audit trail."
}
```

4. 別のactive/incomplete goalがある場合は置換しない。
5. completed goalがthreadに残っている場合は、その上から `create_goal` しない。必要ならCodex UIで `/goal clear` 後に再開する。
6. `update_goal(complete)` はG007 final code-reviewがAPPROVE/CLEARになった最終gateだけ。
7. G007完了時はfresh complete `get_goal` JSONとquality-gate JSONを使ってcheckpointする。

## 8. External checkout / cleanup注意

- repo-local `ComfyUI/` と `ComfyUI_frontend/` は検証用にdownload済みでgitignoreされている。
- repo-local `ComfyUI/.venv/Scripts/python.exe` でbrowser round-tripを実行可能。
- repo-local `ComfyUI_frontend/node_modules/` の local Vitest / Playwright binaryで検証済み。
- これらはprimary成果物ではなく、実ComfyUI parityもoptional。
- `assets/results/` には大きなlocal artifactがある。tracked ledger/stateのhash参照を確認せず削除しない。
- checkout、`.venv`、generated results、released lock fileなどのcleanupは破壊的になり得る。削除対象を正確に列挙し、**ユーザーの明示承認を得てから**実行する。

## 9. 禁止事項

- G004のfinding/verificationなしにpromote、checkpoint complete、cancelしない。
- `.omx/ultragoal/goals.json` / ledgerを手編集しない。
- `docs/prompt_quality/**/ledger.jsonl` とstate recordを上書き・並べ替え・削除しない。訂正や再試行は新しいappend record / attempt / iterationで行う。
- G003の失敗review attempt-001/002を削除しない。
- `assets/results/` のlocal artifactだけをdurable authorityとして扱わない。
- shared worktreeへreset/checkout/revertを行わない。
