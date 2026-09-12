# N2.7-R4.3 — Codex実装計画書
## Producer evidenceの共通化と、実workflowにおける6構文への到達経路の整備

- 対象: `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`
- 作業ブランチ: `refactor/realizer-v2`
- 設計基準HEAD: `9a2aa32c1e3a48d1d7ea51eb91aee42843dba021`
- candidate07コードの履歴上のcommit: `24bbbfbfb7ef7a66d2997f47149d870dfb84e79a`
- 比較対象のstable main: `10d7d8dd6a6dd006f7269bf09aedc5e3624f5c51`
- 作成日: 2026-09-11 JST
- 文書状態: **PROPOSED / 実装前**
- 推奨配置先: `docs/diversity_refactor/r43_implementation_plan.md`
- 成果物の性質: 実装・診断・検証の実行契約。R4.3実装済み、検証PASS、正式採用済みを示すものではない。

> この文書をCodexへ渡したら、まず **R43-00** だけを開始する。以後は依存順に一度に1タスクを実装する。既存の安全条件を緩めず、stable mainへのmerge・push・N2.8有効化は行わない。

---

## 0. Codexへの開始指示

以下をそのまま開始プロンプトとして使用できる。

```text
対象は Shiba-2-shiba/ComfyUI-Scripted-Context-Generator の
refactor/realizer-v2 ブランチです。

この計画書、および CURRENT_STATUS.md、REPO_STRUCTURE.md、
docs/diversity_refactor/{spec,tasks,progress}.md、
docs/diversity_refactor/development_branch.md を読んでください。

まずR43-00を実行し、現在HEAD、worktreeの既存変更、candidate07との差分、
検証環境、A1.6 lock、利用可能なbaseline証拠を記録してください。
ユーザーの既存変更を上書き・reset・cleanしてはいけません。

この文書にある新規API・ファイル・CLIは実装対象であって、既存機能ではありません。
一度に1タスクだけ実装し、タスク開始前と終了時にprogress.mdを更新してください。
Acceptance未達なら次タスクへ進まず、原因を記録してください。

優先順位は、baseline保存 → 計測 → 共通evidence → producerの再構築経路 →
family別の証明 → 統合 → 開発評価です。
seed一覧や完成文allowlistの追加、unknownの安全扱い、測定器の有利な変更、
LLM/NLP依存、V150語彙の大量拡張、Scheduler先行実装は禁止します。

特に、runtime-onlyオブジェクトはノード間のcontext_jsonを越えて届きません。
Builderが実際に持つ既存context/historyだけで再構築可能な範囲と、
監査runnerだけが持つ情報で再生可能な範囲を分けてください。
後者をruntime coverageとして数えてはいけません。

全6 familyの実装宣言、強制描画成功、通常seed選択での実行、v1 fallbackの構造名は
別の数値として記録してください。
64/512は開発上の目安であり、A1.6合格条件でも品質保証でもありません。

R4.3で開発上の成果が出ても、formal評価と必要な採用証拠が揃うまでは
adoption=BLOCKED、N2.8未着手を維持してください。
```

## 1. 目的と完了状態の分離

### 1.1 目的

candidate07で成立した「producer由来の情報と現在の文字列を照合してから構文を変更する」方式を再利用し、次を実現する。

1. Action / Clothing / Scene / Template / Subjectの証拠を、共通の読み取り専用内部型で扱う。
2. producer固有のfamily許可リストではなく、**その入力とその構文に必要な証明**から6 familyを判定する。
3. 実workflowで何が不足しているかをseed×familyの到達可能性監査で特定する。
4. safety・意味・V150・公開API・決定論性を保持したまま、既存より広い入力を処理する。

これは「文章を一般的に理解するNLPエンジン」の開発ではない。既存の生成物を、証明できる構文単位に限って再配置する作業である。

### 1.2 3種類の完了を混同しない

| 状態 | 判定対象 | 何を意味しないか |
|---|---|---|
| `architecture_status=PASS` | 共通型、単一のfamily判定、輸送境界、非回帰 | coverageや品質の改善を保証しない |
| `development_status=PASS` | 実workflowでの到達・適用拡大と開発受入条件 | A1.6の正式合格ではない |
| `adoption_status=ELIGIBLE` | source-bound正式比較、A1.6、適用される品質証拠 | 自動mergeや自動N2.8開始の許可ではない |

開発が成立しても正式証拠がなければ、`adoption_status=BLOCKED`とする。正式に測定した閾値未達は`REJECTED`、未測定や証拠欠損は`BLOCKED`として区別する。

---

## 2. 基準コードから確認できる現在地

本節は設計基準HEADのコード・記録に基づく。数値はリポジトリに記録された過去の測定であり、本計画書作成時にテストを再実行した結果ではない。[S01][S02][S03]

| 項目 | 確認された状態 | R4.3への含意 |
|---|---|---|
| 保存形式 | candidate04–07は通常のGit commitへ展開済み | ZIPを開発の前提にしない |
| candidate07の過去の開発測定 | 実v2適用9/512、fallback込み構造名4種類 | 新しい実測で再確認する |
| branch-native検証記録 | 151 focused tests / 1,888 subtests、29関連回帰 | checkpoint時の160/1,890と集合を混同しない |
| 既知の除外 | `test_actual_v1_family_metadata_and_seed_replay` | 無視せず契約を整理する |
| Action | `_render_action_parts()`をrenderとtraceで共用 | この設計は保持する |
| producer-bound direct経路 | `direct_binding_families()`が最大3 familyを返す | 語彙追加だけでは6構文への経路は揃わない |
| Template | subject/bodyが直接placeholderであること等を要求 | 入力の複雑さとは別にtopology制限を計測する |
| Clothing / Scene | 完成文字列とsource辞書から構成を再構築 | 履歴で候補を絞り、共通constructorへ接続する |
| ComfyUIノード境界 | upstreamは`context_json: STRING`を渡す | ephemeral traceを別ノードからそのまま受け取れない |
| Builder出力 | 公開ノードはpromptだけを返す。内部APIはupdated contextも返す | upstream contextとBuilder debugの比較対象を分ける |
| 正式評価 | 8192参照 / 2048 gate / fixed80は未完了 | 開発監査から正式合格を推定しない |

### 2.1 「最大3 family」の正確な意味

現行`direct_binding_families()`は、`subject_action__scene_tail`を基本に、条件付きで`scene_lead_subject_action`と`subject_scene_action`を加える。[S04]

これは **producer-bound direct経路の制限** であり、別の単純入力経路や人工fixtureまで含めて全コードが3構文しか描画できない、という意味ではない。監査でも経路別に集計する。

### 2.2 前提を補正する重要事項

- `base_pack`、seed、attempt indexがあっても、過去の全ノード入力・履歴・設定が復元できるとは限らない。
- source内に存在する文字列であることは、文法上の名詞句・所有関係・移動可能性の証明ではない。
- 共通dataclassを導入するだけでは、新たな文法的証拠は増えない。
- 既存の語彙は自由文を含む。すべてのnounに`number`等が既にあると仮定しない。
- family許可リストを消すだけでは安全にならない。各familyに対応したconstructorと否定例を先に作る。

---

## 3. 不変条件と対象外

### 3.1 不変条件

- stable `main`のruntimeは変更しない。作業は指定された開発ブランチで行う。
- V150: subjects=135、locations=109、compatibility rows=8,227、base variations=150,184を保持する。
- `Context*` / `PromptCleaner`の公開I/O、`context_json` version、`ActionFrame.to_dict()`、`ContentPlan.to_dict()`の契約を変更しない。
- semantic-only、solo safety、compatibility、Semantic EPIG、既存の選択重み・履歴penaltyを保持する。
- upstreamで選択された人物・衣装・場所・行動・対象物・関係・moodを変更しない。
- `composition_mode=false`は既存rollbackを保持する。
- 同じsource/config/workflow/seed/historyでは同じ出力になることを保持する。
- A1.6の定義・閾値・missing処理・normalization・family mappingを有利に変更しない。
- 新しい監査用evidenceを`extras`や`history`へ保存して、固定比較条件を変えない。

保護対象は正本specに従う。少なくとも次をfeature expansion目的で変更しない。

```text
vocab/data/variation_scope.json
assets/compatibility_review.csv
vocab/source/action_pools/*.json
vocab/data/action_pools.json
```

### 3.2 対象外

LLM・embedding・汎用NLP依存、新しい公開ノード、語彙数拡張、V250/V350/V500、D3 Scheduler、6を超えるfamily、画像生成評価環境の新設、一般purpose English parser、無関係なcleanupは対象外。

### 3.3 出力の保持範囲

**基盤置換段階:** 同じ512入力についてcandidate07のraw/cleaned promptと既存のserialized debugを保持する。監査データは外部receiptへ出す。

**適用拡大段階:** 元のv1 fallback入力が、安全証明後にv2へ変わることは目的に含む。それ以外のfallbackはbyte-identicalを維持する。既存9件の成功例は当面保持する。

