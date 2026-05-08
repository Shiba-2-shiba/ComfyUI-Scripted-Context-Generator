# Variation Expansion Workstream

このディレクトリは、日常系 location 昇格と action pool 拡張を進めるための作業入口です。

## Active Documents

- [Next Refactor Plan](./next_refactor_plan.md)
- [Next Expansion Wave Plan](./next_expansion_wave_plan.md)
- [Progress](./progress.md)
- [Task Board](./tasks.md)
- [Completed Wave: 2026-05-08](./completed_wave_2026-05-08.md)
- [Original Wave Plan](./location_action_refactor_plan.md)

## Current Scope

第1波、運用面リファクタ、P8 location expansion は完了済みです。現在の次作業は P9 です。

1. P8: remaining daily-life location を昇格し、`unique locations` を増やす - Done
2. P9: P8 完了後に `unique subjects` の昇格候補を評価する - Next

詳細な候補、想定増分、実行順は
[`next_expansion_wave_plan.md`](./next_expansion_wave_plan.md) を参照してください。

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
