# Repository Cleanup Refactor Specification

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev2`
作成日: 2026-06-19
関連文書:

- `CURRENT_STATUS.md`
- `REPO_STRUCTURE.md`
- `docs/documentation_cleanup_plan.md`
- `docs/repository_cleanup/progress.md`
- `docs/repository_cleanup/tasks.md`

---

## 1. 目的

このリファクタは、prompt 生成ロジックや ComfyUI node の public I/O を変えずに、
リポジトリの保守面を整理するためのもの。

対象は次の4点に限定する。

1. 通常の unittest に混ざっている重い監査を分離する
2. `assets/` に混在している test / audit / generated artifact / archive の責務を整理する
3. compatibility facade の境界を将来の変更者にも分かるように固定する
4. 空の placeholder file を削除する

この順序で進める。先にファイル移動や削除を行うと、テスト失敗が runtime regression なのか、
テスト配置変更の副作用なのかを切り分けにくくなる。

---

## 2. Non-Goals

この波では次を行わない。

- `Context*` node の public input/output spec 変更
- prompt 文面、seed determinism、variation sizing の意図的な変更
- vocabulary expansion や solo safety ルールの追加
- 新規依存関係の追加
- ComfyUI workflow sample の仕様変更
- archive 内 historical docs の本文修正

---

## 3. Current Findings

### 3.1 重い unittest

`assets/test_repetition_guard_audit.py` には `step_count=32, scenario_count=8` の監査が
通常の unittest として含まれている。

該当箇所:

- `assets/test_repetition_guard_audit.py`
- `tools/audit_repetition_guard.py`

確認済みの問題:

- `test_repetition_guard_thresholds_pass_for_default_audit` 単体で 60 秒 timeout
- `python -m unittest discover -s assets -p "test_*.py"` の通常導線を重くする
- CI や変更前後確認で「全テストを気軽に回す」運用を妨げる

### 3.2 `assets/` の責務混在

`assets/` は現在、少なくとも次を同居させている。

- unittest
- fixtures
- audit / verification scripts
- generated baseline / results
- historical archive
- architecture docs

確認済みの問題:

- `assets/results/` は `.gitignore` 対象だが、追跡済み baseline が残っている
- tests と generated artifacts の境界が読み取りにくい
- archive が active verification surface と同じ階層にあり、探索ノイズになる

### 3.3 compatibility facade の境界

互換 facade は意図的に残されている。

- `pipeline/content_pipeline.py`
- `background_vocab.py`
- `clothing_vocab.py`
- `improved_pose_emotion_vocab.py`

確認済みの良い点:

- facade であることは docstring や `REPO_STRUCTURE.md` に書かれている
- 旧 import を即座に壊さない設計になっている

確認済みの問題:

- repo-owned caller の許容範囲が機械的に固定されていない
- 新規コードが facade を default import 先として使っても検出しにくい
- compatibility surface を残す期限または保持理由がファイル単位では弱い

### 3.4 空 placeholder

次の tracked file は実質空で、active source としての意味がない。

- `vocab/background/test.md`
- `vocab/clothing/test.md`
- `vocab/data/test.md`
- `vocab/garnish/test.md`

確認済みの問題:

- 検索ノイズになる
- `test.md` という名前が test asset と誤解されやすい

---

## 4. Refactor Principles

### 4.1 Behavior lock first

実装前に現在の挙動を確認する。配置変更後も、少なくとも同じ focused checks を通す。

Baseline command:

```bash
git status --short --branch
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python assets/calc_variations.py --json
python -m unittest assets.test_solo_duplicate_suppression assets.test_location_semantics assets.test_vocab_lint assets.test_mood_builder
```

重い監査は通常 unittest から分離した後、明示的な audit command で確認する。

### 4.2 One boundary per pass

1 pass で複数種類の整理を混ぜない。

推奨順:

1. heavy audit separation
2. `assets/` responsibility map and artifact policy
3. compatibility facade guardrails
4. placeholder deletion
5. docs/status update

### 4.3 Runtime behavior must remain stable

次を変えない。

- prompt output contract
- seed determinism
- current base variations: `103,212`
- current variation boundary: `120 subjects / 90 locations`
- public `Context*` node I/O
- existing workflow sample compatibility

### 4.4 Move only when ownership is clear

ファイル移動は import path、test discovery、docs links を同時に直せる場合だけ行う。
単に見た目を整えるための大規模移動は行わない。

---

## 5. Target Design

### 5.1 Test and audit split

通常 unittest:

- deterministic
- short
- no generated baseline dependency unless fixture is tracked
- default local check として 1-2 分以内を目標にする

Audit:

- threshold / KPI / long sequence evaluation
- generated JSON output allowed
- `assets/results/` or future `artifacts/` に出力
- explicit command で実行する

Candidate naming:

```text
assets/test_repetition_guard_audit.py
  -> short unittest only

