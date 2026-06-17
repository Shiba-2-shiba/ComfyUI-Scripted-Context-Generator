# Curated Reference Adoption Specification

対象リポジトリ: `ComfyUI-Scripted-Context-Generator`  
対象ブランチ: `dev2`  
作成日: 2026-06-17 JST  
関連文書:

- `docs/semantic_epig/reference_refresh_spec.md`
- `docs/semantic_epig/reference_refresh_progress.md`
- `docs/semantic_epig/reference_refresh_handoff.md`
- `docs/semantic_epig/refactor_spec.md`
- `docs/semantic_epig/refactor_progress.md`

---

## 1. 目的

前回の reference refresh では、EPIG / NRC VAD / EmotionDynamics / LLM expanded prompts を
runtime へ直接接続せず、audit-only として扱う判断をした。

この文書は、その次段階として、以下の 1〜3 を主対象にした実装計画を定義する。

1. 低リスクな整備
   - `docs/semantic_epig/reference_refresh_*` に残る古い参考パスを再現可能な形へ整理する。
   - `relation_keys` 対応の未完テストを追加して、既存 matcher の仕様を固定する。
2. 採用前の候補選定
   - `assets/results/subject_centric_descriptor_candidates.json` の `needs_phrase` を直接採用せず、repo-authored な候補へ書き直すための選定手順を作る。
   - local/generated な reference output と tracked data の境界を明確にする。
3. 小さな runtime 採用計画
   - 最初の runtime 採用対象は subject-centric な personality / garnish descriptor の小規模 curated set に限定する。
   - passive/debug-first で導入し、active 化は audit と snapshot が揃った小さな wave に限定する。

後続拡張では、同じ枠組みで emotion nuance、action descriptor、dominance audit などへ広げられるようにする。

---

## 2. 現在の前提

### 2.1 Runtime baseline

- Public surface は `Context*` nodes と `PromptCleaner`。
- Public node I/O は変更しない。
- Transport は `context_json: STRING`。
- Semantic EPIG の5 domain は all-active:
  - `action`
  - `object_relation`
  - `location_scene`
  - `clothing_tpo`
  - `personality_behavior`
- `selected_by_semantic` は後方互換フィールドとして残し、新規検証は明示的 debug fields を見る。

### 2.2 Reference refresh baseline

直近の判断:

```text
overall_decision=no_runtime_adoption_now
runtime_prompt_changes=deferred
dominance_runtime_axis=audit_only
small_derived_data_subsets_should_be_added_now=false
```

理由:

- 既存 Semantic EPIG runtime は現時点で十分に機能している。
- raw data / score-bearing overlay を tracked data や runtime へ入れるには、ライセンス・再配布・出力 drift のリスクがある。
- `subject_centric_descriptor_candidates.json` の `needs_phrase` は、そのまま使う語彙ではなく、repo 用に書き直すヒントである。
- LLM expanded prompts は style / quality / camera / render 語を多く含むため、negative corpus 以外に使わない。

### 2.3 現在確認済みの reference metrics

現在の `参考` ディレクトリで再実行した代表値:

```text
overlay.extracted_term_count=8728
overlay.matched_term_count=7700
overlay.unmatched_term_count=1028
subject_descriptor.descriptor_count=809
subject_descriptor.direct_count=7
subject_descriptor.needs_phrase_count=80
subject_descriptor.reject_count=595
subject_descriptor.unmatched_count=127
llm_policy.policy_issue_count=83
dimension_projection.high_risk_count=15
dimension_projection.runtime_axis_adoption=deferred
```

---

## 3. Non-goals

この wave では以下を行わない。

- NRC / EPIG / EmotionDynamics の raw data を runtime で読む。
- `assets/results/*.json` の score-bearing overlay を tracked data として採用する。
- `llm_expanded_prompts.csv` を prompt source にする。
- public ComfyUI node I/O を変更する。
- 新規 dependency を追加する。
- dominance を runtime axis として active 化する。
- 大規模な prompt snapshot 更新を伴う出力刷新を行う。
- subject-centric descriptor を一度に複数 wave 分 active 化する。

---

## 4. Scope

### 4.1 Part 1: Low-risk stabilization

#### 4.1.1 Reference path cleanup

現状の docs には過去環境の絶対パスが残っている。

例:

```text
C:\Users\inott\Downloads\新しいフォルダー (3)\参考
```

方針:

- 手順例では可能な限り `..\参考` または `<REFERENCE_ROOT>` を使う。
- 現環境固有の例を出す場合は、"local example" と明記する。
- `参考/` は repo 外の local source であり、commit 対象外であることを繰り返し明記する。

Acceptance:

- `reference_refresh_handoff.md` と `reference_refresh_progress.md` の再実行コマンドが、repo checkout の親ディレクトリにある `参考` で動く形になる。
- 旧 `(3)` パスへ依存した説明が残らない。
- 生成物は `assets/results/` に出すが tracked にしない。

#### 4.1.2 Relation-key-specific action descriptor fixture/test

`pipeline/action_semantics.py` は `relation_keys` matcher を持っているが、専用 fixture/test が未完である。

方針:

- tiny payload / temporary descriptor を test 内で作るか、既存 data に最小の safe descriptor を追加する。
- まずは runtime output 変更を避け、`semantic_descriptor_options_for_slot()` の relation-key match を直接テストする。
- data 追加が必要な場合は semantic-only policy と asset validator を同時に通す。

Acceptance:

- `relation_keys=["drink:sipping"]` のような descriptor が、該当 relation key でだけ返る。
- unrelated relation key では返らない。
- action key / object token / relation key の優先関係が deterministic に固定される。
- runtime prompt 出力は変わらない。

### 4.2 Part 2: Candidate selection before adoption

#### 4.2.1 Local reports regeneration

候補選定は tracked data ではなく、local/generated report から始める。

再生成対象:

```text
assets/results/subject_centric_descriptor_candidates.json
assets/results/epig_reference_overlay.local.json
assets/results/reference_dimension_projection.json
assets/results/llm_expanded_prompt_policy_audit.json
assets/results/reference_refresh_adoption_decision.json
```

Acceptance:

- `assets/results/` は tracked しない。
- report が missing の場合でも、再生成コマンドが docs から辿れる。
- optional reference が無い場合は warning として記録し、実装 blocker にしない。

#### 4.2.2 Candidate triage rules

`subject_centric_descriptor_candidates.json` の分類を次のように扱う。

| Classification | Meaning | Action |
|---|---|---|
| `direct` | 既存 repo descriptor と subject-centric reference が exact match | 既存 descriptor の validation signal として使用可 |
| `needs_phrase` | subject-centric signal はあるが、そのまま prompt phrase に弱い | repo-authored phrase へ書き直す候補 |
| `reject` | 非 subject / policy banned / prompt に不適 | 採用しない |
| `unmatched` | reference signal なし | 既存 repo-authored descriptor として維持、削除しない |

Acceptance:

- `needs_phrase` から直接 copied phrase を作らない。
- 採用候補には `source_hint`, `rewrite_reason`, `target_slot`, `risk_note` を持たせる。
- body-type / camera / quality / render / style domain に近い候補は除外する。

### 4.3 Part 3: Small runtime adoption plan

#### 4.3.1 First adoption target

最初の対象は subject-centric な personality / garnish descriptor に限定する。

候補:

- shy / gentle / serious / confident の gaze / posture / hands descriptor
- expression ではなく body expression として安全なもの
- action context と矛盾しにくいもの

除外:

- camera angle / viewpoint
- body-shape emphasis
- quality / style / render phrasing
- LLM expanded prompt 由来の phrase
- score-bearing raw copy

#### 4.3.2 Proposed data shape

新しい tracked data を入れる場合は、full overlay ではなく小さな repo-authored data にする。

候補ファイル:

```text
vocab/data/subject_centric_descriptor_overrides.json
```

最小 schema 案:

```json
{
  "schema_version": "1.0",
  "notes": "Repo-authored subject-centric descriptors derived from local audit hints, not copied source data.",
  "descriptors": [
    {
      "id": "shy_gaze_away_small",
      "personality": ["shy"],
      "slot": "gaze",
      "text": "looking slightly away",
      "source_hint": ["subject_centric_audit:needs_phrase"],
      "rewrite_reason": "Turned a weak reference term into an existing repo-style subject descriptor.",
      "risk_note": "Avoid camera/viewpoint phrasing; keep as behavior.",
      "mode": "passive"
    }
  ]
}
```

Rules:

- `text` は repo-authored であること。
- `source_hint` は provenance であり、runtime lookup source ではない。
- 初期 `mode` は `passive`。
- active 採用前に audit と snapshot を必ず取る。

#### 4.3.3 Runtime integration boundary

