# Semantic Diversity / Natural Language Refactor Specification

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`  
基準ブランチ: `main`  
作成日: 2026-09-06  
正本:
- `docs/diversity_refactor/spec.md`
- `docs/diversity_refactor/tasks.md`
- `docs/diversity_refactor/progress.md`

関連文書:
- `README.md`
- `CURRENT_STATUS.md`
- `REPO_STRUCTURE.md`
- `docs/prompt_quality/`
- `docs/semantic_epig/README.md`
- `docs/variation_expansion/500k_loop_plan.md`

---

## 0. Codex Execution Contract

Codex はこの wave では以下を守る。

1. 作業開始時に `CURRENT_STATUS.md`, `REPO_STRUCTURE.md`, 本 `spec.md`, `tasks.md`, `progress.md` を読む。
2. **一度に1つの task ID だけを実装する。**
3. task 開始前に `progress.md` を `IN_PROGRESS` に更新し、対象ファイルを記録する。
4. task の `Acceptance` を満たすまで次 task を開始しない。
5. failure は隠さず `BLOCKED` または `REJECTED` として `progress.md` に残す。
6. source/data hash が途中で変わった場合、古い評価結果を新しい candidate の証拠として再利用しない。
7. public `Context*` node I/O、`context_json` contract、semantic-only policy は維持する。
8. V150 の variation data を「数を増やす目的」で変更しない。
9. 大量語彙追加、新 dependency、LLM dependency、camera/quality/style/artist tag の再導入を行わない。
10. full release gate は milestone でのみ実行し、小 task ごとに重い blind review / confirmation を繰り返さない。

---

## 1. Objective

V150 を semantic-base の完成版として一旦 freeze し、次の価値軸を
`base variation count` から **effective semantic diversity と natural-language realization diversity** へ移す。

この wave の目的は4点。

1. **V150 Freeze**
   - 150k semantic-base を基準として固定する。
   - V250/V350/V500 は削除せず deferred roadmap とする。
2. **Effective Diversity Audit**
   - `semantic_unique@N`
   - `coverage@N`
   - `repetition`
   - `syntax entropy`
   を決定論的に測定できるようにする。
3. **Natural Language Realizer v2**
   - 既存 `ContentPlan` と `ActionFrame` を利用する。
   - 新しい意味情報を大量追加せず、同じ semantic frame を複数の自然な英文構造に realization する。
4. **Deterministic Diversity Scheduler**
   - pure random ではなく、連続 seed 上で同等候補を意図的に散らす。
   - semantic compatibility / EPIG / safety を壊さず diversity を増やす。

---

## 2. Strategic Decision: V150 Freeze

### 2.1 Freeze baseline

wave 開始時に以下を再計測し `progress.md` に記録する。

Expected V150 reference:

```text
unique subjects: 135
unique locations: 109
base variations: 150,184
compatibility rows: 8,227
actions per location: min 12 / median 16 / mean about 16.33 / max 20
unique mood tags: 172
unique micro actions: 280
unique background context tags: 1,028
semantic units: 1,480
```

実際の source of truth は wave 開始時の `main` と `python assets/calc_variations.py --json`。

### 2.2 Protected variation surfaces

以下は **feature expansion のためには変更禁止**。

```text
vocab/data/variation_scope.json
assets/compatibility_review.csv
vocab/source/action_pools/*.json
vocab/source/action_pools/_shared_families.json
vocab/data/action_pools.json
```

例外:
- 明確な bug fix
- security/policy fix
- data corruption fix

例外変更を行う場合:
- dedicated task ID を追加する
- variation count 増加を success criterion にしない
- before/after count と prompt-quality regression を記録する

### 2.3 Deferred roadmap

`V250 / V350 / V500` は historical / deferred plan として保持する。

この wave では:
- target count を追わない
- candidate subject/location/action を増やさない
- 500k plan を削除しない
- README / CURRENT_STATUS 上では「deferred while effective-diversity refactor is active」と明示する

---

## 3. Non-Goals

この wave では以下を行わない。

- LLM を runtime dependency にする
- embedding model を audit dependency にする
- camera / lens / framing / DoF を active prompt に戻す
- quality tag / render tag / artist tag / art style を active prompt に戻す
- body-shape emphasis を追加する
- character/location/action vocabulary の大量追加
- public ComfyUI node の追加
- public input/output schema の変更
- `context_json` version の変更
- subject/location compatibility model の全面刷新
- V250/V350/V500 の実装
- semantic EPIG を scheduler で置き換える
- randomness を完全に排除する

---

## 4. Architectural Invariants

### 4.1 Semantic-only invariant

最終 prompt は引き続き次の意味領域のみを扱う。

- subject / character profile
- clothing / TPO
- location / environment
- action / state / small event
- mood / staging / garnish
- object relation

禁止領域は既存 policy を正本とする。

### 4.2 Determinism invariant

同じ:
- source bytes
- configuration
- workflow
- seed
- history/context

から同じ結果が得られること。

新しい diversity 機構は wall clock、OS randomness、unordered set iteration に依存しない。

### 4.3 Safety / compatibility precedence

候補選択順序の原則:

```text
hard policy / solo safety / compatibility
        ↓
semantic eligibility / Semantic EPIG
        ↓
diversity scheduling
        ↓
weighted or deterministic tie resolution
        ↓
surface realization
```

Scheduler は filter で除外された候補を復活させてはならない。

### 4.4 Public compatibility invariant

以下を維持する。

- current `Context*` public inputs/outputs
- `PromptCleaner`
- `context_json: STRING`
- current workflow sample round-trip
- `composition_mode=false` legacy rollback behavior
- seed reproducibility

---

## 5. Target Architecture

```text
PromptContext
    │
    ├─ existing semantic pipelines
    │    ├─ character
    │    ├─ scene/action
    │    ├─ clothing
    │    ├─ location
    │    ├─ mood
    │    └─ garnish
    │
    ▼
ActionFrame + PromptContext + semantic debug
    │
    ├───────────────┐
    │               │
    ▼               ▼
Effective       Diversity
Signature       Scheduler
Builder         (eligible choices only)
    │               │
    └──────┬────────┘
           ▼
       ContentPlan
           │
           ▼
Natural Language Realizer v2
           │
           ▼
semantic-only natural prompt
           │
           ▼
PromptCleaner
```

Audit は runtime selection を変更しない read-only consumer とする。

---

# 6. Phase A — Effective Diversity Audit

## 6.1 New files

推奨:

```text
tools/audit_effective_diversity.py
tools/effective_diversity_metrics.py
assets/test_effective_diversity_metrics.py
assets/test_effective_diversity_audit.py
```

既存 `tools/workflow_prompt_runner.py` を generator として再利用する。
独自の「似た workflow runner」を作らない。

## 6.2 Signature model

final prompt text を再parseして semantic signature を推定しない。

可能な限り:
- `final_context`
- `ActionFrame`
- node debug decisions
- canonical resolver output

から signature を作る。

### `semantic_signature_v1/core`

最低限:

```text
canonical_subject
canonical_location
action_family_or_main_verb
primary_object_or_object_family
```

### `semantic_signature_v1/frame`

core に加えて利用可能なもの:

```text
posture
hand_action family
gaze_target family
progress
stimulus_or_obstacle
social_relation
mood
clothing family / chosen type
garnish semantic family
```

文字列全文を signature に入れすぎない。
表面上の言い換えを semantic unique と誤認しないことが目的。

## 6.3 Required metrics

### A. `semantic_unique@N`

```text
unique semantic signatures among first N records / N
```

最低限:
- `core`
- `frame`

を別々に出す。

推奨 N:

```text
128
512
2,048
8,192
```

small smoke では `128` のみでもよい。

### B. `coverage@N`

軸ごとの coverage を出し、単一値だけに潰さない。

Required axes:

```text
subject
location
action_family
primary_object_family
mood
clothing_family
garnish_family
syntax_family
```

定義:

```text
axis_coverage@N =
  unique values observed in first N
  / reachable values observed in the locked reference universe
```

reference universe は同じ source/config で固定した audit probe から構築し、
report に hash を持たせる。

Aggregate を出す場合は単純平均とし、axis 別値を必ず残す。

### C. repetition

最低限:

```text
exact_prompt_duplicate_rate
normalized_prompt_duplicate_rate
semantic_core_duplicate_rate
semantic_frame_duplicate_rate
max_consecutive_same_action_family
max_consecutive_same_syntax_family
```

`normalized_prompt` は:
- lowercase
- whitespace normalization
- punctuation normalization
- subject alias normalization

程度に留め、意味を書き換える aggressive stemmer は使わない。

### D. syntax entropy

Shannon entropy:

```text
H = -Σ p_i log2(p_i)
normalized_H = H / log2(K)
```

`K` は active syntax families。
`K <= 1` の場合 `normalized_H = 0.0`。

出力:
- family counts
- raw entropy
- normalized entropy
- dominant family share

## 6.4 Report schema

例:

```json
{
  "schema_version": "effective-diversity-audit/v1",
  "source_hash": "...",
  "workflow_hash": "...",
  "config_hash": "...",
  "seed_start": 0,
  "sample_count": 2048,
  "metrics": {
    "semantic_unique": {},
    "coverage": {},
    "repetition": {},
    "syntax_entropy": {}
  }
}
```

JSON field order は canonical output utility に合わせて deterministic にする。

## 6.5 Audit profiles

```text
smoke:     N=128
gate:      N=2,048
release:   N=8,192
```

Codex は通常 task では `smoke`。
milestone gate で `gate`。
final adoption のみ `release`。

これにより毎 task で重い audit を繰り返さない。

---

# 7. Phase B — Natural Language Realizer v2

## 7.1 Design principle

**semantic planning と linguistic realization を分離する。**

Realizer v2 は新しい scene content を考えない。

許可:
- clause order の変更
- sentence boundary の変更
- safe connective の追加
- existing semantic slots の再配置
- ActionFrame を使った既存情報の明示化
- pronoun / punctuation の安全な surface normalization

禁止:
- 新しい object の発明
- 新しい action の発明
- mood の勝手な変更
- location の勝手な変更
- subject の追加
- camera/style/quality language の追加

## 7.2 Reuse existing structures

必須:
- `ContentPlan`
- `ActionFrame`
- `template_catalog.json`
- existing named seed streams
- existing semantic policy
- existing solo safety
- existing prompt cleaner

新しい parallel semantic model を作らない。

## 7.3 Syntax family target

最初の promoted target は **最低6 family**。
7–8 は audit が良ければ有効化する。

### Required candidates

1. `subject_action_scene`
   - baseline
   - 1 sentence
   - S → A → L

2. `subject_action__scene_tail`
   - baseline-compatible
   - S → A. L.

3. `scene_lead_subject_action`
   - L → S → A
   - scene lead が文法的に安全な場合のみ

4. `action_lead_subject_scene`
   - A → S → L
   - gerund/participial action surface のみ
   - dangling modifier を禁止

5. `subject_scene_action`
   - S → L → A
   - ActionFrame から安全な predicate を作れる場合のみ

6. `subject_action_scene_insert`
   - S → A の内部または直後に non-duplicative scene adjunct
   - scene/action の意味重複時は fallback

### Optional candidates

7. `scene_sentence__subject_action`
   - L. S → A.

8. `subject_action_progress__scene`
   - `ActionFrame.progress` が存在する場合のみ
   - progress を新規生成せず既存 slot を使う

## 7.4 Eligibility-first rendering

各 syntax family は metadata を持つ。

例:

```json
{
  "key": "action_lead_subject_scene",
  "roles": ["focused", "transition"],
  "allowed_action_surfaces": ["gerund"],
  "requires": ["scene_anchor"],
  "forbids": ["fragment_subject_action"],
  "weight": 1.0
}
```

family を選んでから無理に文を修復するのではなく:

```text
context
  ↓
eligible families
  ↓
scheduler / deterministic selector
  ↓
render
  ↓
normalization
```

とする。

安全な family が1つしか残らない場合は baseline family を使う。

## 7.5 Predicate realization

一般-purpose English NLP engine を作らない。

優先順位:

1. existing full `action_clause` をそのまま安全に使える family
2. `ActionFrame.main_verb` が `-ing` surface の場合の限定的 construction
3. explicitly tested verb normalization helper
4. unsafe / unknown → baseline fallback

不規則動詞の巨大辞書を新設する必要が出たら scope creep と判定し、
この wave では baseline fallback を優先する。

## 7.6 Suggested file ownership

Primary candidates:

```text
pipeline/prompt_realizer.py
prompt_renderer.py
vocab/data/template_catalog.json
```

必要なら:

```text
pipeline/syntax_family_selector.py
```

新しい module を作るのは `prompt_realizer.py` がさらに責務過多になる場合のみ。

## 7.7 Debug contract

`ContextPromptBuilder` decision に最低限:

```text
realizer_version
syntax_family
eligible_syntax_families
syntax_fallback_reason
clause_order
template keys
```

を記録する。

Audit が final text parse に依存しないために使う。

---

# 8. Phase C — Deterministic Diversity Scheduler

## 8.1 Goal

同じ候補集合で seed を連番にしたとき、
pure independent random よりも family/category coverage を早く広げる。

Scheduler は:
- semantic compatibility を決めない
- safety を決めない
- EPIG を置き換えない
- novel content を作らない

**eligible candidates の中の selection policy** のみ担当する。

## 8.2 Core primitive

推奨 API:

```python
def spread_index(
    seed: int,
    size: int,
    namespace: str,
    *,
    block_key: str = "",
) -> int:
    ...
```

候補サイズ `K` に対して、連続 seed block 内で偏りを減らす
deterministic permutation / affine permutation を利用する。

例となる性質:

```text
same inputs -> same index
0 <= index < K
for a fixed block and K, positions distribute across K before heavy repetition
namespace separates action/syntax/garnish streams
```

実装方法は固定しないが、以下を禁止:

- Python built-in `hash()` 依存
- unordered container order 依存
- wall clock
- process-global mutable RNG
- OS entropy

既存 `mix_seed()` を使う。

## 8.3 Selection hierarchy

候補に semantic weight がある場合は全候補を平坦化しない。

推奨:

```text
hard eligible set
   ↓
semantic score / existing weight
   ↓
quality-equivalent shortlist or score band
   ↓
group by diversity key
   ↓
scheduler selects group
   ↓
existing deterministic weighted selection within group
```

score band の閾値は Phase A baseline なしに固定しない。
まず audit で bias を測る。

## 8.4 Rollout axes

### Required first axis: syntax family

最も低リスクで効果を測りやすい。

- eligible syntax family を scheduler で散らす
- `syntax entropy`
- `max_consecutive_same_syntax_family`
- naturalness
を評価する

### Required second axis: action family

既存 action selection の:
- safety
- object policy
- semantic EPIG
- recent verb/object penalty

を残し、その後の同等候補群で scheduler を利用する。

diversity key 候補:

```text
purpose
main_verb
object family
action semantic family
```

最終 key は audit 結果を見て1つに固定する。

### Optional axes

baseline で偏りが確認された場合のみ:

```text
garnish family
template part family
clothing family
```

「scheduler を使えるから全 axis に入れる」は禁止。

## 8.5 Sequence semantics

`seed` 自体を sequence index として扱える設計を基本とする。

history がある場合:
- existing recent-history penalty を維持
- scheduler と recent penalty が競合した場合は safety / semantic / repetition guard を優先

history がない単発 generation でも deterministic であること。

---

# 9. Quality Gates

## 9.1 Gate levels

### Level 1 — Task gate

各 task:
- focused unittest
- `tools/validate_prompt_data.py`（data touched 時）
- deterministic smoke audit（relevant 時）

### Level 2 — Phase gate

各 phase:
- relevant focused test suite
- `python tools/verify_full_flow.py`
- Effective Diversity `gate` profile
- before/after report

### Level 3 — Final adoption gate

Realizer v2 / Scheduler を active default にする直前:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
python assets/calc_variations.py --json
```

加えて:
- Effective Diversity `release` profile
- current prompt-quality fixed cohort comparison
- semantic consistency
- naturalness
- image-prompt suitability
- protagonist clarity
- redundancy
- diversity

### Blind review policy

この wave の小 task ごとに blind review を行わない。

blind review / large confirmation は:
- Realizer v2 active-default candidate
- Scheduler active-default candidate
- final combined candidate

のうち、**prompt surface を実際に変更する milestone に限定**する。

既存 `docs/prompt_quality/` contract が mandatory と判定する場合はそれを優先する。

---

# 10. Promotion Criteria

## 10.1 Phase A promotion

- audit metrics are deterministic
- same source/config/seed returns byte-stable or canonical-stable report
- no runtime prompt behavior change
- baseline report committed or hash-bound per repository policy

## 10.2 Realizer v2 promotion

必須:
- minimum 6 active syntax families
- semantic slots are preserved
- no banned-domain leakage
- no increase in consistency failures
- no material naturalness regression
- normalized syntax entropy improves vs v1 baseline
- exact/normalized prompt repetition does not regress materially
- unsupported action surfaces reliably fallback

数値 threshold は Phase A baseline を測定後に `progress.md` で lock する。
baseline を見る前に都合の良い threshold を固定しない。

## 10.3 Scheduler promotion

必須:
- exact determinism preserved
- semantic guard metrics non-regression
- coverage@N improves on at least the targeted axis
- max consecutive same-family does not worsen
- syntax/action entropy improves or remains acceptable
- EPIG ranking semantics are not bypassed

## 10.4 Combined promotion

- V150 counts unchanged unless approved bug fix
- no public node I/O change
- full tests pass
- workflow round-trip pass
- release audit pass
- prompt-quality gate pass
- README / CURRENT_STATUS / progress updated

---

# 11. Stop Conditions

以下の場合、task を止め `BLOCKED` または `REJECTED` とする。

- V150 protected data の大規模変更が必要になった
- realizer のために大量 lexical dictionary が必要になった
- grammar repair が general NLP engine 化し始めた
- scheduler が safety/EPIG を bypass しないと効果が出ない
- audit が final prompt の fragile regex parsing に依存する
- diversity metric を改善するため near-duplicate を水増しする設計になった
- seed determinism が壊れた
- public node I/O 変更が必要になった
- current prompt-quality guard に material regression が出た

---

# 12. Definition of Done

この wave は以下で完了。

1. V150 semantic-base freeze が文書化・検証されている
2. Effective Diversity Audit が deterministic CLI として利用可能
3. baseline diversity report が存在する
4. Realizer v2 が最低6 syntax family を安全に選択できる
5. Realizer v2 が semantic facts を追加・削除せず表現を変えられる
6. Deterministic Diversity Scheduler が最低 syntax + action family で評価される
7. targeted `coverage@N` / entropy / repetition が baseline より改善する
8. semantic consistency / naturalness / safety / determinism が regression しない
9. V150 base variation count を増やすことを success metric にしていない
10. `tasks.md` が terminal state、`progress.md` が final receipt を持つ
