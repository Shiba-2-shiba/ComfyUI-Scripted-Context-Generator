# Variation Expansion Workstream

このディレクトリは、base variations 拡張作業の入口です。

現在の active work は **P13: staged 500k loop planning** です。P8-P12 の
100k stabilization までは完了済みです。現行 planner を核に、L0-L3 の
capability pass と V150/V250/V350/V500 の段階gateを順に進めます。

## Active Documents

- [Progress](./progress.md)
- [Task Board](./tasks.md)
- [Canonical Staged 500k Loop Plan](./500k_loop_plan.md)
- [Planner Refactor Specification](./planner_refactor_spec.md)
- [Promoted Planner L1 Contract](./planner_l1_contract.md)
- [Variation Candidate L2 Contract](./candidate_l2_contract.md)
- [Variation Candidate L3 Snapshot Contract](./candidate_l3_contract.md)
- [V150 Planner L0 Baseline](./experiments/v150-planner-l0/manifest.json)
- [V150 Planner L1 Receipt](./experiments/v150-planner-l1/receipt.json)
- [V150 Candidate L2 Rejection](./experiments/v150-candidate-l2/rejection-receipt.json)
- [V150 Candidate L2 Iteration 002 Handoff](./experiments/v150-candidate-l2-iteration-002/handoff-receipt.json)
- [V150 Candidate L3 Snapshot Rejection](./experiments/v150-candidate-l3-iteration-001/rejection-receipt.json)
- [V150 Shape Iteration 003 Handoff](./experiments/v150-candidate-shape-iteration-003/handoff-receipt.json)
- [V150 Shape Iteration 004 Prompt Rejection](./experiments/v150-candidate-shape-iteration-004/rejection-receipt.json)
- [V150 Coverage Schedule Iteration 005 Rejection](./experiments/v150-candidate-shape-iteration-005/rejection-receipt.json)
- [V150 Full-Workflow Coverage Iteration 006](./experiments/v150-candidate-shape-iteration-006/rejection-receipt.json)
- [V150 Guard Remediation Iteration 007](./experiments/v150-candidate-shape-iteration-007/guard-remediation-receipt.json)
- [100k Stabilization and Historical 500k Notes](./base_variations_100k_plan.md)
- [Clothing State Location Gate Refactor Plan](./clothing_state_location_gate_plan.md)

Historical or completed-plan references:

- [Completed Refactor Plan](./next_refactor_plan.md)
- [Completed P8 Expansion Wave Plan](./next_expansion_wave_plan.md)
- [Completed Wave: 2026-05-08](./completed_wave_2026-05-08.md)
- [Original Wave Plan](./location_action_refactor_plan.md)

## Current Scope

第1波、運用面リファクタ、P8 location expansion、P9 target modeling、P10
compatibility taxonomy expansion、P11 action authoring refactor、P12 100k
stabilization gate は完了済みです。

現在は P13 L3 full-workflow coverage iteration 006完了後のquality remediation設計です。L0 baseline と6件の非counted runtime pool分類は
`experiments/v150-planner-l0/`、L1 pure projectionの昇格証拠は
`experiments/v150-planner-l1/` にhash固定済みです。L2 iteration 001は
coverage不足とduplicate pressure超過でreject済みです。iteration 002は
structural gateを通過しましたが、isolated materializationのrealized値は
`141,984`でV150未達でした。prompt生成はblockされ、snapshot iteration 001は
reject済みです。

Exact contribution modelにより4 location追加で`150,184`となるshapeを実装し、
isolated 64+16比較まで完了しました。location entropyは改善しましたが、8 location / 13
location-action pairのcoverage不足、repeated n-gram、context sizeの回帰により
`REJECTED`です。subject追加はなく、active dataへの昇格もありません。

Iteration 005ではfixed 64+16を維持した19-row scheduleを実装しましたが、
`ContextSource`到達19/19に対して最終workflowはlocation 12/19、exact
location-action 9/19でした。次は`ContextSceneVariator`を含むcomplete workflow
outcomeを事前modelingします。品質正本のrejectとactive dataは変更していません。

Iteration 006ではfixed 64+16内でfinal location/action witnessを19/19再現し、
coverage gateを通過しました。ただしcoverageは品質証拠ではなく、semantic-family
repetitionとcontext size guardが回帰したため品質判定は引き続き`REJECTED`です。

Iteration 007ではcoverage scheduleを凍結したままdebug payloadを圧縮し、
semantic-family/context sizeを含む全定量guardを非回帰へ戻しました。q9からの
cleaned prompt変更は0件です。この結果はdiagnostic passであり、次は非選択の
quality validation surfaceが必要です。

並行する品質改善として、衣装 `states` が Location と衝突する問題を
[`clothing_state_location_gate_plan.md`](./clothing_state_location_gate_plan.md)
で扱います。これは prompt quality cleanup であり、base variation sizing
や compatibility rows は変更しません。

1. P8: remaining daily-life location を昇格し、`unique locations` を増やす - Done
2. P9: 100k target modeling を追加し、subject / location / action depth の必要量を測る - Done
3. P10: compatibility taxonomy と variation scope を 100k 向けに拡張する - Done
4. P11: action authoring source を 20+ effective actions に耐える形へ拡張する - Done
5. P12: 100k stabilization gate で全体検証を固定する - Done
6. P13: staged 500k loop planning で planner と次の拡張形状を検証する - Active
7. P14: clothing state location gate で Location と衣装状態語の衝突を抑える - Done

10万達成までの履歴は `base_variations_100k_plan.md`、現在の500k計画は
[`500k_loop_plan.md`](./500k_loop_plan.md) を参照してください。

## Historical Baseline

Last measured: 2026-05-08

```text
unique subjects: 58
unique locations: 76
base variations: 15,610
compatibility rows: 1,637
actions per location: min 4 / median 8 / mean 8.03 / max 12
location candidates: 93
dedicated action pool missing candidates: 9
```

Current measured after later variation restrictions:

```text
unique subjects: 120
unique locations: 90
base variations: 103,212
compatibility rows: 5,806
actions per location: min 12 / median 16 / mean 15.6 / max 20
missing action pools: 0
```

## P13 Planning Target

500k planning は、次を段階別に測り、`docs/prompt_quality/` の品質契約を
維持できる候補だけを次のstageへ昇格します。

- subject count
- location count
- compatibility density
- median action depth
- action-family reuse quality

Target planning command:

```bash
python tools/plan_variation_target.py --target 500000
```

## Current Stabilized Target

```text
target base variations: 100,000
target shape: reached and remains above target at 103,212 base variations
final planning horizon: 500,000 base variations
```

## Source References

- [Current Status](../../CURRENT_STATUS.md)
- [Expansion Guide](../../EXPANSION_GUIDE.md)
- [Repository Structure](../../REPO_STRUCTURE.md)
- [Variation Scope](../../vocab/data/variation_scope.json)

## Completion Rule

P13 planning は、次が満たされたとき最初の V150 実装waveへ進めます。

- `python tools/plan_variation_target.py --target 500000` の scenario output が記録されている
- compatibility density と location count のどちらが次の limiter か明示されている
- action depth を増やす場合の repetition / semantic-quality guardrail が明示されている
- `vocab/data/variation_scope.json`, `assets/compatibility_review.csv`,
  `vocab/source/action_pools/` のどれを先に変えるかが決まっている
- P12 baseline checks は引き続き clean である
- L0-L3 planner capability の対象、テスト、stop condition が固定されている
- baseline/candidate の prompt-quality control/exploration cohort、blind
  review、confirmation、promotion/rejection evidence 契約が固定されている
