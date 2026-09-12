# Semantic Diversity / Natural Language Refactor Specification

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
基準ブランチ: `main`
作成日: 2026-09-06
正本:
- [`docs/diversity_refactor/spec.md`](./spec.md)
- [`docs/diversity_refactor/tasks.md`](./tasks.md)
- [`docs/diversity_refactor/progress.md`](./progress.md)

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

## 6.2 Locked signature model — A1.1 (2026-09-06)

本節〜6.6 は `effective-diversity-audit/v1` の normative contract。
実装は A1.2–A1.4、基準計測は A1.5、改善閾値の決定は A1.6 で行う。
この契約の変更時は contract hash を更新し、旧レポートを新契約の証拠に流用しない。

### Input and metadata boundary

- Generator は `tools/workflow_prompt_runner.py:build_canonical_record(s)` を再利用する。
  1 report は1 workflow/profile/override 構成を対象とする。複数 workflow を混ぜない。
- `final_context`、型付き `ActionFrame`、既存 resolver、選択済み node decision が正本。
  `cleaned_prompt` / `raw_prompt` の解析で意味署名を作らない。
- `ContentPlan.semantic_slots` は現状テンプレートの placeholder を含むことがあるため、
  subject/action/object の canonical identity として直接使用しない。
- 標準 runner の `final_context` は node 7（Garnish）の出力。
  `ContextPromptBuilder` は公開出力が prompt のみで、内部の更新 context/debug は破棄される
  (`nodes_context.py:ContextPromptBuilder.build_prompt_context`)。
  出力 selector の変更だけでは builder debug を得られない。
- A1.4 では該当 builder の `execution_trace.inputs` を取り、公開 node と同じ
  `core.context_codec.context_from_json(context_json, default_seed=int(seed))` を通して
  `pipeline.prompt_orchestrator.build_prompt_from_context(context, template, composition_mode, seed)`
  を read-only replay する。run_seed ではなく trace に解決済みの builder seed を使う。
  replay prompt とその builder を指す `raw_prompt` を文字列完全一致で照合したときだけ
  replay context の最後の `ContextPromptBuilder.decision` を採用する。
- 上記は既存 builder の観測用再実行であり、別 workflow runner・新 node・public I/O 変更を作らない。
  対象 builder は raw_prompt selector の node ID で特定する。複数の曖昧な builder、
  不一致、取得不能はエラーにし、推測した syntax や別 node の history で埋めない。
- `syntax_family` は一致確認済み decision の `syntax_family`（v2）→
  `content_plan.syntax_family`（v1）の順。双方が存在し不一致ならエラー。
  composition_mode=false など metadata が存在しない経路は `null`。
  文の数・句読点・template key から family を推定しない。

### Signature fields and sources

`semantic_signature_v1/core` は次の4 key を常に持つ JSON object。
値は非空 canonical string または JSON `null`。空文字や `"unknown"` を category にしない。

| Field | Fixed source / resolution order |
|---|---|
| `canonical_subject` | `resolve_character(raw=ctx.subj, source_subj_key=extras.source_subj_key, character_name=extras.character_name)` の `profile_key` → `compatibility_key`。表面の `girl` に主体を一括変換しない。未解決は null |
| `canonical_location` | `location_service.resolve_location_key(ctx.loc)`。未解決なら `extras.raw_loc_tag` を同 resolver へ渡す。未解決は null |
| `action_family_or_main_verb` | 有効な ActionFrame.main_verb を軽量正規化して `verb:<value>`。欠損時は既存 `pipeline.action_parser.action_verb(ctx.action)` の結果。これも空なら選択済み slots.purpose の既存 scene-axis key を `purpose:<key>`。新しい類義語辞書や stemming を追加しない |
| `primary_object_or_object_family` | 有効な ActionFrame.primary_object。欠損時は選択済み slots.primary_action（なければ ctx.action）に既存 `object_focus_service.extract_action_object_flags` を適用し、結果が1 family の場合だけ採用する。0件または複数で primary を確定できなければ null |

