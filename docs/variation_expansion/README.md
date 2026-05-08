# Variation Expansion Workstream

このディレクトリは、日常系 location 昇格と action pool 拡張を進めるための作業入口です。

## Active Documents

- [Next Refactor Plan](./next_refactor_plan.md)
- [Progress](./progress.md)
- [Task Board](./tasks.md)
- [Completed Wave: 2026-05-08](./completed_wave_2026-05-08.md)
- [Original Wave Plan](./location_action_refactor_plan.md)

## Current Scope

第1波は完了済みです。現在の作業対象は、次の拡張に入る前の運用面リファクタです。

1. variation scope の source of truth 化
2. `assets/compatibility_review.csv` の再生成可能化
3. `action_pools.json` の authoring 面整理

## Baseline

Last measured: 2026-05-08

```text
unique subjects: 58
unique locations: 68
base variations: 15,034
compatibility rows: 1,565
actions per location: min 4 / median 8 / mean 8.03 / max 12
location candidates: 93
dedicated action pool missing candidates: 17
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
