# EPIG的 Semantic Enrichment 実装仕様書

対象リポジトリ: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
対象ブランチ: `dev`
対象範囲: 提案 1〜5

- 1. 動作・ジェスチャー
- 2. 物体との相互作用
- 3. 場所・シーン演出
- 4. 衣装・TPO
- 5. キャラクター性・人格の視覚化

関連ファイル:

- `progress.md`
- `tasks.md`

---

## 1. 背景と狙い

EPIG の本質は、感情語を単純に追加することではなく、抽象的な意図を構造化された意味空間へ写し、近い descriptor を選び、subject / stimulus / context などの役割へ結びつけることにある。

このリポジトリには、すでに感情表現について EPIG 的な処理が入っている。現在の garnish 実装は、`emotion_vad.py` の VAD 距離・relevance・descriptor ranking を使い、`ContextGarnish` で expression / gaze / behavior などの身体表現へ落としている。

今回の実装では、この考え方を感情以外へ広げる。

```text
抽象語・高次カテゴリ
  ↓
カテゴリ別 semantic space / axis profile
  ↓
descriptor ranking
  ↓
role-aware slot binding
  ↓
既存 context_json / prompt fragment に反映
```

最終目標は、画像生成プロンプト内で次の問題を減らすこと。

- 動詞はあるが、動作として成立して見えない
- 物体は出るが、使われていない
- 場所は出るが、混雑度・活動感・秩序感などのシーン属性が曖昧
- 衣装がテーマ名には合うが、場所・天候・動作に合わない
- personality が単なる雰囲気語になり、姿勢・視線・手の動きに変換されない

---

## 2. 実装原則

### 2.1 既存方針を壊さない

このリポジトリは `context_json` を中心にした context-first 構成で、ランタイムロジックは `pipeline/`、スキーマ・context 操作は `core/`、語彙データは `vocab/data/` に分離されている。新規実装もこの境界を守る。

### 2.2 semantic-only を維持する

新規 descriptor は semantic content に限定する。

許可:

- subject / role / character profile
- clothing theme / clothing detail
- location / environment context
- action / state / small event
- mood nuance / staging / garnish

禁止:

- camera angle / lens / framing / depth of field
- quality tag / art style / render effect
- body type / body shape emphasis
- exact text rendering / exact count control

### 2.3 public node UI は原則変更しない

初期実装では `nodes_context.py` の public input / output spec を変更しない。

理由:

- 既存 workflow widget round-trip の破壊リスクが高い
- 既存ノードの `context_json` optional chaining を維持したい
- Codex による段階 PR でテストしやすい

有効化・無効化は当面、JSON config と module-level fallback で扱う。

### 2.4 seed 再現性を維持する

- semantic ranking 自体は deterministic にする
- 乱択が必要な場合は既存の `rng` / `mix_seed()` に乗せる
- 同じ input / seed / config から同じ prompt fragment が出ること

### 2.5 training-free / black-box 前提

画像生成モデル本体、LoRA、ControlNet、VLM 評価ループは今回の範囲外。

---

## 3. 共通アーキテクチャ

### 3.1 新規共通モジュール

追加:

```text
vocab/semantic_space.py
pipeline/semantic_epig.py
vocab/data/semantic_epig_config.json
```

#### `vocab/semantic_space.py`

カテゴリ非依存の距離計算・ranking utility。

必須関数:

```python
Vector = dict[str, float]

def clamp01(value: float) -> float: ...
def normalize_vector(vector: dict, axes: list[str]) -> Vector: ...
def weighted_distance(left: Vector, right: Vector, axis_weights: dict[str, float] | None = None) -> float: ...
def relevance_from_distance(distance: float, gamma: float = 2.0) -> float: ...
def rank_candidates(
    candidates: list[dict],
    target_vector: Vector,
    axes: list[str],
    *,
    axis_weights: dict[str, float] | None = None,
    gamma: float = 2.0,
    text_key: str = "text",
    vector_key: str = "vector",
) -> list[dict]: ...
def top_window(ranked: list[dict], window_size: int = 3) -> list[dict]: ...
def validate_axis_payload(payload: dict, required_axes: list[str] | None = None) -> list[str]: ...
```