tools/audit_repetition_guard.py
  -> long audit CLI

docs/repository_cleanup/progress.md
  -> long audit runtime and last resultを記録
```

必要なら unittest では long case を skip するのではなく、test method 自体を短い fixture に変更する。
long audit は `tools/` の CLI として明示する。

### 5.2 `assets/` responsibility map

短期的には大移動せず、まず active ownership を明文化する。

```text
assets/test_*.py          unittest
assets/fixtures/          tracked test fixtures
assets/results/           ignored generated outputs
assets/archive/           historical assets, not active checks
assets/compatibility_review.csv  tracked variation sizing input
assets/calc_variations.py tracked metric tool
```

中期的な候補:

```text
tests/                    Python unittest relocation target
tools/                    executable audit / validation scripts
artifacts/                ignored generated outputs
docs/*/archive/           historical docs only
```

この波では、移動による import churn が大きい場合は明文化と小さい整理に留める。

### 5.3 Compatibility facade guardrails

compatibility facade は残してよいが、次を固定する。

- facade file の docstring に owner / allowed callers / removal condition を書く
- repo-owned caller が増えたら test が検出する
- runtime implementation は narrower module を import する
- public compatibility tests は `assets/test_deprecated_behavior.py` に集約する

Guard test candidate:

```text
assets/test_compatibility_boundaries.py
```

Check examples:

- `pipeline.content_pipeline` を repo-owned runtime が import していない
- root `*_vocab.py` facade を新規 runtime module が default import 先にしていない
- allowed caller list は明示的に管理する

### 5.4 Placeholder deletion

空 placeholder は削除する。

削除対象:

```text
vocab/background/test.md
vocab/clothing/test.md
vocab/data/test.md
vocab/garnish/test.md
```

削除前確認:

```bash
rg -n "vocab/(background|clothing|data|garnish)/test.md|test.md" README.md CURRENT_STATUS.md REPO_STRUCTURE.md docs assets tools vocab
```

参照がなければ削除する。参照がある場合は、参照先を正しい docs または fixtures に更新する。

---

## 6. Verification Gates

### 6.1 Before changes

```bash
git status --short --branch
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python assets/calc_variations.py --json
python -m unittest assets.test_solo_duplicate_suppression assets.test_location_semantics assets.test_vocab_lint assets.test_mood_builder
```

### 6.2 After heavy audit split

```bash
python -m unittest assets.test_repetition_guard_audit
python -m unittest discover -s assets -p "test_*.py"
python tools/audit_repetition_guard.py --help
```

If full discovery still includes long audits, record the remaining file and split it before continuing.

### 6.3 After `assets/` cleanup

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python assets/calc_variations.py --json
```

If test relocation is done, run both old and new discovery commands until old path is intentionally empty or documented.

### 6.4 After compatibility facade guardrails

```bash
python -m unittest assets.test_deprecated_behavior
python -m unittest assets.test_registry
python -m unittest assets.test_context_content_pipeline
```

Run the new compatibility boundary test if added.

### 6.5 Final gate

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python assets/calc_variations.py --json
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

---

## 7. Definition of Done

- 通常 unittest から長時間監査が分離されている
- long audit の実行方法が docs に明示されている
- `assets/` の active ownership と ignored/generated artifact policy が明文化されている
- tracked generated baseline の扱いが fixtures / ignored artifact / deleted のいずれかに整理されている
- compatibility facade の allowed caller と保持理由がファイルまたは test で固定されている
- 空 placeholder が削除されている
- prompt output, variation sizing, node I/O に意図しない変更がない
- final verification gate が pass するか、既知の slow audit / ignored artifact gap として記録されている
