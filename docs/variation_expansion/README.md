# Variation Expansion Workstream

このディレクトリは、日常系 location 昇格と action pool 拡張を進めるための作業入口です。

## Active Documents

- [Refactor Plan](./location_action_refactor_plan.md)
- [Progress](./progress.md)
- [Task Board](./tasks.md)

## Current Scope

今回の対象は次の3点です。

1. 日常系 location 8-10件の昇格
2. 昇格 location への専用 action pool 追加
3. 高カバレッジ既存 location への action 追加

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

## Completion Rule

この workstream は、次が満たされたとき完了扱いにします。

- 8-10件の日常系 location が base variation 計測に反映されている
- 対象 location が dedicated action pool または意図した fallback で生成可能
- 高カバレッジ既存 location の action 追加が semantic-only policy に違反していない
- `python tools/validate_prompt_data.py` が `ERROR: []`, `WARNING: []`
- `python assets/calc_variations.py --json` の差分が `progress.md` に記録されている