戻り値の `ranked` item は以下を含む。

```python
{
    "text": "holding a tilted teapot",
    "vector": {"motion_energy": 0.35, ...},
    "distance": 0.1234,
    "score": 0.7812,
    "source": "action_slot_descriptors:puring.hand_action[0]",
    "role": "hand_action",
}
```

#### `pipeline/semantic_epig.py`

ランタイム用の共通 config loader / debug helper。

必須関数:

```python
def load_semantic_epig_config() -> dict: ...
def domain_enabled(domain: str, *, active_only: bool = False) -> bool: ...
def semantic_mode(domain: str) -> str: ...  # "off" | "passive" | "active"
def add_semantic_debug(decision: dict, domain: str, payload: dict) -> None: ...
```

初期 config:

```json
{
  "schema_version": "1.0",
  "default_mode": "passive",
  "gamma": 2.0,
  "top_k": 3,
  "top_window": 3,
  "domains": {
    "action": {"mode": "passive"},
    "object_relation": {"mode": "passive"},
    "location_scene": {"mode": "passive"},
    "clothing_tpo": {"mode": "passive"},
    "personality_behavior": {"mode": "passive"}
  }
}
```

`passive` は ranking と debug だけを出し、出力 prompt は変更しない。  
`active` で初めて slot selection / descriptor insertion に反映する。

段階実装では、各ドメインを `passive` → test → `active` の順に進める。

---

## 4. データ設計

### 4.1 共通 payload 規約

すべての semantic asset は次の形を基本にする。

```json
{
  "schema_version": "1.0",
  "axes": ["axis_a", "axis_b"],
  "axis_weights": {
    "axis_a": 1.0,
    "axis_b": 1.0
  },
  "profiles": {},
  "descriptors": {},
  "notes": {}
}
```

値は `0.0`〜`1.0`。

欠損 axis は `0.5` で補完してよいが、validator では warning を出す。

### 4.2 新規データファイル

追加予定:

```text
vocab/data/semantic_epig_config.json
vocab/data/action_semantic_profiles.json
vocab/data/action_slot_descriptors.json
vocab/data/object_relation_profiles.json
vocab/data/location_axis_profiles.json
vocab/data/staging_axis_descriptors.json
vocab/data/clothing_axis_profiles.json
vocab/data/personality_behavior_profiles.json
```

`asset_validator.py` の banned-term 検査対象へ上記ファイルを追加する。

---

## 5. 提案1: Action EPIG

### 5.1 目的

`running`, `pouring`, `reading`, `waiting` のような抽象的な動詞・目的を、画像内で動作が成立して見える視覚証拠へ分解する。

```text
Action label / purpose
  ↓
posture / hand_action / gaze_target / progress / relation evidence
```

### 5.2 既存接続点

主な変更先:

```text
pipeline/action_generator.py
pipeline/context_pipeline.py
vocab/data/action_semantic_profiles.json
vocab/data/action_slot_descriptors.json
assets/test_action_semantics.py
```

既存 `action_generator.py` には以下の slot がある。

- `purpose`
- `progress_state`
- `social_distance`
- `obstacle_or_trigger`
- `anchor`
- `posture`
- `hand_action`
- `gaze_target`
- `purpose_clause`
- `progress_clause`
- `social_clause`
- `obstacle_clause`
- `optional_micro_action`
- `time_or_weather`

この slot 構造をそのまま使い、候補選択だけ semantic ranking で補強する。

### 5.3 Action axes

```json
[
  "motion_energy",
  "body_openness",
  "precision",
  "object_coupling",
  "social_intensity",
  "time_pressure"
]
```

意味:

- `motion_energy`: 動きの強さ
- `body_openness`: 身体の開き・大きさ
- `precision`: 手元作業の精密さ
- `object_coupling`: 物体との結びつきの強さ
- `social_intensity`: 他者との関わり
- `time_pressure`: 急ぎ・待機・遅延感

### 5.4 `action_semantic_profiles.json` 例

```json
{
  "schema_version": "1.0",
  "axes": ["motion_energy", "body_openness", "precision", "object_coupling", "social_intensity", "time_pressure"],
  "profiles": {
    "study": {
      "vector": {
        "motion_energy": 0.20,
        "body_openness": 0.30,
        "precision": 0.85,
        "object_coupling": 0.75,
        "social_intensity": 0.15,
        "time_pressure": 0.30
      }
    },
    "commute": {
      "vector": {
        "motion_energy": 0.65,
        "body_openness": 0.45,
        "precision": 0.35,
        "object_coupling": 0.45,
        "social_intensity": 0.60,
        "time_pressure": 0.80
      }
    }
  }
}
```

### 5.5 `action_slot_descriptors.json` 例

```json
{
  "schema_version": "1.0",
  "axes": ["motion_energy", "body_openness", "precision", "object_coupling", "social_intensity", "time_pressure"],
  "slots": {
    "posture": [
      {
        "text": "leaning in over what she is doing",
        "vector": {"motion_energy": 0.25, "body_openness": 0.30, "precision": 0.80, "object_coupling": 0.70, "social_intensity": 0.10, "time_pressure": 0.35}
      }
    ],
    "hand_action": [
      {
        "text": "hands staying precise and controlled",
        "vector": {"motion_energy": 0.30, "body_openness": 0.30, "precision": 0.90, "object_coupling": 0.60, "social_intensity": 0.10, "time_pressure": 0.35}
      }
    ]
  }
}
```

### 5.6 Runtime behavior

新規:

```text
pipeline/action_semantics.py
```

関数:

```python
def build_action_target_vector(
    purpose: str,
    progress_state: str = "",
    social_distance: str = "",
    obstacle_or_trigger: str = "",
    loc: str = "",
    action_text: str = "",
    selected_objects: set[str] | None = None,
) -> dict: ...

def rank_action_slot_options(slot_name: str, options: list[str], target_vector: dict, loc: str = "") -> list[dict]: ...

def choose_action_slot_semantic(
    slot_name: str,
    options: list[str],
    rng,
    *,
    target_vector: dict,
    loc: str,
    fallback_choice_fn,
    debug: dict,
) -> str: ...
```

変更箇所:

- `build_action_slots()` 内の `choose_slot()` を semantic-aware にする
- `passive` mode では既存 `_weighted_slot_choice()` の出力を使い、ranking だけ decision に出す
- `active` mode では既存 object/recent penalty と semantic score を掛け合わせる

推奨 scoring:

```text
existing_weight = repetition/object policy weight
semantic_score = relevance(candidate_vector, target_vector)
final_weight = existing_weight * (0.50 + semantic_score)
```

### 5.7 DebugInfo

`ContextSceneVariator` の decision に追加:

```json
{
  "semantic_epig": {
    "action": {
      "mode": "passive",
      "target_vector": {},
      "slot_rankings": {
        "posture": [{"text": "...", "score": 0.82, "distance": 0.12}],
        "hand_action": []
      },
      "selected_by_semantic": false
    }
  }
}
```

### 5.8 Acceptance criteria

- `passive` mode では既存 prompt snapshot が変わらない
- `active` mode では同じ seed で deterministic
- `study` は precision / object_coupling の高い hand/gaze が選ばれやすい
- `commute` は time_pressure / motion_energy の高い posture/gaze が選ばれやすい
- 既存 object/recent repetition guard は維持される

---

## 6. 提案2: Object Relation EPIG

### 6.1 目的

物体を「存在」ではなく「使用関係」として prompt に結びつける。

```text
book が出る
  ↓
open book / hand holding book / gaze toward pages
```

### 6.2 既存接続点