family集合拡大で旧成功例の選択まで変わる場合、snapshotを黙って更新しない。次のどちらかを実装前に記録する。

- 既存の受理経路を互換adapterとして優先し、新経路を従来fallbackの入力へ限定する。
- 別の明示的タスクで「旧成功例も構文のみ変更可」という変更契約を先に定め、対比較する。

R4.3の既定は前者。seed番号で互換対象を選んではならない。互換adapterは移行用であり、candidate世代ごとに別の巨大runtimeを複製しない。

---

## 4. 目標アーキテクチャと輸送境界

```text
既存Context + 既存history + Builderに実際に与えられた引数
       │
       ├─ Action: legacy_slotsを同じrendererで再生
       ├─ Clothing: 履歴で選択済packを特定し、完全な入力があれば再生
       ├─ Scene: 既存選択記録を利用し、完全な入力があれば再生
       ├─ Template: 今回選ばれたentryを直接検証
       └─ Subject: 既存profile/constructorとのbindingを検証
       │
       ▼
ProducerTrace: 出所・選択部品・join/dedupe/順序の証拠
       │
       ▼
RealizationEvidence: 文法・主語・所有先・参照・適用可能な変形の証拠
       │
       ▼
prove_family(family, evidence): family固有の全条件を判定
       │
       ▼
construct_family(): そのfamilyに対応する具体的な句を構成
       │
       ▼
既存のseed-based選択 → 実現 → 既存normalizer / PromptCleaner
```

### 4.1 replayの2つの等級

| 等級 | 必要条件 | 言ってよいこと |
|---|---|---|
| `exact_renderer_replay` | 必要な元入力・設定・sourceが特定され、同じrendererを再実行してtext/traceが一致 | その入力条件のproducer replayが一致した |
| `bound_constructor` | 選択済source部品が既存履歴等で絞れ、純粋constructorの再構成が現在textと一致。文法・所有先も一意 | 現在textの構成が証明された。全ノードの過去実行再現ではない |

全入力が不明な場合に既定値を埋めて`exact_renderer_replay`と呼ばない。`bound_constructor`も証明できなければ既存conservative経路かv1 fallbackへ戻す。

### 4.2 runtimeで利用可能な情報だけを使う

`tools/workflow_prompt_runner.py`のexecution traceは、監査では元widget入力やBuilder入力を取得できるが、通常のBuilder入力にその全情報が含まれるわけではない。[S06][S07]

したがって監査上は次を別カウンターにする。

- `runtime_proof`: Builderに実際に届く情報だけで成立。
- `audit_only_replay`: execution trace等の追加情報がなければ成立しない。
- `unavailable`: どちらでも不足する。

`audit_only_replay`をruntime eligible数やformal six-family証拠に加算してはいけない。

### 4.3 ノード間のglobal side channelを禁止

global dict、seed→traceキャッシュ、ファイルを介した暗黙のtrace受け渡し、ノード実行順への依存、別リクエストのtrace再利用は禁止する。`context_json`からBuilderを別processで再実行して同じ結果になる必要がある。

Builder内部の`producer_context`引数は、**受信済みcontext/historyからその呼び出しの中で構成する**。まだ存在しない過去入力を入れない。大きなtraceは返却contextへ追加せず、監査sinkへ出す。

### 4.4 source bindingと文法判定を分離

`OriginProof`が成立しても`ClauseEvidence.grammar_known`は自動的にTRUEにならない。

例: `props`に登録されているだけで名詞句と断定しない。`gaze_target`にあるだけで主人公本人が文法上の主語とは断定しない。`with`挿入、冠詞挿入、動詞活用、関係節化にはそれぞれ明示的なrule IDとテストを必要とする。

---

## 5. dataclass案

以下は **新規設計案**。既存の名前ではない。Python 3.10互換の標準ライブラリだけを使う。型は契約を表すための最小形であり、不要なfieldは削ってよいが、unknown・出所・主語とownerの区別を潰してはいけない。

推奨配置: `pipeline/realization_evidence.py`。`core/schema.py`へは追加しない。

```python
from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Truth(Enum):
    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


Domain = Literal["subject", "clothing", "action", "scene", "template", "garnish", "mood"]
ProofMode = Literal["exact_renderer_replay", "bound_constructor"]


@dataclass(frozen=True)
class SourceRef:
    domain: Domain
    producer: str                  # 例: pipeline.action_renderer
    field: str                     # 例: primary_action / core / colors
    catalog_key: str | None         # source entryが特定できない場合はNone
    selected_text_sha256: str       # 正規化前の選択文字列にbinding


@dataclass(frozen=True)
class ProducerPart:
    part_id: str                   # 選択済み部品内の決定論的ID
    source: SourceRef
    text: str


@dataclass(frozen=True)
class ProducerTrace:
    mode: ProofMode
    producer: str
    source_tree_hash: str
    input_binding_sha256: str
    raw_output_sha256: str
    emitted_output_sha256: str     # sanitize後の現在textと照合
    parts: tuple[ProducerPart, ...]
    emitted_part_ids: tuple[str, ...]  # shuffle後の順序
    omitted_parts: tuple[tuple[str, str], ...]  # ID, 既存抑制rule ID
    constructor_id: str


@dataclass(frozen=True)
class ClauseEvidence:
    atom_id: str
    source_part_ids: tuple[str, ...]
    source_text: str
    grammar_known: Truth
    grammatical_subject_id: str | None  # protagonist / body:eyes / scene:0 等
    owner_id: str | None                # grammatical subjectとは別
    form: str                          # noun_phrase / gerund / finite / unknown
    attachment: str                    # main / shared_modifier / with_absolute 等
    same_subject: Truth
    place_refs: tuple[str, ...] | None  # None=不明、()=無参照を証明済み
    antecedent_ids: tuple[str, ...] | None
    rule_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceComponent:
    domain: Domain
    trace: ProducerTrace | None
    atoms: tuple[ClauseEvidence, ...]
    runtime_available: bool
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class RealizationEvidence:
    schema_version: str                # realization-evidence/v1、内部専用
    input_binding_sha256: str          # 全部品・frame・template・palette等
    components: tuple[EvidenceComponent, ...]


@dataclass(frozen=True)
class FamilyProof:
    family: str
    input_binding_sha256: str
    constructor_id: str | None
    eligible: bool
    facts: tuple[tuple[str, Truth], ...]
    blocker_ids: tuple[str, ...]
    transform_rule_ids: tuple[str, ...]
```

### 5.1 型の必須意味

- `Truth`を`if fact:`で評価しない。必ず`fact is Truth.TRUE`等と比較する。
- `frozen=True`でもdictを保持すれば内部は可変になる。tupleと不変な子要素を使う。
- `part_id`はsource fieldとその場のindex等から作り、Python `hash()`、object ID、時刻を使わない。
- `input_binding_sha256`はJSONのcanonical表現等から計算し、host固有絶対pathを含めない。
- hashは改ざんの暗号学的認証ではない。入力が変わった証拠の再利用を防ぐためのbindingである。
- full source manifestは監査の開始・終了時に取得する。通常promptごとに全repoを走査しない。runtimeのsource identityは読み込み済みcode/catalogの固定identityから得る。immutableなcatalog cacheと、禁止されるmutableなnode間trace cacheを混同しない。
- 不明のplace referenceを空tupleへ変換しない。重複不明は重複なしと異なる。
- `FamilyProof`だけを外部callerから受け取り信頼しない。現在のevidenceとbindingを再確認する。
- auditのJSON化は明示serializerを使う。これらを`PromptContext`等の`asdict()`対象へ組み込まない。

### 5.2 既存型との対応

| 既存 | 対応方針 |
|---|---|
| `RenderedActionPart` | 保持。必要なら`ProducerPart`へのadapterを作る |
| `ActionStructuralEvidence` | 公開互換を壊さず`ProducerTrace`へadapter接続 |
| `LeafGrammarFacts` / `ActionGrammarFacts` | `ClauseEvidence`への変換を先に追加。安全条件の同時変更は避ける |
| `ContentPlan` | 新semantic modelへ置き換えない。具体化された句の入力先として維持 |
| `ActionFrame` | semantic main verb・legacy_slotsを保持。文法上のheadで上書きしない |

---

## 6. 共通API案と責務

以下の新規名は実装時に初めて追加する。既存コードの同等APIが見つかった場合は再利用し、重複実装を作らない。

```text
# 以下は関数契約の擬似記法。実装時はdef・型・error handlingを定義する。
# pipeline/realization_evidence.py
build_realization_evidence(builder_inputs, *, producer_context=None) -> RealizationEvidence
validate_evidence_binding(evidence, builder_inputs) -> bool

# pipeline/family_capabilities.py
prove_family(family, plan, evidence, *, catalog) -> FamilyProof
prove_all_families(plan, evidence, *, catalog) -> tuple[FamilyProof, ...]

# pipeline/prompt_realizer.py または責務分離した小さなconstructor module
construct_family(plan, evidence, proof) -> tuple[ContentPlan, tuple[str, ...]]
```

`construct_family()`の第2戻り値は適用したtransform rule IDs。実装上は小さな結果型にしてもよい。