ActionFrame は `core.context_state.generation_state_from_context` の既存 stale-frame 検査を維持する。
`legacy_text` と ctx.action が一致しない frame を採用しない。
一致確認済み builder replay の action_frame を優先し、通常 record しかない場合は
有効な extras.action_frame → 最新の該当 SceneVariator decision の action_frame/slots の順に使う。
古い history の action/slot を新しい action の証拠にしない。
ActionFrame 不在でも既存の action field / resolver で core を作れるが、欠損は明示する。

`semantic_signature_v1/frame` は core の4 key に以下を加える。全 key を常に出力する。

| Field | Type and fixed source |
|---|---|
| `posture` | string/null。有効 frame.posture の先頭が既存 `action_parser.STANCE_STARTERS` の語境界に一致する場合、その stance key。他は null |
| `hand_action_family` | string array/null。有効 frame.hand_action に `core.semantic_families.semantic_families_for_text` を適用した family 集合 |
| `gaze_target_family` | string array/null。有効 frame.gaze_target に既存 `extract_action_object_flags` を適用した object-family 集合。viewer 関係は social_relation で記録 |
| `progress` | string/null。frame.progress または既存 slots.progress_state の scene_axis.progress key |
| `stimulus_or_obstacle` | string/null。frame.stimulus_or_obstacle または slots.obstacle_or_trigger の scene_axis.obstacle key |
| `social_relation` | string/null。frame.social_relation または slots.social_distance の scene_axis.social_distance key、または既存 solo-safe key `viewer` |
| `mood` | string/null。extras.raw_mood_key → meta.mood のうち mood_map.json の key と一致する値。展開済み mood 英文は署名に入れない |
| `clothing_family` | string/null。最新の ContextClothingExpander decision.chosen_type があれば選択済み type ID として直接採用。欠損時だけ decision.theme → ctx.costume を既存 `clothing_service.resolve_clothing_theme` で解決する。装飾付き clothing_prompt は使わない |
| `garnish_family` | string array/null。最新の ContextGarnish decision.final_tags の選択済みタグ集合に `semantic_families_for_tags` を適用。decision がなければ extras.garnish を既存 split_semantic_tags で分割して同じ関数へ渡す |

- 文字列は Unicode NFC → lowercase → trim / 連続 whitespace を1 space にする。
  canonical resolver の ID はこの軽量正規化後に保存。stemmer、語順変更、単語削除はしない。
- family array は辞書順で整列し重複を除く。入力 slot が欠損または非空なのに分類不能なら null。
  選択結果が明示的に空（例: final_tags=[]）なら []。null は「不明」、[] は「観測済みの空」。
- 抽出元・fallback・未解決 field は別の `diagnostics` に保持し、署名の一部にしない。
  seed、debug 全文、prompt、template key、syntax family、history は署名から除外する。
- subject/location/action の3 field が非nullなら valid core とする。object は欠損可能。
  valid frame は valid core に上記 projection を加えたもの。任意 slot の null も比較対象だが、
  field 別 missing_count を必ず併記する。欠損が多い frame を完全な意味の識別と称しない。
- この有限分類は粗い projection であり、すべての同義語や object 差を識別する保証はない。
  表面だけの変更は core を変えず、認識済みの main verb / primary object の変更は core を変える。
  hand/gaze/garnish の英語全文や ContentPlan placeholder を追加して unique 数を稼がない。

## 6.3 Locked metrics

### Prefixes and ordering

- record は整数 run_seed の昇順。重複 seed、bool seed、異なる workflow/config の混在はエラー。
- CLI は `seed_start + i`（i=0..sample_count-1）の連番を既存 runner に渡す。
  各 record は同じ workflow 初期 history/context から開始し、前 record の出力を次へ注入しない。
- 正式 prefix は `[128, 512, 2048, 8192]` のうち実 sample_count 以下だけ。
  実 sample_count がこの列にない場合、その値の prefix も追加する（小さい unittest を許可）。
  正数でない CLI sample_count はエラー。pure helper の空入力だけ `"0"` prefix を許可する。
- `prefixes` は昇順 integer array。各 metric group は同じ prefix を十進 string key で持つ。
  例: smoke は `"128"` のみ、gate は `"128"`, `"512"`, `"2048"`。
  N未満の標本を `@N` と表示せず、取得失敗 record を黙って分母から除かない。

### Metric payload (for each prefix N)