主な変更先:

```text
object_focus_service.py
pipeline/action_generator.py
vocab/data/object_relation_profiles.json
assets/test_object_relation_semantics.py
```

現在の `object_focus_service.py` は object pattern、object concentration policy、slot object policy weight を持っている。ここに relation schema を追加する。

### 6.3 Data schema

```json
{
  "schema_version": "1.0",
  "relations": {
    "book:reading": {
      "object": "book",
      "verbs": ["reading", "reviewing", "studying"],
      "required_roles": {
        "hand_action": ["holding an open book", "one hand supporting the book"],
        "gaze_target": ["eyes lowered toward the pages"],
        "object_state": ["open pages visible"]
      },
      "forbidden_patterns": ["closed book in the background", "book floating nearby"]
    }
  }
}
```

初期対応 object:

- `book`
- `phone`
- `coffee`
- `drink`
- `screen`
- `microphone`
- `surfboard`

### 6.4 Runtime behavior

新規関数:

```python
def load_object_relation_profiles() -> dict: ...
def infer_object_relation_key(action_text: str, object_flags: set[str]) -> str: ...
def relation_slots_for_action(action_text: str, object_flags: set[str]) -> dict[str, list[str]]: ...
def apply_object_relation_slots(slots: dict, rng, loc: str, debug: dict) -> dict: ...
```

`build_action_slots()` の後半で、以下の順序で relation を適用する。

1. 既存 slots を生成
2. action text / selected object flags から relation を推定
3. relation slot が既存 slot と矛盾しない場合だけ追加または弱く置換
4. `object_relation` / `object_state` を slots に入れる
5. `render_action_slots()` がそれを clause に含める

### 6.5 Rendering order

`render_action_slots()` の clause order を次のように変更する。

```text
primary
posture
hand_action
object_relation
object_state
gaze_target
optional_micro_action
social_clause
progress_clause
obstacle_clause
time_or_weather
```

ただし重複句は既存 dedupe に通す。

### 6.6 DebugInfo

```json
{
  "semantic_epig": {
    "object_relation": {
      "mode": "active",
      "detected_objects": ["book"],
      "relation_key": "book:reading",
      "applied_slots": {
        "gaze_target": "eyes lowered toward the pages",
        "object_state": "open pages visible"
      },
      "skipped_slots": {
        "hand_action": "existing slot already object-bound"
      }
    }
  }
}
```

### 6.7 Acceptance criteria

- `reading` + `book` で gaze/page/hand relation が増える
- `phone` + `checking` で hand/gaze relation が増える
- object relation は `recent_objects` penalty と競合しない
- relation が不明な object では出力を変えない
- forbidden pattern は prompt に出力しない

---

## 7. 提案3: Location / Scene Axis EPIG

### 7.1 目的

場所を単なる背景 pack ではなく、混雑度・活動量・秩序感・明るさ・親密度・時間圧などの scene axis として制御する。

感情語で `anxious station` と書くのではなく、次のような視覚属性に落とす。

```text
crowd_density: high
activity_level: high
time_pressure: high
orderliness: medium
```

### 7.2 既存接続点

主な変更先:

```text
pipeline/location_builder.py
pipeline/mood_builder.py
vocab/data/location_axis_profiles.json
vocab/data/staging_axis_descriptors.json
assets/test_location_semantics.py
```

`location_builder.py` は現在、`environment`, `core`, `props`, `texture`, `time`, `weather`, `crowd`, `fx` から weighted choice している。ここに scene axis による重み補正を入れる。

### 7.3 Scene axes

```json
[
  "crowd_density",
  "activity_level",
  "openness",
  "orderliness",
  "weather_intensity",
  "light_softness",
  "intimacy",
  "time_pressure"
]
```

### 7.4 Data schema

`location_axis_profiles.json`:

```json
{
  "schema_version": "1.0",
  "axes": ["crowd_density", "activity_level", "openness", "orderliness", "weather_intensity", "light_softness", "intimacy", "time_pressure"],
  "profiles": {
    "school_library": {
      "vector": {"crowd_density": 0.20, "activity_level": 0.15, "openness": 0.35, "orderliness": 0.90, "weather_intensity": 0.0, "light_softness": 0.65, "intimacy": 0.50, "time_pressure": 0.15}
    },
    "commuter_transport": {
      "vector": {"crowd_density": 0.85, "activity_level": 0.80, "openness": 0.45, "orderliness": 0.45, "weather_intensity": 0.10, "light_softness": 0.25, "intimacy": 0.15, "time_pressure": 0.85}
    }
  }
}
```

`staging_axis_descriptors.json`:

```json
{
  "schema_version": "1.0",
  "axes": ["crowd_density", "activity_level", "openness", "orderliness", "weather_intensity", "light_softness", "intimacy", "time_pressure"],
  "descriptors": {
    "crowd": [
      {"text": "commuters moving through the background", "vector": {"crowd_density": 0.85, "activity_level": 0.80, "time_pressure": 0.75}}
    ],
    "details": [
      {"text": "neatly arranged shelves", "vector": {"orderliness": 0.90, "activity_level": 0.15}}
    ]
  }
}
```

### 7.5 Runtime behavior

新規:

```text
pipeline/location_semantics.py
```

関数:

```python
def build_scene_target_vector(loc_key: str, action_text: str = "", mood_text: str = "") -> dict: ...
def rank_location_segment_options(section_name: str, options: list[str], target_vector: dict, loc_key: str) -> list[dict]: ...
def weighted_scene_choice(section_name: str, options: list[str], rng, loc_key: str, target_vector: dict, existing_weight_fn) -> str: ...
```

`apply_location_expansion()` は context を持っているので、`expand_location_prompt()` に optional な `action_text` / `mood_text` を渡す。

変更例:

```python
location_prompt, decision = expand_location_prompt(
    loc_tag,
    seed,
    mode,
    lighting_mode,
    recent_objects=recent_prompt_objects(ctx),
    action_text=ctx.action,
    mood_text=ctx.meta.mood,
    return_debug=True,
)
```

### 7.6 Scene target adjustment

初期実装は過度に複雑化しない。

- location base vector を取得
- action keyword で軽く補正
  - commute / waiting / delay: `time_pressure +0.15`, `crowd_density +0.10`
  - study / reading / writing: `orderliness +0.10`, `activity_level -0.10`
  - rest / relax: `activity_level -0.15`, `light_softness +0.10`
  - running / dancing / playing: `activity_level +0.15`, `motion-like` section は crowd/activity へ寄せる
- mood text は直接感情語として使わず、`staging_tags` がある場合のみ低重みで補正

### 7.7 FX 制約

既存 `FX_DENY_PATTERNS` を維持する。

新規 scene descriptor は camera / bokeh / lens flare / render effect を使わない。

### 7.8 Acceptance criteria

- `commuter_transport` + commute action で crowd/time_pressure 系 segment が選ばれやすい
- `school_library` + study action で orderly/quiet 系 segment が選ばれやすい
- `lighting_mode=off` の挙動を壊さない
- `passive` mode では prompt が変わらない
- `active` mode でも banned fx term を出さない

---

## 8. 提案4: Clothing TPO EPIG

### 8.1 目的

衣装を theme だけで選ぶのではなく、場所・天候・動作への適合で rank する。

```text
formal / casual
warmth
movement_freedom
weather_fit
activity_fit
visual_prominence
```

体型・身体強調は扱わない。

### 8.2 既存接続点

主な変更先:

```text
pipeline/clothing_builder.py
vocab/data/clothing_axis_profiles.json
assets/test_clothing_semantics.py
```

`clothing_builder.py` は現在、候補を最大 `CLOTHING_CANDIDATE_ATTEMPTS = 5` 回作り、repeat penalty が低い候補を採用している。ここに TPO semantic score を加える。

### 8.3 Clothing axes