### 6.1 family判定の単一化

Bridge、selector、realizerがそれぞれ違う安全条件を持つ構造を解消する。

- `prove_family()`が真偽判定の唯一の正本。
- Bridgeはeligible集合から既存seed方式で選ぶだけ。
- Realizerは選ばれたfamilyのbindingを再確認し、そのfamily用constructorを使う。
- `direct_binding_families()`と`candidate_family_safe()`は移行adapterとして残してよいが、新しいfamily規則を追加しない。
- proofを再検証することと、全packを何度も総当たりすることを区別する。binding成立後の純粋な中間結果は1呼び出し内で再利用できる。

### 6.2 familyごとに具体化する

scene-leading用に構成したscene文字列を、scene-insertのラベルに変えただけで流用しない。

`family + input_binding + constructor_id`を一組で保持する。各constructorは、source atomの対応、主語・owner・参照先、必要な接続詞・冠詞・活用変更を記録する。

### 6.3 runtime selectionは当面変更しない

新規候補の選択には既存`mix_seed(seed, "realizer_v2_candidate_family")`と決定論的な候補整列を使う。重み変更、round-robin、seed系列最適化はD3へ延期する。family名のalias変更でentropyを上げることは禁止する。

---

## 7. 変更ファイル計画

### 7.1 既存ファイル

| ファイル | 対象symbol / 変更 | 守ること |
|---|---|---|
| `prompt_renderer.py` | `build_prompt_text()`のcandidate importと内部引数、選択済entryの受渡し、監査sink | 公開node I/Oと既存template選択/RNGを維持 |
| `pipeline/prompt_orchestrator.py` | `build_prompt_from_context()`で既存history/stateからruntime用producer入力を構築 | runner専用traceを使わず、返却contextへevidence追加なし |
| `pipeline/action_renderer.py` | `_render_action_parts()` / `trace_action_slots()`のadapter | renderer本文のbyte parityと既存dedupeを維持 |
| `pipeline/clothing_candidate_renderer.py` | `build_item_description()` / `render_clothing_candidate()`の共通trace付き内部処理 | return tuple、draw順、candidate選択、signatureを維持 |
| `pipeline/clothing_candidate_selector.py` | 必要な場合のみ選択済candidateのtraceを内部保持 | attempt/ranking/early breakを変えない |
| `pipeline/location_builder.py` | `expand_location_prompt()`のsegmentをsource field付きで内部保持 | probability、shuffle、filter、dedupeを変えない |
| `pipeline/v2_structural_evidence.py` | 既存Action proofを共通型へ接続 | version/type/replay照合を維持 |
| `pipeline/v2_direct_provenance.py` | 共通evidence adapter、旧routeの互換保持 | 個別case用のcomplete-string追加禁止 |
| `pipeline/v2_clothing_provenance.py` | 既存historyで選択済packを絞り、replay/constructorへ接続 | 全pack逆探索を主経路にしない。不足はunknown |
| `pipeline/v2_scene_provenance.py` | 選択済部品・所有先を共通traceへ接続 | 無条件でplace/headを安全扱いしない |
| `pipeline/v2_template_provenance.py` | 選択済entryのtopology検証と具体化 | catalog keyだけで安全を保証しない |
| `pipeline/v2_leaf_grammar.py` | facts adapterと既存bounded rulesの再利用 | 新たな巨大語彙表を作らない |
| `pipeline/syntax_family_selector.py` | family判定を共通engineに集約 | baseline markerと実v2 eligibilityを区別 |
| `pipeline/prompt_realizer.py` | family-specific constructionを消費 | `ContentPlan.to_dict()`とplan-only v1を維持 |
| `pipeline/v2_candidate_bridge.py` | 旧受理経路と新経路を整理、診断の取得点 | 既存成功・未対応fallback保持、seed allowlistなし |
| `assets/test_prompt_realizer_v2.py` | v1生metadataとcandidate aliasの契約テストを分離 | 除外を恒久化せず、検証を弱めない |
| `docs/diversity_refactor/{tasks,progress}.md` | R43子タスク・証拠・結果 | A1.6 lock本文は変更しない |
| `docs/diversity_refactor/development_branch.md` | 新検証入口と残課題 | full-suite未実施を隠さない |

`pipeline/clothing_builder.py`や`pipeline/character_profile_pipeline.py`を変更する場合は、trace取得に必要な内部変更だけをR43-00で明示する。公開serialized fieldsは変えない。

### 7.2 新規ファイル

```text
pipeline/realization_evidence.py
pipeline/family_capabilities.py
# producer replayが既存provenance moduleに収まらない場合だけ追加:
pipeline/producer_replay.py

tools/audit_realizer_reachability.py
tools/verify_realizer_v2_candidate.py

assets/test_r43_evidence_contract.py
assets/test_r43_producer_trace.py
assets/test_r43_family_capabilities.py
assets/test_r43_reachability_audit.py
assets/test_r43_runtime_transport.py
assets/test_r43_import_modes.py
assets/test_r43_integration.py
assets/fixtures/r43_real_graph_cases.json

docs/diversity_refactor/r43_implementation_plan.md
docs/diversity_refactor/r43_metric_contract.json
```

テストが大きくなる場合のみproducer別へ分割する。「新しいmodule数を増やすこと」を成果指標にしない。`r43_metric_contract.json`は診断定義とcohortを固定する開発用契約で、A1.6の代替ではない。

### 7.3 原則編集しないファイル

`core/schema.py`、`nodes_context.py`、`nodes_prompt_cleaner.py`、V150保護データ、`tools/effective_diversity_metrics.py`、`tools/effective_diversity_signatures.py`、既存quality comparator、既存semantic-review policyは原則read-only。

`tools/audit_effective_diversity.py`の`ACTIVE_V1_FAMILIES`命名修正は任意の別task。R4.3のために6要素集合・順序・hash対象を変えない。catalogから単純に全宣言familyを読み出して「active」とする変更も禁止する。

---

## 8. Producer別の実装仕様

### 8.1 Action: 現行の強みを維持する

- `trace_action_slots()`と`render_action_slots()`は同じ`_render_action_parts()`を使い続ける。
- `ActionFrame.legacy_text`、現在action、replay textの照合はcase・polarity・ownershipを保持する。空白以外の緩い正規化で一致扱いしない。
- 両activity modeのtraceが同じなら同じ構造として扱える。異なるならunknown。
- emitted partと未描画slotを区別する。もともとproducerが採用しなかったslotをv2で勝手に出力しない。
- `standing and tidying ...`のgrammatical headsとsemantic `main_verb`は別々に検証する。
- body-part subject、external-event subject、protagonistの区別を保つ。
- 否定、目的語、従属句、時間関係、location referenceを省略してcoverageを増やさない。

既存の`build_structural_evidence()`を捨てず、共通型へのadapterから始める。[S08]

### 8.2 Clothing: 選択済みpackを入口にする

現行`build_item_description()`は内部でselected_items、color、material、pattern、style、detailsを持つが、従来APIはtextとsignatureを返す。[S09]

**実装手順:**

1. 同じ処理からtext/signature/traceを構成するprivate helperを作る。
2. 既存`build_item_description()`はその結果の従来2値だけを返す。
3. trace版も同じhelperを使う。通常版とtrace版で乱数draw数・順序を変えない。
4. `render_clothing_candidate()`は選択済attemptのtraceを内部的に取得可能にする。既存戻り値やdecisionのserialized keysは変えない。
5. Builderでは、受信済みhistoryの該当`ContextClothingExpander` decisionから、base_pack/chosen_type/outerwear_pack/variant等の実在fieldを確認する。
6. 全入力が揃う場合だけexact replay。それ以外は選択済packを限定したbound constructor。source ambiguity・ownership ambiguityが残る場合はunknown。

**注意:** `base_variant` / `outerwear_variant`は正規化されたsignatureであり、任意の元文字列を可逆に復元できる形式だと仮定しない。outfit_mode、outerwear_chance、過去のrecent履歴、palette適用時点が不明なら、都合のよい既定値で補って過去実行を再現したことにしない。

複数packが同じtextを持つ場合、最新contextに結び付いた選択済pack情報を優先する。履歴の根拠なく全packから最も通りやすいものを選ばない。同じ出力でも異なるmodifier ownerを与える解釈はunknown。

**文法:** pack membershipだけでNPとしない。既存のreviewed noun/attachment規則を再利用し、singular/plural/mass、article、detailのownerを証明する。新規規則は監査で効果が見込めるconstructorに限定する。

### 8.3 Scene: shuffle前後のsource fieldを失わない

現行`expand_location_prompt()`が作るenvironment/core/props/texture/details/time/weather/crowd/fxを、内部的にはtextとsource field付き部品として保持する。[S10]

