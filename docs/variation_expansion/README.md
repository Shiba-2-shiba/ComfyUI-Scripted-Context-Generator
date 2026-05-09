# Variation Expansion Workstream

このディレクトリは、base variations 拡張作業の入口です。

現在の active work は **P13: 500k target planning** です。P8-P12 の
100k stabilization までは完了済みなので、次の実装は subject / location /
compatibility density / action depth の組み合わせを測ってから開始します。

## Active Documents

- [Progress](./progress.md)
- [Task Board](./tasks.md)
- [100k Stabilization and 500k Forward Plan](./base_variations_100k_plan.md)
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

現在は P13 です。500k へ向けた拡張形状を再設計し、bulk data edit の前に
target planner で候補形状を測ります。

並行する品質改善として、衣装 `states` が Location と衝突する問題を
[`clothing_state_location_gate_plan.md`](./clothing_state_location_gate_plan.md)
で扱います。これは prompt quality cleanup であり、base variation sizing
や compatibility rows は変更しません。

1. P8: remaining daily-life location を昇格し、`unique locations` を増やす - Done
2. P9: 100k target modeling を追加し、subject / location / action depth の必要量を測る - Done
3. P10: compatibility taxonomy と variation scope を 100k 向けに拡張する - Done
4. P11: action authoring source を 20+ effective actions に耐える形へ拡張する - Done
5. P12: 100k stabilization gate で全体検証を固定する - Done
6. P13: 500k target planning で次の拡張形状を決める - Active
7. P14: clothing state location gate で Location と衣装状態語の衝突を抑える - Done

10万達成までの再計画と、500kへ進むための制約は
[`base_variations_100k_plan.md`](./base_variations_100k_plan.md) を参照してください。

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

Current measured after P11:

```text
unique subjects: 120
unique locations: 91
base variations: 105,612
compatibility rows: 5,926
actions per location: min 12 / median 16 / mean 15.6 / max 20
missing action pools: 0
```

## P13 Planning Target

500k planning は、次を先に測ってから実装に入ります。

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
target shape: reached and stabilized at 105,612 base variations
final planning horizon: 500,000 base variations
```

## Source References

- [Current Status](../../CURRENT_STATUS.md)
- [Expansion Guide](../../EXPANSION_GUIDE.md)
- [Repository Structure](../../REPO_STRUCTURE.md)
- [Variation Scope](../../vocab/data/variation_scope.json)

## Completion Rule

P13 planning は、次が満たされたとき実装計画へ進めます。

- `python tools/plan_variation_target.py --target 500000` の scenario output が記録されている
- compatibility density と location count のどちらが次の limiter か明示されている
- action depth を増やす場合の repetition / semantic-quality guardrail が明示されている
- `vocab/data/variation_scope.json`, `assets/compatibility_review.csv`,
  `vocab/source/action_pools/` のどれを先に変えるかが決まっている
- P12 baseline checks は引き続き clean である