全 integer count は非負、ratio/entropy は有限 float（reference が空の coverage rate だけは null）。計算途中は丸めず、出力時のみ小数6桁に
`round(value, 6)`。entropy の加算は family key の辞書順。NaN/Infinity は出力しない。

| Path under `metrics` | Required fields and formula |
|---|---|
| `semantic_unique[N].core` / `.frame` | `sample_count=N`, `valid_count=V`, `missing_count=N-V`, `unique_count=U`, `rate=U/N`。U は valid signatures の canonical JSON の種類数。N=0 は rate=0.0 |
| `coverage[N][axis]` | `observed_unique_count=|O|`, `covered_unique_count=|O∩R|`, `reference_count=|R|`, `missing_count`, `out_of_reference_values=sorted(O-R)`, `rate=|O∩R|/|R|`。R が空なら rate=null（未測定） |
| `repetition[N]` | `sample_count=N`; 下記4 duplicate rates と2 run lengths |
| `syntax_entropy[N]` | `sample_count=N`, `valid_count=M`, `missing_count=N-M`, `active_family_count=K`, `family_counts`, `raw_entropy`, `normalized_entropy`, `dominant_family_share` |

`coverage` の8 axis は固定:

```text
subject location action_family primary_object_family
mood clothing_family garnish_family syntax_family
```

対応は core.canonical_subject / core.canonical_location / core.action_family_or_main_verb /
core.primary_object_or_object_family / frame.mood / frame.clothing_family / frame.garnish_family /
観測した syntax_family。v1 の action_family は上記 verb/purpose projection であり、
D3.4 の scheduler diversity key 選択を先取りしない。
array は各 record 内で集合として扱い、重複 family を複数回数えない。null は O/R から除外して
missing_count に数える。[] は既知の空なので O に値を足さず、missing にも数えない。
aggregate coverage は v1 では出さず、必ず axis 別値を残す。

`repetition[N]` の field / 定義:

- `exact_prompt_duplicate_rate = (N - unique(cleaned_prompt))/N`。
- `normalized_prompt_duplicate_rate = (N - unique(normalized_prompt))/N`。
- `semantic_core_duplicate_rate = (valid_core_count - unique_core_count)/N`。
- `semantic_frame_duplicate_rate = (valid_frame_count - unique_frame_count)/N`。
- 上記は「最初の出現以外の重複」の割合。重複 group に属する全 record の割合や文内 n-gram 重複率と混同しない。
  semantic signature 欠損を重複として数えない。全入力の欠損率は semantic_unique に残す。
- `max_consecutive_same_action_family` / `max_consecutive_same_syntax_family` は
  seed 昇順での最長連続一致数。null は連続を切断し、自身は数えない。空入力/全欠損は0。
- N=0 の duplicate rates はすべて0.0。cleaned_prompt が非string または空白だけなら入力エラー。
  空 prompt を有効な「多様な」出力として数えない。

`syntax_entropy[N]`:

- `active_syntax_families` は config で宣言した、該当 renderer 経路で選択可能な family の整列済み集合。
  K はこの集合のサイズで、観測できた family 数から逆算しない。
- 現行 composition_mode=true の K=2:
  `single-sentence-scene-tail`, `two-sentence-scene-tail`。
  v2 は実装済みかつ有効な family を宣言する。計画だけの6 family は数えない。
- `family_counts` は active family をすべて含め、未観測は0。null は別途 missing_count。
  宣言外の非null syntax family は config/metadata 不整合としてエラー。
- M は nonnull syntax の record 数。`p_i=count_i/M`, `H=-Σ(p_i*log2(p_i))`。
  加算対象は count_i>0 の family のみ（0 log2(0) は0と定義）。
  M=0 なら H=0.0。`normalized_entropy=H/log2(K)`、K<=1 は0.0。
  `dominant_family_share=max(count_i)/M`、M=0 は0.0。
- K/M/missing_count と raw H を必ず併記し、metadata 欠損で entropy が改善したと称しない。
  legacy 経路で構造 metadata がなければ active_syntax_families=[]、syntax 全欠損として報告する。

### Prompt normalization (`effective-diversity-normalization/v1`)

exact の比較対象は runner の cleaned_prompt 文字列そのまま。
normalized は次の順序だけを適用し、runtime PromptCleaner を変更しない。