```json
[
  "formality",
  "warmth",
  "movement_freedom",
  "softness",
  "weather_fit",
  "activity_fit",
  "visual_prominence"
]
```

### 8.4 Data schema

```json
{
  "schema_version": "1.0",
  "axes": ["formality", "warmth", "movement_freedom", "softness", "weather_fit", "activity_fit", "visual_prominence"],
  "theme_profiles": {
    "school_uniform": {"vector": {"formality": 0.65, "warmth": 0.45, "movement_freedom": 0.45, "softness": 0.45, "weather_fit": 0.40, "activity_fit": 0.55, "visual_prominence": 0.55}},
    "casual": {"vector": {"formality": 0.25, "warmth": 0.50, "movement_freedom": 0.75, "softness": 0.60, "weather_fit": 0.50, "activity_fit": 0.75, "visual_prominence": 0.40}}
  },
  "pack_profiles": {
    "outerwear:raincoat": {"vector": {"warmth": 0.70, "weather_fit": 0.95, "movement_freedom": 0.55}}
  },
  "location_targets": {
    "modern_office": {"vector": {"formality": 0.70, "visual_prominence": 0.35}},
    "rainy_bus_stop": {"vector": {"weather_fit": 0.90, "warmth": 0.65}}
  },
  "action_targets": {
    "commute": {"vector": {"movement_freedom": 0.75, "weather_fit": 0.70, "visual_prominence": 0.30}},
    "rest": {"vector": {"softness": 0.75, "formality": 0.20}}
  }
}
```

### 8.5 Runtime behavior

新規:

```text
pipeline/clothing_semantics.py
```

関数:

```python
def build_clothing_target_vector(loc: str, action_text: str = "", theme_key: str = "") -> dict: ...
def score_clothing_decision(decision: dict, prompt: str, target_vector: dict) -> dict: ...
def semantic_clothing_penalty(score: float, max_penalty: int = 4) -> int: ...
```

`expand_clothing_prompt()` の候補比較を次に変更する。

```text
existing_repeat_penalty
+ semantic_tpo_penalty
= final_candidate_penalty
```

`passive` mode:

- `semantic_tpo_score` と `semantic_tpo_penalty` を decision に出す
- 採用候補は既存ロジックのまま

`active` mode:

- final penalty で候補選択する

### 8.6 State detail rule との関係

既存 `STATE_DETAIL_RULES` は維持する。

新規 TPO score は state detail rule を置き換えない。  
`wet`, `snow`, `sweaty`, `battle-worn` などの location constraint は今まで通り hard filter として扱う。

### 8.7 DebugInfo

```json
{
  "semantic_epig": {
    "clothing_tpo": {
      "mode": "active",
      "target_vector": {},
      "candidate_scores": [
        {"attempt_index": 0, "score": 0.71, "semantic_penalty": 1, "repeat_penalty": 2, "final_penalty": 3}
      ],
      "selected_attempt_index": 2
    }
  }
}
```

### 8.8 Acceptance criteria

- rainy / winter / gym / office などで不自然な state detail が増えない
- weather/activity fit によって候補選択が変わる
- body-type term は出力しない
- repeat guard は維持される
- `asset_validator.py` が新規 clothing asset を検査する

---

## 9. 提案5: Personality Behavior EPIG

### 9.1 目的

`shy`, `confident`, `serious` などの personality を、直接的なラベルではなく、視線・姿勢・手・距離感などの視覚表現へ変換する。

```text
shy
  ↓
looking slightly away / shoulders drawn inward / holding bag close
```

### 9.2 既存接続点

主な変更先:

```text
vocab/garnish/logic.py
vocab/data/personality_behavior_profiles.json
assets/test_personality_semantics.py
```

現在は `PERSONALITY_GARNISH_BIAS` が inline dict として存在し、`prefer` から 1 つ選んで garnish_pool に入れている。これを data-driven + semantic ranking へ移す。

### 9.3 Personality axes

