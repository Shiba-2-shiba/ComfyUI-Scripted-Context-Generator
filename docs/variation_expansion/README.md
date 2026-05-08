# Variation Expansion Workstream

このディレクトリは、日常系 location 昇格と action pool 拡張を進めるための作業入口です。

## Active Documents

- [Base Variations 100k Implementation Plan](./base_variations_100k_plan.md)
- [Next Refactor Plan](./next_refactor_plan.md)
- [Next Expansion Wave Plan](./next_expansion_wave_plan.md)
- [Progress](./progress.md)
- [Task Board](./tasks.md)
- [Completed Wave: 2026-05-08](./completed_wave_2026-05-08.md)
- [Original Wave Plan](./location_action_refactor_plan.md)

## Current Scope

第1波、運用面リファクタ、P8 location expansion、P9 target modeling、P10 compatibility taxonomy expansion、P11 action authoring refactor、P12 100k stabilization gate は完了済みです。現在の次作業は 500k へ向けた拡張計画の再設計です。

1. P8: remaining daily-life location を昇格し、`unique locations` を増やす - Done
2. P9: 100k target modeling を追加し、subject / location / action depth の必要量を測る - Done
3. P10: compatibility taxonomy と variation scope を 100k 向けに拡張する - Done
4. P11: action authoring source を 20+ effective actions に耐える形へ拡張する - Done
5. P12: 100k stabilization gate で全体検証を固定する - Done
6. P13: 500k target planning を開始する - Next

10万達成までの再計画と、500kへ進むための制約は
[`base_variations_100k_plan.md`](./base_variations_100k_plan.md) を参照してください。

## Baseline

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

Target planning command:

```bash
python tools/plan_variation_target.py --target 100000
```

## Intermediate Target

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

この workstream は、次が満たされたとき完了扱いにします。

- `vocab/data/variation_scope.json` が current sizing surface を明示する
- `python tools/check_variation_scope.py` が `ERROR: []`
- `assets/compatibility_review.csv` の生成・検証手順が docs に明記されている
- `python tools/validate_prompt_data.py` が `ERROR: []`, `WARNING: []`
- `python tools/build_action_pools.py --check` が `ERROR: []`, `WARNING: []`
- `python tools/plan_variation_target.py --target 100000` が target met を返す