1. Unicode NFC、lowercase。
2. U+2018/U+2019 を ASCII apostrophe、U+201C/U+201D を ASCII double quote、
   U+2013/U+2014 を ASCII hyphen に置換。
3. 既存 `pipeline.prompt_realizer.normalize_subject_to_girl` と同じ alias 規則を再利用:
   1woman / 1lady / 1female / 1girl / woman / women / lady / female → girl（語境界）。
   これは prompt 比較専用。意味署名の subject resolver に適用しない。
4. ASCII `. , ; : ! ?` の各連続列を1 space に置換。
   apostrophe/hyphen、数字、他の語は保持する。
5. whitespace を1 space に縮約して前後を除去。

例: `A woman reads, quietly.` と `a girl reads quietly!` は同一 normalized prompt。
`a girl doesn't read` と `a girl does read` は異なる。
単語集合への変換、stemmer、stopword/negation 削除、自由な synonym 置換を禁止する。

## 6.4 Locked report envelope and provenance

以下は key/type の仕様（sample record を追加することは A1.4 の任意機能）。

```text
schema_version: "effective-diversity-audit/v1"
status: "ok"
profile: "smoke" | "gate" | "release"
source_hash: sha256 of canonical source_identity
source_identity:
  source_tree_hash: existing build_source_manifest(root).source_tree_hash
  supplemental_inputs: [{path: repository-relative POSIX path, sha256: file SHA256}]
workflow_hash: runner base_workflow_hash
effective_workflow_hash: runner effective_workflow_hash
runner_config_hash: runner config_hash
config_hash: sha256 of canonical audit_config
audit_config:
  runner_config_hash: as above
  signature_versions: {core: "semantic_signature_v1/core", frame: "semantic_signature_v1/frame"}
  normalization_version: "effective-diversity-normalization/v1"
  contract_sha256: raw bytes SHA256 of docs/diversity_refactor/spec.md
  active_syntax_families: sorted unique strings
seed_start: integer
sample_count: positive integer
prefixes: sorted integer array
records_sha256: SHA256 of concatenated canonical runner records in seed order
reference_universe: {schema_version, source_hash, effective_workflow_hash, config_hash,
                     seed_start, sample_count, records_sha256, axes, reference_hash}
diagnostics:
  signature_missing_counts: {core: {field: count}, frame: {field: count}}
  extraction_sources: {field: {source_label: count}}
  builder_replay: {checked_count: integer, mismatch_count: 0}
metrics: {semantic_unique: {N: ...}, coverage: {N: ...},
          repetition: {N: ...}, syntax_entropy: {N: ...}}
```

- SHA256 は lowercase 64 hex。`canonical_json_bytes` は既存 runner utility を直接再利用する:
  UTF-8 / ensure_ascii=false / sort_keys=true / compact separators / allow_nan=false / 末尾LF。
  ordered record の順は seed 順のまま保持する。
- `tools.prompt_quality_loop.build_source_manifest` は runtime/tools/tests 等の raw bytes と
  versioned rules を既に含むため再実装しない。ただし root の `prompts.jsonl`, `mood_map.json`,
  `templates.txt` は含まれないため supplemental_inputs へ必ず追加する。
  他の file input を使う場合も実際の読み込み対象を同 manifest または supplemental_inputs に束縛する。
  supplemental_inputs は path 順、重複なし。未束縛または repository 外の file input は v1 CLI では拒否する。
- source/config/workflow を実行前後に確認し、変更時はエラー。古い cache を受け入れない。
  Source manifest は docs を含まないため contract_sha256 を config に明示する。
  progress.md の更新は契約hashに含めない。
- config_hash は抽出・正規化・renderer構成の identity。sample_count/seed_start/profile は
  envelope に明示し、基準 probe と測定 prefix が同じ config を共有できるよう audit_config へ入れない。
- report 内に自己参照の report hash、実行日時、経過時間、hostname、絶対出力先を入れない。
  report file SHA256 は外部 receipt / progress.md で記録する。
- エラーは `status: "error"`, `schema_version: "effective-diversity-audit/v1"`,
  `error: {code: stable string, details: canonical object}` を出し非0終了。
  エラー時に成功 metrics を発行しない。code は A1.4 で列挙し、失敗を skipped sample に置き換えない。

## 6.5 Reference universe and audit profiles