- 現在と同じ順序で乱数を消費し、部品tuple/listを同じRNGでshuffleする。
- dedupe判定は現在のtextに対する判定と一致させる。source fieldが異なるという理由で以前抑制した重複を復活させない。
- defaults混入とpack由来を区別する。unknown fieldをknown sourceに付け替えない。
- producer traceにはshuffle後の順序と既存抑制理由を残すが、公開contextへは追加しない。
- Builderで`mode`、`lighting_mode`、action、mood、recent_objects等の当時の入力が不明なら、full replayを主張しない。
- 既存`location_scene.section_changes`等は使える範囲を確認する。ただしmode-dependentで欠損し得るため必須存在と決めつけない。
- 現在のlocationとframe内の古いlocationが違う場合、都合のよい方を採用せず、binding mismatchとして扱う。

元のfield構造が証明できても、`gallery arranged for ...`のownerや`each work`の参照先は別に検証する。weather/crowdを黙って削除してsceneを通さない。

### 8.4 Template: 選択済みentryをその場で利用する

`prompt_renderer.build_prompt_text()`が持つ`intro_entry` / `body_entry` / `end_entry`を、そのBuilder呼び出しのevidence builderへ渡す。[S05]

- text、key、roles、placeholder topologyをbinding対象に含める。
- exact catalog entryの選択は「出所」の証拠であって文法保証ではない。
- `template_entries_fn`で注入されたentryや自由入力templateも存在する。未認識topologyはfallback。
- 既存の固定suffix削除やfiller pruningをtrace上で認識する。v2適用のためにtemplate抽選や既存filler policyを変更しない。
- 直接tripleだけでなく、どのtopologyが何件を遮断しているかを監査する。効果の小さなwrapperを順に追加する方法を避ける。
- `room`を含む既存wrapperは、単語を消さずに所有先を保ったまま必要な活用変更を行う。

### 8.5 Subject / Garnish / Moodも必須の計測対象

Action・Clothing・Sceneだけを一般化しても、`_subject()`の限定されたhair/eye表や`_GARNISH` / `_MOODS`の入口で止まる可能性がある。[S04]

まず既存規則を共通evidenceへadapter化し、認識率・単独blocker数を測る。source profile、現在のsubject text、既存garnish選択情報を照合する。

既存source辞書を丸ごと`safe=True`として取り込まない。文法上のunknownが残る場合はそのcomponentをUNKNOWNのまま返す。追加規則は監査で選ぶ。最初から全領域を完全に構造化する巨大migrationを始めない。

---

## 9. 6 familyの証明契約

正本catalogのrequired slots / requires / forbidsは引き続き適用する。既存selectorとrealizerにある追加条件も、削除ではなく共通engineへ移す。[S11][S14][S15]

以下はそれを置き換える緩い一覧ではなく、constructorで具体化すべき追加の証明責務である。

| Family | 具体的に証明すること | 主な拒否例 |
|---|---|---|
| `subject_action_scene` | subjectとfinite predicateを連結でき、sceneを後置してもowner・意味を変えない | baseline markerだけ、unknown subject、未証明のscene重複 |
| `subject_action__scene_tail` | subject/actionを完結でき、sceneを独立文にできる | scene fragmentを冠詞等なしに文扱い、外部主語の混入 |
| `scene_lead_subject_action` | sceneを前置しても全modifierのownerが保持される | dangling scene modifier、temporal scope不明 |
| `action_lead_subject_scene` | actionは許可されたgerund形、修飾先が同じ主人公であり、scene述語へ安全に接続できる | eyes/hands主体、external event、独立主語、finite action |
| `subject_scene_action` | subjectとpredicateの間へsceneを挿入しても依存関係を切らない | pronoun参照先変化、主語の重複、unknown attachment |
| `subject_action_scene_insert` | actionにscene adjunctを付けても重複・scope変更がない | overlap TRUE/UNKNOWN、action内の場所と重複 |

### 9.1 安全判定の粒度

- 各familyのrequirementsを証明できるか、familyごとに独立して判定する。
- 「どれかのfamilyに不明点がある」だけで、無関係なfamilyまで拒否しない。
- ただし必要なfactがUNKNOWNなら許可しない。
- 既存のstandalone-scene例外以外でoverlap条件を緩めることは、R4.3の自動許可範囲に含めない。
- `subject_action_scene`をunconditionalな実v2許可としない。fallback markerとしてのbaselineとは別。
- fallbackの2形をcanonical v2 family名へ写す既存mappingを変えない。実行versionを必ず併記する。

### 9.2 missing familyを「許可」だけで増やさない

familyごとに、現在の実workflowから得た未変更入力を利用するpositive fixtureと、主語・owner・polarity等を変えたnegative fixtureを必要とする。

人工的に単純化したcontext、異なる衣装/場所への差し替え、強制的なupstream再抽選で作った例を「real-graph positive」と呼ばない。再結合fixtureは有用だが、別カテゴリとして記録する。

---

## 10. Reachability Audit仕様

新規CLI: `tools/audit_realizer_reachability.py`
新規schema: `realizer-reachability/v1`

目的は正式なEffective Diversity Auditの置換ではなく、**どの入力・どの構文が、何によって止まっているか**の決定論的な診断である。

### 10.1 workflow runnerを再利用する

- 実行は既存`build_canonical_record()` / `build_canonical_records()`を使用する。
- 新しい似たworkflow engineは作らない。
- Builder replayにはrecordのexecution traceにある正確なBuilder入力を使う。
- `run_seed`と、randomize済みのBuilder seedは別物。後者をrun_seedで代用しない。
- replayしたraw promptとrecordのraw_promptが不一致なら、そのrowを成功扱いせずerrorを記録する。
- runtimeのevidence取得には内部のoptional診断sinkを利用してよいが、sinkの有無で本文・既存debug・RNG・contextが変化しないことをテストする。
- 通常Builderにないrunner-only入力をproof engineへ足さない。監査専用replayは別モード・別カウンターにする。

### 10.2 計測する6段階

各seed×familyについて以下を区別する。

1. `declared`: catalogに存在。
2. `constructor_present`: そのfamilyのconstructorが実装されている。
3. `runtime_eligible`: runtimeで利用可能な証拠だけで全required条件を満たす。
4. `forced_render_v2`: **診断内だけ**でそのfamilyを要求し、実v2描画・意味保持を確認。
5. `selected`: 通常のseed選択で選ばれた。
6. `executed_v2`: 通常workflowで`realizer_version=v2`として実行された。

別途、通常出力の`syntax_family`をfallback込みで数える。`observed_structure_count`と`executed_v2_family_count`を混同しない。

forced evaluationは公開nodeへのinput追加、既存seed抽選の変更、上流semantic値の変更を伴わない。通常実行とのfact parityが必須で、formalな通常選択のfamily countsへ合算しない。

### 10.3 proofとconstructorの不一致をエラーにする

`runtime_eligible=True`なのにconstructorが失敗したりv1へ戻ったりしたら、単にfallback数へ埋めず`proof_constructor_mismatch`として扱う。

現在の入力に対して構文を作れることと、後段normalizer/PromptCleanerを通過して意味を保持できることの両方を確認する。前段の単語保持だけでfinal promptの品質を証明したことにしない。

### 10.4 Blocker taxonomy

安定したIDを用い、自然文の説明とは分ける。例:

```text
binding.frame_current_text_mismatch
binding.replay_mismatch
binding.source_ambiguity
binding.history_stale
transport.runtime_inputs_missing
transport.audit_only_evidence
subject.unsupported_constructor
clothing.owner_unknown
clothing.number_unknown
scene.source_field_unknown
scene.attachment_unknown
scene.place_overlap_unknown
action.leaf_grammar_unknown
action.independent_subject
action.same_subject_unknown
action.polarity_unproved
template.topology_unsupported
family.constructor_missing
family.legacy_route_ceiling
policy.conflict
render.proof_constructor_mismatch
```

policyによるhard rejection、UNKNOWN、安全なfeatureが未実装、契約上到達不能を分ける。`None`を返すだけのhelperには、監査用の詳細結果を追加して原因を保持する。公開の既存戻り値はwrapperで維持してよい。

### 10.5 集計

最低限、次をcanonical JSONと短いMarkdown summaryへ出す。

- domain別: binding成功、grammar既知、runtime利用可能、audit-only、unknown件数。
- family別: eligible / forced成功 / 通常selected / 通常executed-v2件数。
- seed別: eligible family数の分布、実v2適用、v1 fallback、error。
- route別: simple legacy-compatible / legacy-direct / common-evidence / fallback。
- blocker別: 重複を許す出現件数、**そのblockerだけ**で止まる件数。
- blockerの組合せ: 完全なblocker集合ごとの件数、上位のpair/triple。
- 複数のblockerが同時に存在する入力を、単独修正で救済できる件数へ重複加算しない。
- 新規救済seed、旧成功保持seed、後退seedを比較する。
- 具体例は各blockerの決定論的な代表少数件を載せる。runtime allowlistには使用しない。

### 10.6 改修効果の見積もり

`only_blocked_by_X`は、Xが安全に解決できた場合の**候補上限**であり、必ず改善できる件数ではない。残る未検査条件や語彙scopeがあるときは、その旨を記録する。

単独blockerが少ないときは、交差するpair/tripleを優先して調べる。個別seedを毎回2件ずつ救う開発に戻らない。