候補 integration point:

- `vocab/personality_semantics.py`
- `vocab/garnish/logic.py`
- optional validator in `asset_validator.py`

方針:

- 既存 `personality_behavior_profiles.json` をいきなり大きく書き換えない。
- override loader は missing file safe にする。
- passive mode では debug に候補 availability / ranking のみを出し、prompt output を変えない。
- active mode は feature flag / config を通して明示的に切り替える。

Possible config extension:

```json
{
  "domains": {
    "subject_centric_descriptor": {
      "mode": "passive",
      "max_candidates_per_slot": 1
    }
  }
}
```

既存 `personality_behavior` の内部 option として扱うか、新 domain として扱うかは実装前に決める。
初期は `personality_behavior` 内の passive debug field として実装する方が低リスク。

---

## 5. Extensibility design

### 5.1 Adoption pipeline

今後の reference-driven 採用は次の順序に固定する。

```text
local reference material
  -> local generated audit report
  -> human/repo-authored candidate rewrite
  -> tiny tracked curated data
  -> passive debug integration
  -> active/passive prompt audit
  -> active runtime adoption
```

禁止ルート:

```text
raw reference data
  -> copied score table / copied prompt phrase
  -> tracked runtime data
```

### 5.2 Candidate metadata contract

将来の curated data には、最低限次を含める。

- `id`
- `slot`
- `text`
- `source_hint`
- `rewrite_reason`
- `risk_note`
- `mode`

必要に応じて:

- `personality`
- `emotion`
- `action_keys`
- `object_tokens`
- `relation_keys`
- `location_keys`
- `debug_tags`
- `mood_keys`
- `reject_context_terms`

### 5.3 Validator expansion

新しい curated data を追加する場合、`asset_validator.py` は次を確認する。

- schema_version
- duplicate id
- non-empty text
- unknown slot
- semantic-only policy violation
- copied-looking raw score fields の禁止
- mode が `off` / `passive` / `active` のいずれか
- optional list fields (`personality`, `mood_keys`, `reject_context_terms`, `debug_tags`) が文字列配列であること

### 5.4 Audit expansion

active 前には必ず次を比較する。

- passive prompt
- active prompt
- changed domain
- prompt length delta
- semantic-only policy issues
- selected descriptor rank
- fallback rate
- context reject rate

既存 `tools/audit_semantic_epig_outputs.py` を拡張するか、subject-centric 専用 audit を追加する。

---

## 6. Verification gates

### 6.1 Docs / test-only stabilization

```bash
python -m unittest assets.test_action_semantics assets.test_action_generator
python tools/validate_prompt_data.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

### 6.2 Candidate audit regeneration

```bash
python tools/audit_subject_centric_descriptors.py --reference-root "..\参考" --output assets/results/subject_centric_descriptor_candidates.json
python tools/extract_epig_reference_overlay.py --reference-root "..\参考" --output assets/results/epig_reference_overlay.local.json
python tools/audit_reference_dimension_projection.py --reference-root "..\参考" --output assets/results/reference_dimension_projection.json
python tools/audit_llm_expanded_prompt_policy.py --reference-root "..\参考" --output assets/results/llm_expanded_prompt_policy_audit.json
python tools/review_reference_refresh_adoption.py --results-dir assets/results --output assets/results/reference_refresh_adoption_decision.json
```

### 6.3 Before passive runtime integration

```bash
python -m unittest assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_policy
python tools/validate_prompt_data.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

### 6.4 Before active runtime adoption

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/audit_semantic_epig_outputs.py --samples assets/fixtures/semantic_epig_audit_cases.json --seed-count 8 --output assets/results/semantic_epig_audit_subject_centric_adoption.json
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python assets/calc_variations.py --json
```

---

## 7. Definition of Done

この wave は次を満たすと完了。

- 古い absolute reference path が docs の再実行手順から排除されている。
- `relation_keys` descriptor matching が専用 test で固定されている。
- subject-centric candidate triage 方針が docs と tasks に明文化されている。
- local generated reports の再生成手順が整理されている。
- raw reference data / score-bearing overlay を tracked data にしていない。
- 小さな repo-authored subject-centric descriptor 採用の schema / validator / passive-first 方針が決まっている。
- active runtime 採用は audit と snapshot が揃った narrow wave のみ許可される。
- 将来の emotion/action/dominance 拡張にも同じ adoption pipeline を使える。