`effective-diversity-reference/v1` は同一 source_hash / effective_workflow_hash / config_hash の
固定 probe に現れた到達可能値の集合。辞書内の全語彙数や150,184を coverage の分母にしない。
有限 probe の観測範囲であり、全到達可能空間の証明ではない。

| Profile | Measured N | Reference probe (seed start / count) | Intended use |
|---|---:|---|---|
| smoke | 128 | 0 / 128 | task execution smoke; own reference, no promotion claims |
| gate | 2048 | 0 / 8192 | phase/baseline measurement |
| release | 8192 | 0 / 8192 | final adoption measurement |

- `--sample-count` / `--seed-start` は測定側のみを上書きする。reference は明示的に固定し、
  入力値が変わるたびに観測結果に合わせて伸縮させない。unittest では小さな固定 reference fixture を渡してよい。
- `reference_universe.axes` は8 axis の sorted unique nonnull string arrays。
  garnish の集合は各 member を列挙する。reference_hash は同 object の reference_hash key を
  除いた canonical JSON bytes の SHA256。K の active syntax 集合と、probe 観測の syntax 集合は別物。
- gate/release は source/config 等が完全一致する保存済み reference を再利用できる。
  初回は8192 probeを1回生成し、測定区間と重なる record を再利用して二重生成を避ける。
  task ごとに gate/reference生成を繰り返さない。smoke の128 universe を gate の証拠に流用しない。
- out-of-reference 値は coverage の numerator に加算せず、値一覧を明記する。
  例: R={a,b,c,d}, O={a,b,x} は observed=3, covered=2, reference=4, rate=0.5, outside=[x]。
  reference をその場で拡張して報告値を改善しない。
- before/after の比率を直接比較する場合は、同じ prefix/seed/context と抽出契約、同じ axis の
  reference values を要求する。source が変わった candidate には candidate自身の probe証拠が必要。
  axis の分母が変わったときは observed/covered/reference の実数と相違を示し、比率改善だけで採用しない。
  共通比較 universe が必要になった場合は A1.6 で別途 lock する。
- syntax normalized entropy は宣言した K に対する分布の均等度。
  v1/v2 で K が変わる場合は両方の K、family counts、raw entropy を提示する。
  その比率だけで family 数の増加や意味多様性の改善を主張しない。

## 6.6 Calculable acceptance examples for A1.2–A1.4

次は実装テストに転記できる小さな数値例で、promotion threshold ではない。

| Input | Expected result |
|---|---|
| empty pure-helper input, empty reference, K=0 | uniqueness/repetition/entropy=0.0; run=0; coverage rate=null; counts=0 |
| 4 valid identical signatures/prompts; syntax=[a,a,a,a], active=[a,b] | U=1, unique rate=0.25, duplicate rates=0.75; syntax H=0, normalized H=0, dominant=1, run=4 |
| 4 unique signatures; syntax=[a,b,a,b], active=[a,b] | unique rate=1, semantic duplicate rate=0; H=1, normalized H=1, dominant=0.5, syntax run=1 |
| syntax=[a,a,a,b], active=[a,b] | H=0.811278, normalized H=0.811278, dominant=0.75, run=3 |
| syntax=[a,a,null,a], active=[a,b] | M=3, missing=1, H=0, dominant=1, run=2 (null separates runs) |
| syntax=[a,a], active=[a] | K=1, H=normalized H=0.0 |
| 4 records, 2 valid identical core and 2 invalid core | U=1,V=2,missing=2; unique rate=0.25, semantic duplicate rate=0.25 |
| garnish=[hands,hands,gaze] in one record, reference=[gaze,hands,breath] | observed=covered=2, reference=3, coverage=0.666667 |
| input records reorder with the same unique seeds | canonical metrics and records hash unchanged after seed sorting |
| normalized prose changes but canonical frame is unchanged | normalized prompt metric may change; core/frame signatures unchanged |

A1.3 tests must additionally cover stale/missing ActionFrame, resolver aliases, recognized object/verb
changes, sorted family arrays, known empty vs unknown, and no final-prose-derived semantic identity.
A1.4 tests must cover builder replay parity failure, unknown syntax metadata, out-of-reference values,
source/contract/corpus hash changes, duplicate seeds, invalid profile/sample count, canonical rerun equality.

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