任意の補助指標として、固定cohortで証明済み到達構造のunionから`log2(K_reachable)/log2(6)`を出してよい。これは現在の実装・証明範囲での上限診断であり、将来実装後の可能性や実際のentropyではない。`K_reachable`には通常fallbackの実構造も明示して含め、declared-onlyのfamilyを混ぜない。

### 10.7 JSON envelope

```json
{
  "schema_version": "realizer-reachability/v1",
  "status": "ok",
  "candidate_id": "r43-current",
  "identity": {
    "git_commit": "...",
    "source_tree_hash": "...",
    "audit_implementation_hash": "...",
    "workflow_hash": "...",
    "effective_workflow_hash": "...",
    "runner_config_hash": "...",
    "family_catalog_hash": "...",
    "r43_contract_hash": "...",
    "a16_lock_id": "A1.6-2026-09-06/v1"
  },
  "cohort": {
    "seed_start": 0,
    "sample_count": 512,
    "history_mode": "existing-workflow",
    "classification": "development-not-holdout"
  },
  "records_sha256": "...",
  "rows_sha256": "...",
  "domains": {},
  "families": {},
  "blockers": {},
  "blocker_combinations": [],
  "actual": {
    "v2_applied_count": 0,
    "v2_family_counts": {},
    "v1_fallback_structure_counts": {},
    "errors": []
  },
  "comparison": null,
  "adoption_verdict": "NOT_EVALUATED"
}
```

上記0はschema例であり、baseline値ではない。未測定は`null`または`NOT_RUN`を使い、0件成功と表現しない。

per-seed詳細は`rows.jsonl`へ分離する。各rowにinput binding、各component、family別proof/blockers、forced result、通常実行結果、semantic parityを保存する。

### 10.8 CLI案

以下は **R43-02で実装する新CLI**。現在存在するコマンドではない。

```bash
python tools/audit_realizer_reachability.py \
  --profile smoke --seed-start 0 --sample-count 16 \
  --output-dir assets/results/diversity_refactor/r43/smoke

python tools/audit_realizer_reachability.py \
  --profile intake --seed-start 0 --sample-count 512 \
  --force-families all \
  --output-dir assets/results/diversity_refactor/r43/intake512
```

`--profile smoke`の既定16、`intake`の既定512。既存Effective Diversityのsmoke=128とは別の軽量診断profileである。名前だけで同じ計測と解釈しない。

オプション`--baseline-root <read-only-worktree>`を実装する場合、比較対象は別processで実行し、sourceごとのmodules/dataを混ぜない。baselineに新診断APIがない場合は、取得できる通常出力と既存metadataだけを比較し、未取得のreachabilityは`NOT_AVAILABLE`にする。

### 10.9 baselineと計測器の固定

- candidate07基準sourceを変更前に別worktreeで保存する。
- R43-02で診断取得点を入れたsourceは別の`R43-AUDIT-BASE`として保存し、candidate07とのraw/cleaned/既存debugの同一性を記録する。
- 新しい計測器で測った結果を「変更前sourceから直接得た」と偽装しない。
- baselineとcandidateを同一interpreterへ交互にimportしない。`sys.modules`とdata cacheによる混線を防ぐ。
- `build_source_manifest()`を再利用しつつ、新規runtime module・source metadata・監査コードがhash対象から漏れていないか確認する。
- 実行中にsourceが変わったらreceiptをINVALIDにする。Git SHAだけではuncommitted sourceを識別できない。
- 時刻・計測時間・OS絶対path等の可変値はcanonical metricsから分離する。

---

## 11. 正式Auditとの境界とalias契約

### 11.1 既存の除外テストを整理する

対象: `TestRealizerBuilderDebug.test_actual_v1_family_metadata_and_seed_replay`。[S12]

このテストは旧v1 family名と空のfallback reasonを期待する。一方candidate bridgeは、v1へ戻る場合もcanonical構造名にmappingし、`fallback_origin_syntax_family`等を保持する。[S13]

既定方針:

1. plan-only v1は、生の旧family名と従来本文を検証する。
2. candidate branchのBuilder fallbackは、既存canonical mapping・`realizer_version=v1`・`candidate_v2_applied=False`・origin・replayを検証する。
3. 同じテストを単に緩めるのではなく、2つの契約を別テストで厳密に残す。
4. 既存mapping、normalization、entropyの集計定義は変更しない。
5. 合格後は既知除外をなくす。別の失敗があれば分類し、full-suite PASSを偽らない。

### 11.2 制限された公開範囲を正しく保持する

監査sinkやtyped evidenceは公開nodeのINPUT_TYPESに追加しない。`build_prompt_from_context()`等の内部APIにkeyword-onlyで追加する場合も、既存callの出力を保持する。

candidate bridgeから返す大量の診断を既存Builder decisionへ追加しない。`candidate_eligibility`の既存キーを変更する必要がある場合は、基盤byte-parity段階ではlegacy projectionを保持し、新しい詳細は別receiptに出す。

### 11.3 v2を実行したfamilyと構造名は別

次の2つは必ず別に記録する。

```text
通常promptの構造名counts（既存locked mapping、v1 fallbackを含む）
realizer_version=v2かつ実行されたfamily counts
```

R4.3では後者の6構文実行経路を証明する。前者だけ6になったことをもって、v2の6構文実装・到達を証明したとしない。

---

## 12. 実装順とタスク別Acceptance

各タスクは独立した差分としてレビュー可能にする。タスク開始前にIN_PROGRESS、終了時に変更ファイル・command・exit code・結果・source identity・次タスクを記録する。

### R43-00 — Intakeとbaseline保存

**変更:** 文書と外部証拠のみ。

- 現在のbranch/HEAD/dirty stateを確認。
- 設計基準HEAD以後の変更がある場合は差分を読み、既に実装済みの箇所を計画へ反映する。古い内容で上書きしない。
- candidate07とstable mainの読み取り専用比較sourceを確保。
- A1.6 lock、保護データ、public signatures、source manifest、既存test集合を記録。
- full workflow replayに必要な入力が、各domainのhistoryにどこまで存在するか表にする。

**Acceptance:**

- [ ] 基準sourceとユーザーの既存変更が保全されている。
- [ ] historical測定と新規測定が区別されている。
- [ ] runtimeで利用可能なfield / audit-only field / missing fieldの表がある。
- [ ] original V150の正式baseline証拠の有無を確認した。欠損を推定で補っていない。
- [ ] baseline不足でも可能な基盤作業と、正式比較がBLOCKEDになる範囲を明示した。

### R43-01 — Importとmetadata契約の整備

**変更:** `prompt_renderer.py`、既存metadata test、新import/transport tests、検証入口の最小版。

- function内の`from pipeline.v2_candidate_bridge ...`を既存のpackage/non-package設計へ揃える。
- root/package両方のimport、独立した2checkoutのmodule identityを確認する。
- §11のalias契約をテストとして分離し、既知のテスト除外を解消する。
- scoped test collectionを機械可読に保存する。

**Acceptance:**

- [ ] 対象の既知除外が解消され、単なるassert削除ではない。
- [ ] package-modeでrepo rootがsys.path直下にない場合もBuilder実行が通る。
- [ ] root-modeとpackage-modeが同じ入力で同じ結果を返す。
- [ ] 既存focused/regression/validator/full-flowの結果を記録した。
- [ ] 本文、公開I/O、family mappingを変えていない。

### R43-02 — Reachability Auditを先に作る

**変更:** 新audit、診断contract、必要最小限の内部sink、監査test。

- §10の宣言/実装/eligible/forced/selected/executedを分離。
- 新しい安全許可や新grammarはまだ入れない。
- candidate07基準とinstrumented baselineのparityを確認してintake512を保存。
- 9/512・4構造という過去記録と異なる場合は、source/cohort/設定の差を診断する。

**Acceptance:**

- [ ] 512行×6 familyの結果または明示的なNOT_AVAILABLEがある。
- [ ] 共通fallback理由だけでなくcomponent blockerを取得できる。
- [ ] sink有無のprompt・既存debug・context・RNG parityが成立。
- [ ] 同一sourceで再実行したcanonical report/rows hashが一致。
- [ ] only-blocker、pair/triple、route別集計がある。
- [ ] 比較条件が同一と証明できない結果をbaseline regressionと断定しない。

### R43-03 — 共通evidence型とbinding

**変更:** `realization_evidence.py`、Action/legacy facts adapter、contract tests。

- §5の型を実装。unknown、owner、grammatical subjectを保持する。
- hashing/canonical serializationと入力改変時のinvalid化を実装。
- 今は旧family選択と本文を変えない。

**Acceptance:**

- [ ] forged/stale/version-mismatched evidenceが許可を与えない。
- [ ] optional field欠損がTRUEや空集合に化けない。
- [ ] `ContentPlan` / `ActionFrame` / contextのserialized契約は不変。
- [ ] 旧512 prompt・既存debugに差がない。

### R43-04 — Clothingの共通traceと再構築