```json
[
  "sociability",
  "restraint",
  "confidence",
  "curiosity",
  "meticulousness",
  "warmth"
]
```

### 9.4 Data schema

```json
{
  "schema_version": "1.0",
  "axes": ["sociability", "restraint", "confidence", "curiosity", "meticulousness", "warmth"],
  "profiles": {
    "shy": {"vector": {"sociability": 0.25, "restraint": 0.85, "confidence": 0.20, "curiosity": 0.45, "meticulousness": 0.50, "warmth": 0.55}, "prefer_category": "care"},
    "confident": {"vector": {"sociability": 0.75, "restraint": 0.25, "confidence": 0.90, "curiosity": 0.55, "meticulousness": 0.50, "warmth": 0.55}, "prefer_category": "joy"}
  },
  "descriptors": {
    "gaze": [
      {"text": "looking slightly away", "vector": {"sociability": 0.25, "restraint": 0.80, "confidence": 0.25}},
      {"text": "looking directly ahead", "vector": {"sociability": 0.70, "restraint": 0.25, "confidence": 0.85}}
    ],
    "posture": [
      {"text": "shoulders drawn inward", "vector": {"restraint": 0.85, "confidence": 0.20}},
      {"text": "upright composed posture", "vector": {"restraint": 0.45, "confidence": 0.80, "meticulousness": 0.60}}
    ],
    "hands": [
      {"text": "holding her bag close", "vector": {"restraint": 0.80, "confidence": 0.25}}
    ]
  }
}
```

### 9.5 Runtime behavior

新規:

```text
vocab/personality_semantics.py
```

関数:

```python
def load_personality_profiles() -> dict: ...
def personality_vector(personality: str) -> dict | None: ...
def prefer_category_for_personality(personality: str) -> str | None: ...
def rank_personality_descriptors(personality: str, slot: str, candidates: list[str]) -> list[dict]: ...
def pick_personality_descriptor(personality: str, rng, context_loc: str, context_costume: str, action_text: str, existing_tags: list[str], debug: dict) -> str: ...
```

`sample_garnish()` の personality 処理を次に変更する。

1. data file が読める場合は semantic personality を使う
2. 読めない場合は既存 inline `PERSONALITY_GARNISH_BIAS` を fallback とする
3. `prefer_category` は既存 `_resolve_target_emotion()` に渡す
4. descriptor は `_is_out_of_context()` を通す
5. `passive` mode では既存 prefer tag を維持し、ranking debug だけ出す
6. `active` mode では semantic descriptor を採用する

### 9.6 DebugInfo

```json
{
  "semantic_epig": {
    "personality_behavior": {
      "mode": "active",
      "personality": "shy",
      "target_vector": {},
      "slot_rankings": {
        "gaze": [{"text": "looking slightly away", "score": 0.86}],
        "hands": []
      },
      "selected": "looking slightly away"
    }
  }
}
```

### 9.7 Acceptance criteria

- `shy` は away/down/close/restraint 系が選ばれやすい
- `confident` は direct/upright/open 系が選ばれやすい
- `serious` は focused/composed/meticulous 系が選ばれやすい
- action context と矛盾する posture/gaze は既存 filter で落ちる
- emotion VAD の expression/gaze/behavior selection と二重衝突しない

---

## 10. Asset validation

### 10.1 `asset_validator.py`

変更:

- `_TARGETED_BANNED_ASSETS` に新規 JSON を追加
- semantic asset schema validation を追加

新規関数案:

```python
def validate_semantic_axis_asset(filename: str) -> list[str]: ...
def validate_semantic_epig_assets() -> list[str]: ...
```

チェック項目:

- `schema_version` がある
- `axes` が非空 list
- vector 値が `0.0 <= x <= 1.0`
- descriptor text が空でない
- banned domain terms がない
- camera / quality / body-type 系語彙が混入しない

### 10.2 `tools/validate_prompt_data.py`

可能なら新規 semantic assets も読む。  
最低限 `asset_validator.py` 側で担保する。