**変更:** clothing renderer、必要ならselector、clothing provenance、producer replay tests。

- 共通private helperから従来出力とtraceを生成。
- 履歴で選択済packを絞るadapterを追加。
- exact replayが不可能な場合のbound constructor / unknownを実装。

**Acceptance:**

- [ ] render-onlyとtrace版のtext/signature/decision/RNG post-stateが一致。
- [ ] 複数候補attempt、palette override、material抑制、detail/state、outerwearをテスト。
- [ ] stale/missing historyで別packや別設定を勝手に選ばない。
- [ ] constructor proofの不足を、source membershipだけで埋めない。
- [ ] このタスクで新しいfamily選択を有効化していない。

### R43-05 — Sceneの共通traceと再構築

**変更:** location builder、scene provenance、replay tests。

- 各segmentのsource fieldと順序を共通内部表現へ移す。
- defaults/pack由来、shuffle、dedupeを保持。
- runtime入力不足を明示し、監査専用replayを区別。

**Acceptance:**

- [ ] simple/detailed、auto/off、各source field、defaults、shuffle/dedupeが非回帰。
- [ ] trace取得でrandom drawが変わらない。
- [ ] gallery/works/each-workのowner/referenceが保持される。
- [ ] weather/crowd等の未対応部分を削除せずunknownにする。
- [ ] Builderの別process replayで追加side channelなしに同じ判定が出る。

### R43-06 — Template / Subject / Garnish / Moodのadapter

**変更:** prompt renderer、template/direct provenance、evidence builder、必要なtests。

- selected template entryを同一呼び出し内で渡す。
- 既存subject/garnish/moodを共通型へ写す。
- 監査で判明した大きいblockerに対する最小constructorを事前計画する。

**Acceptance:**

- [ ] topology未認識のentryはfallbackであり、catalog keyだけでは通らない。
- [ ] subject/garnish/moodもfamily proofの必須componentとして診断される。
- [ ] 新たなcomplete action string / seed allowlistがない。
- [ ] 語彙やsemantic selectionを変えず、constructor追加のscopeを記録した。

### R43-07 — Family capability engine

**変更:** `family_capabilities.py`、selector/realizer adapter、family tests。

- 全6 familyのproofとconstructorを実装。
- legacy direct経路の固定3集合を、新共通経路の許可判定には使用しない。
- Bridge/selector/realizerに分散した新規判定を1か所へ集約。
- 旧adapterは現在の挙動を保存するためだけに残す。

**Acceptance:**

- [ ] 6 familyそれぞれにpositive/negative fixtureがある。
- [ ] familyごとのconstructorがinput bindingと結び付く。
- [ ] proof PASSと実描画結果に食い違いがない。
- [ ] action-leadingをbody/external subjectが許可しない。
- [ ] 重複不明をscene-insertの許可に使わない。
- [ ] 人工fixtureの6成功と、実workflowでの6到達を別に扱う。

### R43-08 — 統合と6-family real-graph証拠

**変更:** bridge/orchestratorの限定統合、real-graph fixtures、integration tests。

- 互換経路を維持しつつ、新経路を従来fallbackへ接続。
- upstream choicesと通常seed選択方式は変更しない。
- 固定512の実入力に対してfamily別forced diagnosticsを作る。
- 監査のsingle/pair blockerに基づいて、最も再利用可能な証明を優先する。

**Acceptance:**

- [ ] 固定512の変更前後でupstream contextとcore/frame projectionが一致。
- [ ] 既存9成功例を保持し、新たな通常v2適用例がある。
- [ ] 残るv1 fallbackのraw/cleaned本文が一致。
- [ ] 6 familyすべてが少なくとも1つの未変更real-graph入力で安全にforced実行できる。
- [ ] 未到達familyは原因を明示してBLOCKEDにし、人工例で補完しない。
- [ ] 禁止語・identity・ownership・semantic loss/inventionの新規defectがない。

### R43-09 — 開発検証の統合と判定

**変更:** `verify_realizer_v2_candidate.py`、検証manifest、進捗記録。

- focused → regression → validators → full-flow → paired512 → repeatabilityの順で実行。
- 新旧のsource rootを別processで比較。
- test集合、環境、exit code、skip/deselect/xfail、hashをreceiptへ保存。
- `architecture_status`と`development_status`を別に判定する。

**Acceptance:**

- [ ] §13の開発条件を満たすか、未達を正確に記録した。
- [ ] 9/512→何件という数値だけでなくfamily別実行・blocker差分がある。
- [ ] すべての新規CLIをfresh checkoutで実行可能。
- [ ] 旧ZIPの絶対pathや開発者PCの環境に依存しない。
- [ ] 未実施のfull suite / frontend / formal gateをPASS扱いしていない。

### R43-10 — 正式評価へのhandoff（条件付き）

R43-09までの不足を補うために閾値を緩めない。十分な証拠が揃った候補だけsource/configをfreezeし、既存の正式比較手順へ渡す。

**Acceptance:**

- [ ] original V150 baselineと新candidateのsource identity・比較可能性を確認。
- [ ] A1.6の全項目を使い、部分表だけで判定しない。
- [ ] formal未実施なら`NOT_RUN`、adoptionはBLOCKED。
- [ ] formal閾値を測定して不合格ならREJECTED。
- [ ] R4.3タスク内でmainへmergeせず、N2.8を自動開始しない。

---

## 13. 開発Acceptanceと正式Acceptance

### 13.1 R4.3 architecture acceptance

以下をすべて満たした場合のみ`architecture_status=PASS`。

- [ ] 全domainに共通evidenceの入力経路がある。非対応もUNKNOWNとして表せる。
- [ ] runtime情報とaudit-only情報を混同していない。
- [ ] Action/Clothing/Sceneのtrace取得と通常renderが共通実装を使う。
- [ ] 新規familyの判定の正本が一つであり、consumerごとの別許可リストに依存しない。
- [ ] raw source binding、semantic head、grammatical subject、owner、place/ref unknownが保存される。
- [ ] 公開I/O、serialized contract、V150、RNG、rollbackの非回帰が確認できる。
- [ ] 監査sinkなしの通常実行でも成立し、別processから同じcontextで再現できる。

全domainの自由文をすべて認識することは、この条件に含めない。

### 13.2 R4.3 development acceptance

- [ ] 同じdevelopment512で通常実v2適用が基準9件より増える。
- [ ] 既存成功例と未対応fallbackの保持、全paired semantic/upstream preservationが成立。
- [ ] **6 familyすべてについて未変更real-graph入力のruntime proofとforced描画成功がある。**
- [ ] proof-constructor mismatch、policy/solo/identity/semantic新規defectが0。
- [ ] 追加された構文の最終cleaned promptについて、source atomの保持と自然性をレビューする。
- [ ] 通常選択の実行family数を併記し、6未満ならその不足を残課題として記録する。

### 13.3 開発上の目安と止め方

`actual_v2 >= 64/512`かつ通常実行で少なくとも5 familyを観測することを、従来提案に沿った**開発上の目安**として使う。これは正式閾値ではなく、達成を保証する計画でもない。

この目安に届かない場合、重いformal評価を自動実行しない。blocker単独/交差集計から次の限定タスクを選ぶ。

共通化してもreal-graphの6到達が成立しなければ、「metadataを渡すだけで解決した」と結論しない。新たに必要な文法情報の具体的なsource field、参照関係、語彙category、輸送不足を明記する。必要情報がpublic contract変更なしでは得られない場合は、その範囲をBLOCKEDにし、別の設計判断として扱う。

### 13.4 A1.6正式条件の抜粋

正本は`docs/diversity_refactor/progress.md`の **A1.6-2026-09-06/v1**。以下は抜粋であり、全条件の代替ではない。[S03]

| 項目 | @128 | @512 | @2048 |
|---|---:|---:|---:|
| normalized syntax entropyの下限 | 0.743271 | 0.814359 | 0.855077 |
| maximum same-syntax runの上限 | 11 | 11 | 16 |
| valid core/frame数 | 128 | 512 | 2048 |
| core unique数の下限 | 128 | 508 | 1963 |
| frame unique数の下限 | 128 | 511 | 2042 |
| exact prompt duplicate数の上限 | 0 | 0 | 0 |
| normalized prompt duplicate数の上限 | 0 | 0 | 0 |
| syntax metadata missing数の上限 | 0 | 0 | 0 |

@2048ではrequired 6 familyが有効かつ観測され、raw entropyは`>0.814359 bits`、dominant family shareは`<=0.748047`であることも必要。

加えて、missingness ceilings、各semantic axisのcoverage、per-seed semantic preservation、既存V150の厳格なautomatic quality guards、fixed64+16、適用される独立review・fresh confirmation・release audit・frontend/browser等を正本通りに満たす必要がある。

重要な境界:

- 新candidateのreference8192は、そのcandidate自身のsource/configで作る。
- V150のreference cacheを新candidateへ流用してidentity checkを回避しない。
- 基準code snapshotとpaired recordsがなければ、aggregate countsだけで意味保持を主張しない。
- `ACTIVE_V1_FAMILIES`という変数名の変更と、正式なactive family universeの変更を区別する。[S18]
- Hの分母Kを小さくしたり、missingを除外したり、aliasを増やしたりして合格にしない。
- 正式最終採用の@8192評価にはsource-bound baselineが必要。reference用8192を勝手にrelease測定値と解釈しない。

---

## 14. テスト仕様

### 14.1 必須テストmatrix

| 領域 | Positive | Negative / adversarial | 必須確認 |
|---|---|---|---|
| Action trace | activity_first両mode、primary/support/time採用 | stale text、slot型不正、version不正、複合source | 既存renderと同じbytes・同じ採否 |
| Action grammar | gerund、既知finite、compound、許可subordinate | 独立主語、未解析tail、否定head、object喪失 | semantic headとgrammatical headを別保持 |
| Body ownership | 証明済み`with eyes ...` | eyesを主人公本人扱い、reflexive誤用 | action-leadingを誤許可しない |
| Clothing trace | palette各field、1/複数衣装、details、outerwear | stale pack、重複source候補、owner不明 | same RNG post-state、signature不変 |
| Scene trace | env/core/props/texture/time/defaults/shuffle | 未知field、同名異owner、dangling modifier | source order・dedupe不変 |
| References | `each work`と先行works、scene-owned修飾 | 先行詞欠損、別物へのattach | 参照を発明しない |
| Template | direct、既存owned-finite、承認された新topology | 同じkeyだがtext変更、unknown placeholder | key単独をproofにしない |
| Subject | 現行profile由来の同一人物 | 二人目、独立節、stale profile | 主体数・外観情報の保持 |
| Evidence binding | 同じ入力への再利用 | 1語・palette・entry・source変更後の再利用 | 証拠が確実にinvalidになる |
| Family capability | 6 family個別constructor | proof偽装、family labelだけ変更 | 正しいconstructorへのbinding |
| Audit | 16/512、同一source再実行、別root比較 | duplicate seed、empty、missing proof、途中source変更 | deterministic canonical receipt |
| Transport | context_jsonからfresh processでBuilder再実行 | upstream process cache依存、audit-only入力注入 | 実ComfyUI相当の入力だけで成立 |
| Imports | root import、package import | 2checkout混在、root直下sys.pathがない | クラス同一性・data source整合 |
| Rollback | composition false、unsupported input | malformed but non-crashing legacy input | 旧出力とfail-closed維持 |
| Serialization | 既存public tuple/JSONのround-trip | evidence追加による肥大化 | 既存contract不変 |

### 14.2 source factの保持をテストする方法

coarseなcore/frame signature一致だけでは十分ではない。最終出力に対して次を追加確認する。

- sourceで実際にemittedされたatomが、v2のどのspan/句に対応するか。
- source atomの脱落・不必要な複製がないこと。
- 新たなcontent noun、action、subject、locationを追加していないこと。
- 冠詞・接続語・許可された活用はrule ID付きのtransformとして列挙すること。
- 語のCounter一致は補助oracle。owner・polarity・時間関係・参照の正しさの代わりにしない。
- 既存normalizer / PromptCleaner後の本文でも保持を確認すること。
- baselineの既存policyによる抑制と、v2が新たに落とした事実を区別すること。

### 14.3 recombinationとreal-graphの分離

`r43_real_graph_cases.json`には、run_seed、実Builder seed、正確なBuilder入力、source/cohort hash、expected proof、期待される出力断片を記録する。

人工的なrecombinationは別fixture区分にする。既知constructorの名詞や衣装の組合せを変えたケースは一般化のテストに使えるが、real-graph件数へ加えない。

最低限、scene ownership、compound predicate、body-part clause、clothing modifier、template wrapperについて、実装に用いたpositive例以外の組合せとnegative例を用意する。無制限なrandom property testでflakyなCIを作らず、固定seedまたは小さな直積で再現可能にする。

### 14.4 決定論性

- 同一processで同入力を2回実行。
- fresh processで同入力を実行。
- `PYTHONHASHSEED`を複数値に変えて実行。
- seedを昇順、逆順、固定した別順で実行し、seedごとの結果が同じ。
- root-modeとpackage-modeの出力を比較。
- audit sinkあり/なし、forced診断あり/なしで通常出力が同じ。
- RNGを再生する場合はlocal RNGを使い、本体のRNG stateを消費・巻き戻ししない。

### 14.5 大きなテスト件数を品質保証と混同しない

`tests`と`subtests`を別々に記録する。assertを複製して件数だけ増やさない。収集したtest ID一覧のhashをreceiptへ入れ、比較前後の集合差を説明する。

既知失敗を分類することは許されるが、除外した状態を「全テストPASS」と呼ばない。R43範囲内の既知alias失敗は解消対象。範囲外の既存失敗は別記し、正式採用に必要な条件に影響する場合はadoptionを止める。

---

## 15. 検証CLIと実行例

### 15.1 既存コマンドで行うpreflight

以下は既存のGit/Pythonコマンド。作業dirが対象repoであることを先に確認する。

```bash
git status --short --branch
git branch --show-current
git rev-parse HEAD
git diff --stat 9a2aa32c1e3a48d1d7ea51eb91aee42843dba021

python assets/calc_variations.py --json
python tools/validate_prompt_data.py
python tools/check_variation_scope.py
python tools/build_action_pools.py --check
python tools/build_compatibility_review.py --check
python tools/verify_full_flow.py
```

変更前sourceを別worktreeに保存する例:

```bash
git worktree add --detach ../scg-r43-baseline 9a2aa32c1e3a48d1d7ea51eb91aee42843dba021
```

すでにdirectoryがある場合は削除しない。内容を確認するか別名を使う。実作業HEADが設計基準より新しい場合は、R43-00で固定した実際の開始commitを使用し、設計基準との差分を別途記録する。

### 15.2 新規verifierの契約

新規`tools/verify_realizer_v2_candidate.py`は、既存テスト・validator・runnerを呼ぶ **薄い実行ラッパー** とする。新しい品質判定器やworkflow runnerを実装しない。

想定stage:

| stage | 実施範囲 |
|---|---|
| `focused` | R43、既存N27、selector、realizer、alias/import/transportの対象test |
| `regression` | 既存context/schema/renderer/snapshot/vocab系、data validation、full flow |
| `intake` | focused/regression＋paired512＋reachability＋determinism |
| `adoption-preflight` | 必須baseline/source/lock/receiptの存在と互換性確認。正式計測の代わりではない |

実装後の使用例:

```bash
python tools/verify_realizer_v2_candidate.py \
  --stage focused \
  --output-dir assets/results/diversity_refactor/r43/focused

python tools/verify_realizer_v2_candidate.py \
  --stage intake \
  --baseline-root ../scg-r43-baseline \
  --output-dir assets/results/diversity_refactor/r43/verification
```

CLIはWindows/PowerShellとLinuxの双方を考慮し、Python側でsorted globと`subprocess.run([...], shell=False)`を使う。上記の改行用`\`をPowerShellへそのまま貼らず、1行で実行してもよい。

**verifierの要件:**

- stage選択、実行command、exit code、所要時間、ログpathを記録。
- canonicalな判定payloadと、環境/時刻/所要時間の非決定的ログを分ける。
- failを0で返さない。成功=0、検証failure=1、証拠欠損/入力error=2等を仕様化する。
- source差分を検証中に検出したら結果をINVALIDにする。
- 既存artifactを黙って上書きしない。新run dirまたは明示的な再実行先を使う。
- run中にdependencyを自動installしない。環境不足は明示し、既存開発環境の準備手順へ戻す。
- CI追加は任意の別task。追加するなら軽量testから始め、毎pushで8192 formal gateを走らせない。

### 15.3 正式Effective Diversity Audit

以下の既存コマンドは、正式評価を開始できる条件が整ってから実行する。

```bash
python tools/audit_effective_diversity.py \
  --profile gate \
  --output assets/results/diversity_refactor/r43/formal/effective_gate.json
```

このコマンドだけでA1.6全条件、fixed80、blind review、release、frontend/browserを満たしたことにはならない。

旧`verify_candidate.py`はstable rootとisolated candidates配置を前提にするため、開発branchへそのまま流用しない。[S01] 元V150 baselineの正式証拠がない場合は、その点をadoption-preflightでBLOCKEDにする。

---

## 16. 推奨artifact構造と保存方針

通常のsource・小さなfixture・仕様はGit管理する。大きな生成物は既存方針通りignored `assets/results/`へ保存し、hashとsummaryをtracked文書へ残す。

```text
assets/results/diversity_refactor/r43/<run-id>/
  source-manifest.json
  environment.json
  commands.json
  test-collection.json
  baseline-identity.json
  records.jsonl
  rows.jsonl
  reachability.json
  reachability-summary.md
  preservation.json
  source-atom-review.json
  verification.json
  verdict.json
  logs/
```

`run-id`に時刻を使うこと自体はよいが、canonical reportの内容や測定hashにその可変pathを混ぜない。

tracked summaryには少なくとも次を記録する。

```json
{
  "task": "N2.7-R4.3",
  "source_commit": "...",
  "source_tree_hash": "...",
  "architecture_status": "NOT_RUN",
  "development_status": "NOT_RUN",
  "adoption_status": "BLOCKED",
  "ordinary_v2_count_512": null,
  "ordinary_v2_family_count": null,
  "forced_real_graph_family_count": null,
  "fallback_structure_count": null,
  "proof_constructor_mismatch_count": null,
  "semantic_mismatch_count": null,
  "upstream_context_mismatch_count": null,
  "known_test_exclusions": [],
  "formal": {
    "reference8192": "NOT_RUN",
    "gate2048": "NOT_RUN",
    "fixed80": "NOT_RUN",
    "release8192": "NOT_RUN"
  },
  "evidence": []
}
```

`ordinary_v2_count_512`のように分母を明示する。512で得た数値を2048の結果へ外挿して正式結果の欄へ書かない。

---

## 17. progress.mdテンプレート

### 開始

```markdown
### N2.7-R4.3 / R43-00 — Intake

State: IN_PROGRESS
Branch: refactor/realizer-v2
Design baseline: 9a2aa32c1e3a48d1d7ea51eb91aee42843dba021
Actual start HEAD: <measured>
Stable main source: <measured>
Existing user changes: <recorded, not overwritten>

Goal:
Common runtime evidence and family-specific proof, without changing V150,
public context contracts, semantic selection or A1.6.

Historical development reference:
candidate07: 9/512 actual v2 applications; four structures including fallback.
These are historical recorded results, not measurements of this new source.

Transport boundary:
Only existing Builder inputs/context/history may authorize runtime rendering.
Audit-only replay evidence is reported separately.

Next task: R43-01 after R43-00 acceptance.
Adoption: BLOCKED. No main merge or N2.8 activation.
```

### 各タスク終了

```markdown
### R43-XX — <task title>

State: PASS | BLOCKED | REJECTED
Source HEAD / source-tree hash:
Changed files:
Commands / exit codes:
Collected tests / subtests / skips / exclusions:
Artifact paths and SHA-256:

Preservation:
- upstream context:
- raw/cleaned fallback:
- previous successful cases:
- semantic core/frame:
- source atom / ownership / polarity:
- public signatures and V150:
- determinism and import modes:

Reachability:
- runtime eligible per family:
- forced real-graph v2 per family:
- ordinary executed v2 per family:
- fallback structures:
- leading single/pair blockers:

Unresolved issues:
Next task:
Adoption: BLOCKED unless all applicable formal evidence is complete.
```

---

## 18. Scope creepを止める判断基準

次のいずれかが起きたら、その場で大きな追加実装をせず原因を記録する。

**A. traceは100%取得できるのにgrammarがほとんどunknown**

出所と文法を分離できたこと自体は成果だが、coverage改善ではない。最頻のsource constructorに限定したgrammar情報が必要。全語彙へ単純なsafe flagを付けて解決しない。

**B. Builder入力に必要な過去設定が存在しない**

trace型を追加しても輸送不能は解消しない。existing bound constructorで証明できる範囲だけ進める。新serialized metadataや公開context設計が必要なら、R4.3外の明示的設計判断へ分ける。

**C. common proofは通るが6 family constructorが成立しない**

必要なattachment/owner/predicateの証明が不足している。`direct_supported_families`を単に全6へ広げてはいけない。

**D. 1修正あたり1～2件しか増えず、同じ場所の語彙表が増える**

blocker交差matrixへ戻る。大きい単独blockerや組合せを改善するタスクへ変える。個別seedの救済を継続しない。

**E. 6 family名は出るが通常実v2が増えない**

alias/forced/declaredの混同を疑う。実`realizer_version`とselected constructor、cleaned outputまで確認する。

**F. semantic signatureは一致するのに不自然な文が出る**

signatureは粗いprojectionであり、自然性や全関係の同値を保証しない。source atom、ownership、polarity、最終文レビューへ戻る。signature維持だけでPASSにしない。

---

## 19. 最終handoffチェックリスト

- [ ] 指定ブランチの現在コードに基づいており、古いZIPや別branchのsourceと混ざっていない。
- [ ] 実装・宣言・強制描画・通常実行・fallbackを別々に計測できる。
- [ ] typed evidenceはruntime-onlyであり、JSONノード境界の輸送問題をごまかしていない。
- [ ] exact replayとbound constructorを区別し、不足入力を推定で埋めていない。
- [ ] source membershipを文法保証と扱っていない。
- [ ] family-specific proofとconstructorが同じinput bindingへ結び付く。
- [ ] v1互換adapterの役割と将来の撤去条件が記録されている。
- [ ] 既存9成功例、残るfallback、negative fixtures、V150・公開API・rollbackが守られる。
- [ ] 今回のtest集合と過去のtest集合の差を説明できる。
- [ ] 新規CLIはGit管理されたsourceからfresh checkoutで実行できる。
- [ ] A1.6のlock・測定器・family mappingを変更していない。
- [ ] formal未実施はNOT_RUN、証拠欠損はBLOCKEDとして明示する。
- [ ] 最終成果を「工程が進んだこと」と「実用的に適用範囲が広がったこと」に分けて報告する。
- [ ] mainへのmerge・N2.8・D3を自動開始していない。

---

## 20. 参照元と確認範囲

参照は設計基準HEADに固定した一次ソース。本文の`[Sxx]`は以下に対応する。現在のbranchが進んだ場合は、古い行番号よりsymbol名と差分を優先する。

- **[S01] 開発ブランチ案内・検証集合・既知除外:** [development_branch.md](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/docs/diversity_refactor/development_branch.md)
- **[S02] branch HEAD・commit履歴:** [9a2aa32c1e3a48d1d7ea51eb91aee42843dba021](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/commit/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021)
- **[S03] A1.6 lock・candidate07の記録・正式評価の制約:** [progress.md](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/docs/diversity_refactor/progress.md)
- **[S04] direct経路の入口と最大3 familyの制限:** [v2_direct_provenance.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/pipeline/v2_direct_provenance.py)
- **[S05] template選択・candidate bridge呼出し・後処理:** [prompt_renderer.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/prompt_renderer.py)
- **[S06] 公開node I/O・context_json境界:** [nodes_context.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/nodes_context.py)
- **[S07] canonical workflow runner・execution trace・seed解決:** [workflow_prompt_runner.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/tools/workflow_prompt_runner.py)
- **[S08] 既存Action traceとreplay binding:** [action_renderer.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/pipeline/action_renderer.py)、[v2_structural_evidence.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/pipeline/v2_structural_evidence.py)
- **[S09] Clothingの選択・描画・signature・履歴:** [clothing_candidate_renderer.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/pipeline/clothing_candidate_renderer.py)、[clothing_builder.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/pipeline/clothing_builder.py)
- **[S10] Sceneの選択・shuffle・dedupe・履歴:** [location_builder.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/pipeline/location_builder.py)
- **[S11] 6 familyの正本metadata:** [natural_language_realizer_v2.json](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/vocab/data/natural_language_realizer_v2.json)
- **[S12] 既存Realizer/Builder metadataテスト:** [test_prompt_realizer_v2.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/assets/test_prompt_realizer_v2.py)
- **[S13] candidate選択・v1 fallback mapping:** [v2_candidate_bridge.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/pipeline/v2_candidate_bridge.py)
- **[S14] 既存selector・family安全判定:** [syntax_family_selector.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/pipeline/syntax_family_selector.py)
- **[S15] ContentPlan・6構文の描画:** [prompt_realizer.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/pipeline/prompt_realizer.py)
- **[S16] Builderが実際に利用するcontext/state:** [prompt_orchestrator.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/pipeline/prompt_orchestrator.py)
- **[S17] bounded leaf grammarとsemantic/grammatical head区別:** [v2_leaf_grammar.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/pipeline/v2_leaf_grammar.py)
- **[S18] 正式Auditのsource/config・active family設定:** [audit_effective_diversity.py](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/tools/audit_effective_diversity.py)
- **[S19] 上位仕様・既存タスク:** [spec.md](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/docs/diversity_refactor/spec.md)、[tasks.md](https://github.com/Shiba-2-shiba/ComfyUI-Scripted-Context-Generator/blob/9a2aa32c1e3a48d1d7ea51eb91aee42843dba021/docs/diversity_refactor/tasks.md)

### 確認範囲

本計画書は上記branchのコード・仕様・検証記録を参照して作成した。新規dataclass、audit、verifier、R43タスク群は未実装の提案である。本計画書作成時にrepoのテスト・ComfyUI・formal gateは実行していない。実際のbaseline取得と検証はR43-00以降の実装作業で行う。

---

## 結語

R4.3の中心は「認識できる完成文を増やすこと」ではない。

**現在の生成情報から何を証明できるかを可視化し、同じ証拠を6構文がそれぞれ必要な条件で再利用できるようにすること**である。

共通化とcoverage改善を別に評価し、根拠のない安全許可を増やさず、正式採用条件を維持する。