---

## 11. Test strategy

### 11.1 追加テスト

```text
assets/test_semantic_space.py
assets/test_action_semantics.py
assets/test_object_relation_semantics.py
assets/test_location_semantics.py
assets/test_clothing_semantics.py
assets/test_personality_semantics.py
```

### 11.2 既存テストへの影響

`passive` mode の PR では既存 snapshot が変わらないことを期待する。

`active` mode へ切り替える PR では、影響範囲を明示して snapshot / baseline を更新する。

### 11.3 必須検証コマンド

最小:

```bash
python -m unittest assets.test_semantic_space assets.test_action_semantics assets.test_object_relation_semantics assets.test_location_semantics assets.test_clothing_semantics assets.test_personality_semantics
python -m unittest assets.test_context_nodes assets.test_workflow_samples
python tools/verify_full_flow.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print('issues', len(issues)); print(issues[:20])"
```

ランタイム変更後:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/check_widgets_values.py
```

action pool / variation 周辺を触った場合:

```bash
python tools/build_action_pools.py --check
python assets/calc_variations.py --json
python tools/check_variation_scope.py
```

---

## 12. 実装順序

推奨 PR / Codex セッション順:

```text
M0: baseline verification and docs directory setup
M1: generic semantic_space + config + validator + tests
M2: Action EPIG passive → active
M3: Object Relation EPIG passive → active
M4: Location / Scene Axis EPIG passive → active
M5: Clothing TPO EPIG passive → active
M6: Personality Behavior EPIG passive → active
M7: integration audit, debug cleanup, docs update
```

M2 と M3 は密接なので、M2 で `object_relation` slot の受け皿だけ作り、M3 で relation profile を入れると実装しやすい。

---

## 13. Definition of Done

全体完了条件:

- 1〜5 の domain が `semantic_epig_config.json` で制御可能
- 各 domain に `passive` / `active` mode がある
- active mode で prompt fragment が role-aware に変化する
- context_json schema / public node UI を壊していない
- seed 再現性が維持されている
- semantic-only policy に反する語彙が入っていない
- `asset_validator.py` が新規 asset を検査する
- `DebugInfo.decision.semantic_epig` に判断根拠が出る
- 既存テストと新規テストが通る

---

## 14. 最小サンプル期待値

### 14.1 Action + Object

Input context:

```json
{
  "subj": "a student",
  "loc": "school_library",
  "action": "reading a book",
  "costume": "school_uniform",
  "meta": {"mood": "focus"}
}
```

期待される方向:

```text
a student in school uniform, holding an open book, eyes lowered toward the pages, one hand supporting the book, in a quiet school library ...
```

### 14.2 Scene

Input:

```json
{
  "subj": "a commuter",
  "loc": "commuter_transport",
  "action": "waiting for the next train",
  "meta": {"mood": "tense"}
}
```

期待される方向:

```text
commuters moving through the background, overhead signs, hurried foot traffic, platform crowding
```

### 14.3 Clothing

Input:

```json
{
  "subj": "a woman",
  "loc": "rainy_bus_stop",
  "action": "commuting",
  "costume": "casual"
}
```

期待される方向:

```text
weather-aware outerwear / practical shoes / subdued commuting outfit
```

### 14.4 Personality

Input:

```json
{
  "subj": "a shy student",
  "extras": {"personality": "shy"},
  "action": "standing near the classroom door"
}
```

期待される方向:

```text
looking slightly away, shoulders drawn inward, holding her bag close
```

---

## 15. Codex 実装時の注意

- 大規模リファクタをしない
- 1 セッション 1 domain または 1 utility に絞る
- public node spec の変更は最後まで避ける
- data asset を追加したら validator と unit test を同時に追加する
- output prompt の変更がある PR は、before/after 例を progress に残す
- `passive` mode のテストと `active` mode のテストを分ける
- 既存 inline dict は初期削除しない。data load failure 時の fallback として残す
