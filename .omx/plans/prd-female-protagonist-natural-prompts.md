# 女性主人公・一貫性・自然文・多様性リファクタリング計画

Status: Superseded by `prd-prompt-quality-engineering-loop.md`
Planning mode: RALPLAN-DR short consensus
Scope: 計画のみ。実装は別の承認済み実行レーンで行う。

> 2026-08-24: ユーザー要望により、静的な段階リファクタリング計画から、workflow同等生成・評価・小差分修正を反復するloop engineering計画へ置き換えた。本書は設計論点の参照用として残す。

## 1. 要求概要

このリファクタリングの目的は、生成数を増やすこと自体ではなく、次の4つを同時に満たす生成基盤へ整理することである。

1. 主人公は原則として単一の女性であり、prompt全体で人物同一性が崩れない。
2. subject、character traits、clothing、location、action、emotion、garnishの意味が整合する。
3. 最終promptは重複したタグ列ではなく、読みやすい自然な英語文として出力される。
4. 同じ条件でもseedに応じて、意味・行動・場面・構文の各層で多様性が生まれる。

既存の `context_json`、ComfyUI node I/O、seed determinism、semantic-only policy、legacy payload読込は維持する。

## 2. RALPLAN-DR

### Principles

1. **主人公契約を先に固定する** — 女性主体の同一性はrendererの語句置換ではなく、生成stateの不変条件として扱う。
2. **一貫性を生成前に保証する** — 最終cleanerで矛盾を隠さず、候補生成・選択時に不整合を除外または減点する。
3. **多様性を層別に測る** — variation総数だけでなく、semantic、lexical、syntactic、temporalの各多様性を分ける。
4. **自然文は構造から作る** — comma tag列の後処理ではなく、役割付きintermediate representationから文を組み立てる。
5. **互換性と決定性を継続検証する** — 公開I/Oとseed出力を段階ごとのgateにする。

### Decision drivers

1. 女性主人公とscene/action/clothing/emotionの矛盾を機械的に検出できること。
2. 品質低下を伴わずに語彙・scene・構文を継続拡張できること。
3. 現行workflowとcontext JSONを破壊せず、小さい差分で移行できること。

### Viable options

#### Option A: 語彙とテンプレートを先に増やす

- 長所: 変更が局所的で、短期的に出力数を増やしやすい。
- 短所: 現在の状態境界と整合判定を改善しないため、矛盾・言い換え重複・不自然な連結も同時に増える。

#### Option B: 主人公中心のtyped generation stateと役割付き表現を導入する（採用案）

- 長所: 一貫性、多様性、自然文品質を独立に測定・改善できる。既存extrasから段階移行可能。
- 短所: 初期のbehavior lockとadapter整備が必要で、短期的な語彙増加は遅くなる。

#### Option C: prompt生成全体を新pipelineへ一括置換する

- 長所: 最終形を早く単純化できる可能性がある。
- 短所: seed、history、workflow、legacy context、semantic EPIGの回帰面が大きく、原因分離が困難。

#### Option D: 既存slot/selectorを局所強化する

- 長所: 現在のaction slot、semantic family、template role、domain selectorを保ち、identity validatorとlate-stage content planだけを追加するため、差分と互換性リスクが最小。
- 短所: stage間で構造化情報が文字列へ戻る問題と、debug historyをruntime memoryとして読む問題が残り、長期的な一貫性保証に限界がある。

### Decision

Option Bを、Option Dの小さい移行面を取り込んで段階導入する。既存 `PromptContext` とpublic nodesは維持し、既存action slotとdomain selectorを型昇格・合成する。新しい並列生成系は作らない。各段階で旧経路とのshadow comparisonを行い、品質gateを満たした領域だけ切り替える。

## 3. 非目標

- LLM依存の導入。
- art style、camera、quality tag、body-shape emphasisの再導入。
- 初期フェーズでのComfyUI socket/widget変更。
- variation countのみを目的としたsubject/location/actionの無制限追加。
- 既存compatibility facadeの即時削除。
- 女性主人公を性的・年齢依存の属性で固定すること。年齢や外見は明示されたprofileだけから得る。

## 4. 目標アーキテクチャ

生成処理を以下の5段に整理する。

1. **Identity** — 主人公の人数、女性主体、character id、外見、personality、source subjectを確定。
2. **Scene model** — location、purpose、time、weather、social distance、objectsを正規化。
3. **Intent and action** — 主行動、姿勢、手の動作、視線、対象物、進行状態を役割付きslotで表現。
4. **Constraint and variation selection** — hard conflict除外、soft conflict減点、履歴反復減点、semantic ranking。
5. **Natural-language realization** — 主語、動詞、目的語、修飾、scene clauseを構文variantで実現し、最後に軽量normalize。

`PromptContext` は安定した境界DTOとする。内部ではversioned `GenerationModel` を唯一の正規形とし、`protagonist / scene / action / fragments / selection_memory` を含める。認識可能な `extras["generation"]` を最優先で読み、存在しない旧contextだけをtop-level fieldsとflat extrasから導出する。書込時はGenerationModelを正とし、top-level fieldsと既存flat extrasをlegacy projectionとして生成する。unknown extrasはpassthroughする。

共通化するのは万能candidate modelではなく、次の結果protocolとreason-code体系に限定する。domain固有のrule、candidate型、selectorは既存moduleに残す。

```text
ConstraintResult
  hard_violations[]
  soft_penalties[]
  diversity_penalties[]
  total_penalty
  reason_codes[]
  survivor_count
```

## 5. 段階的実装計画

### Phase 0: 品質ベースラインとbehavior lock

対象:

- `tools/audit_prompt_repetition.py`
- `tools/audit_template_diversity.py`
- `tools/run_bias_audit.py`
- `assets/test_determinism.py`
- `assets/test_prompt_snapshots.py`
- 新規の固定評価fixtureと集計ツール

作業:

1. 現行pipelineから、subject × location × mood × seedを層化した固定corpusを作る。
2. 次のbaselineをJSONで記録する。
   - female protagonist coverage
   - solo-person conflict rate
   - subject/pronoun drift rate
   - location/action/object conflict rate
   - exact prompt duplicate rate
   - repeated n-gram rate
   - action verb / object / location / template-part entropy
   - sentence fragment、dangling modifier、duplicate subject mentionの件数
3. 既存394 unittest、data validators、workflow widget testを必須gateとして固定する。
4. snapshotは少数の代表seedに限定し、大規模品質評価は統計gateに分離する。

完了条件:

- 同一commit・同一seedで評価corpusがbyte-identicalになる。
- hard contradictionを分類する機械可読taxonomyがある。
- 現行値と改善目標を同じreport schemaで比較できる。

### Phase 1: 女性主人公のidentity contract

対象:

- `core/schema.py`
- `core/context_state.py`
- `core/context_ops.py`
- `pipeline/source_pipeline.py`
- `pipeline/character_profile_pipeline.py`
- `character_service.py`
- `vocab/data/character_profiles.json`
- `vocab/data/variation_scope.json`

作業:

1. 入力policy matrixを固定する。
   - default/prompts/profile入力: `single_female` を必須とする。
   - explicit/legacy JSON: 非女性・複数・曖昧主体を含め読込とround-tripは変更しない。
   - natural renderer: supported `single_female` のみ生成成功扱いとし、その他はstable reason code付きでlegacy rendererへfallbackする。
   - female coverage 100%の分母: natural rendererで生成に成功したsupported inputとする。
   - `source_subj_key`: 表層主語ではなくcompatibility archetypeとして保持する。
2. 内部 `ProtagonistState` を定義する。
   - `entity_id`
   - `count`（default 1）
   - `gender_presentation`（default female）
   - `subject_label`
   - `pronouns`
   - `character_profile_id`
   - `visual_traits`
   - `personality`
3. `character_service` が持つprofile key、compatibility key、display nameの区別を再利用し、既存 `subj`、profile、extrasから決定論的に構築するadapterを追加する。
4. subject taxonomyを追加し、single female、非女性、複数人物、曖昧なroleを区別する。
5. public `context_version` は変更せず、旧payloadはadapterで正規化する。
6. downstream stageは文字列 `ctx.subj` の再解釈を避け、`ProtagonistState` を参照する。

完了条件:

- active variation scopeの全subjectがtaxonomyで分類される。
- natural rendererで生成に成功したsupported inputの女性主人公coverageが100%。
- solo modeで複数人物・男性代名詞・主人公の再定義が0件。
- legacy contextと既存snapshotが意図した差分以外で変化しない。

### Phase 2: GenerationModel、state ownership、SelectionMemory

対象:

- `core/context_state.py`
- `core/context_ops.py`
- `pipeline/context_pipeline.py`
- `history_service.py`

作業:

1. namespaced `extras["generation"]` とschema versionを定義する。
2. 読込優先順位を「認識可能なGenerationModel → legacy fieldsからderive」、書込を「GenerationModel → legacy projection」と固定する。
3. `GenerationModel.from_context()` / `apply_to_context()` を唯一の変換境界にし、unknown extrasを保持する。
4. `extras` key registryとstage別ownershipを定義する。
5. typed `SelectionMemory` を導入し、contextを更新して返せるstageのverb/object/location familyをカテゴリ別の固定長dequeとして保持する。
6. 旧contextではhistoryから一度だけSelectionMemoryをderiveし、以後の生成判断はhistoryではなくSelectionMemoryを参照する。
7. historyは互換・観測用traceとして残し、debug envelopeに `decision_schema_version` と `pipeline_version` を記録する。

完了条件:

- 各extras keyのwriterが原則1 stageに限定される。
- legacy flat stateとGenerationModelの優先順位がcontract testで固定される。
- SelectionMemoryのverb/object/location各カテゴリが指定上限を超えない。
- runtime selectionがfree-form debug historyのfield shapeに依存しない。
- `ContextPromptBuilder` は更新contextを返さないため、template/syntax historyは永続SelectionMemoryに含めない。
- context JSON round-tripと既存public node specsが不変。

### Phase 3: domain constraint合成による一貫性保証

対象:

- `core/solo_safety.py`
- `core/semantic_policy.py`
- 新規 `core/constraint_result.py`
- `pipeline/action_generator.py`
- `pipeline/action_relation_binder.py`
- `pipeline/location_builder.py`
- `pipeline/clothing_candidate_selector.py`
- `vocab/data/scene_compatibility.json`
- semantic profile JSON群

作業:

1. 制約を次の3種類に統一する。
   - hard reject: 主人公人数、gender/pronoun、物理的不可能、solo-person conflict
   - soft penalty: TPO、mood/action距離、personality/action距離、weather/clothing違和感
   - diversity penalty: recent verb/object/location/template/semantic family反復
2. 共通化は `ConstraintResult` とstable reason codeに限定し、domain ruleとcandidate型は各既存moduleに残す。
3. `CandidateDecision` はdebug DTOとしてのみ使用し、domain modelにしない。
4. reject/penalty理由、survivor count、fallback rateを `DebugInfo.decision` に記録する。
5. 最終prompt後の検出だけでなく、候補選択前後の両方にvalidatorを置く。
6. fallbackは制約を迂回せず、同じdomain rule compositionを通す。

完了条件:

- 定義済みhard contradictionが固定corpusで0件。
- 全選択stageがselected candidate、rejected reasons、penaltiesをdebugに残す。
- fallback pathにも通常pathと同じsafety/consistency gateが適用される。
- hard/soft/diversity penalty、survivor count、candidate exhaustion、fallback rateが同一reportで確認できる。
- seed determinismが維持される。

### Phase 4: action/garnishを役割付きsemantic frameへ統合

対象:

- `pipeline/action_parser.py`
- `pipeline/action_generator.py`
- `pipeline/action_renderer.py`
- `pipeline/action_relation_binder.py`
- `vocab/garnish/logic.py`
- `vocab/personality_semantics.py`
- emotion / action descriptor JSON群

作業:

1. 既存action slot dictを新系統へ置換せず `ActionFrame` dataclassへ型昇格する。
   - main verb
   - object
   - posture
   - hand action
   - gaze target
   - progress
   - stimulus/obstacle
   - social relation
2. `parse_pool_action_to_slots()` はlegacy string adapterとして維持し、persisted frameとdebug slotsの一致をcontract化する。
3. `ActionFrame` をGenerationModelへ保存し、`ctx.action` はlegacy projectionにする。
4. garnishを独立tagではなく、subject / action / stimulus / context roleへ束縛する。
5. 既存semantic family budgetをframe-level重複検査へ段階移行する。
6. personalityとemotionは行動を上書きせず、候補rankingのpriorとして使う。
7. source action poolは旧文字列とstructured entryを併用できるadapterを持つ。

完了条件:

- actionとgarnishに同義の姿勢・視線・手動作が重複しない。
- descriptorの主体が主人公かsceneかをdebugから追跡できる。
- 旧action poolの全entryがparseまたは明示fallbackされる。
- persisted ActionFrameとdebug slot payloadが一致する。
- action verb/object entropyがbaseline未満にならない。

### Phase 5: 自然言語realizerの分離

対象:

- `prompt_renderer.py`
- `pipeline/prompt_orchestrator.py`
- 新規 `pipeline/prompt_realizer.py`
- `vocab/data/template_catalog.json`
- `vocab/templates_intro.txt`
- `vocab/templates_body.txt`
- `vocab/templates_end.txt`
- `nodes_prompt_cleaner.py`

作業:

1. rendererを以下に分割する。
   - content plan生成
   - clause ordering
   - lexical choice
   - surface realization
   - punctuation/normalization
2. `ProtagonistState` と `ActionFrame` から主語・動詞の一致した文を作る。
3. templateは文字列断片ではなく、必要roleと利用可能slotを宣言する。
4. 同一情報の再言及をcontent plan段階で除外する。
5. PromptCleanerは構造修復器ではなく、禁止語・空白・軽微な句読点の最終guardへ縮小する。
6. intro/body/endと構文familyは、永続historyではなくnamed seedによるstratified selectionと固定corpusの分布gateで反復を制御する。
7. activation contractを固定する。
   - `composition_mode=False`: custom/legacy rendererを維持する。
   - `composition_mode=True`: 新content-plan realizerの対象とする。
   - 初期はlegacy/newをnamed seed streamでshadow生成し、ユーザー出力は旧経路を維持する。
   - gate通過後にcomposition mode内部を切り替え、opt-in natural modeとして公開する。
   - Phase 7Bで、workflow sampleとREADMEを `composition_mode=True` 推奨へ更新する。
   - Phase 7BのE2E・expected-diff・移行案内が承認された場合に限り、widget defaultをTrueへ切り替える。明示的Falseでlegacy rendererを継続利用可能にする。
8. semantic slots、discourse roles、syntax familyを別概念として定義する。
   - semantic slots: subject / predicate / object / adjunct / scene
   - discourse roles: focused / quiet / transition / social
   - syntax family: subject-first / action-first / scene-tail / two-sentence等
9. identity、scene、action、lexical、syntax、templateにnamed `mix_seed` streamを割り当て、候補数変更による乱数消費の連鎖を局所化する。

完了条件:

- 固定corpusでsentence fragment、dangling modifier、主語重複が0件。
- 同一prompt内の重複semantic familyが定義閾値以下。
- template part coverageとentropyがbaseline以上。
- PromptCleanerの変換前後で意味slotが失われない。
- 同一pipeline version内で各named streamと最終出力が再現可能。
- 意図的切替stageだけがversioned expected-diff corpusで差分を持つ。

### Phase 6: 多様性の層別拡張

対象:

- `vocab/source/action_pools/*.json`
- `vocab/data/action_pools.json`
- character / clothing / background / semantic descriptor data
- `tools/build_action_pools.py`
- `tools/build_compatibility_review.py`
- diversity audit tools

作業:

1. 多様性を4層で管理する。
   - semantic: activity、goal、emotion、object relation
   - scene: location、time、weather、social context
   - lexical: verb、noun、modifier
   - syntactic: clause order、sentence pattern、information density
2. 新規語彙にはrole、semantic family、compatibility tags、rarity weightを要求する。
3. 重複を増やすだけの近似表現はcanonical conceptへ束ねる。
4. subject/location/action追加はscope、compatibility CSV、runtime JSONを一括検証する。
5. 長いhistoryだけに頼らず、seed由来のstratified selectionで低頻度候補にも到達可能にする。

完了条件:

- exact duplicate率と上位n-gram集中率がbaselineより改善する。
- semantic、lexical、syntacticの各entropyが個別に報告される。
- 低頻度candidateが到達不能になっていない。
- source/runtime action poolとcompatibility reviewに差分がない。

### Phase 7: public contractと互換性の最終確認

対象:

- `nodes_context.py`
- `__init__.py`
- `workflow_widget_validation.py`
- `workflow_samples.json`
- `verification/frontend/*`
- `verification/browser/*`
- compatibility facade群

作業:

1. `INPUT_TYPES`、widget順序、RETURN_TYPES、FUNCTION名を固定するcontract testを強化する。
2. context schemaの新内部fieldはnamespaced extras adapter経由とし、public version変更は別計画に分離する。
3. browser round-tripまで通した後にのみ品質pipeline切替を完了扱いにする。
4. node module分割、loader/cache集約、facade整理は独立cleanup trancheへ移し、この品質改善のcritical pathから外す。

Phase 7B（必須の採用gate）:

1. opt-in natural modeの品質・画像prompt適合性・rollbackをE2Eで確認する。
2. `ComfyUI-workflow-context.json`、workflow sample manifest、READMEの推奨値を `composition_mode=True` に更新する。
3. widget defaultをTrueへ切り替えるexpected-diffと移行案内をレビューする。
4. frontend/browser round-tripが成功した場合のみdefault切替を採用する。失敗時はopt-inのままリリースし、Phase 7Bを未完了として残す。

完了条件:

- workflow import/save/reload後のcustom node snapshotが一致する。
- 旧workflow fixtureが変更なしで読み込め、更新sampleは明示的expected-diffとして検証される。
- public node mappingと表示名が不変。
- runtime codeがcompatibility facadeを新規利用しない。
- natural modeはPhase 5でopt-in利用可能になり、Phase 7Bの採用gate通過後に推奨workflowとwidget defaultになる。

### Follow-up cleanup tranche（品質pipeline切替後の別計画）

- domain JSON loader、path resolution、cacheをservice層へ集約する。
- `context_pipeline.py` の独自loader/cacheと薄いforwarding wrapperを整理する。
- `nodes_context.py` のComfyUI contract、stage adapter、inspector formattingを必要に応じて分割する。
- compatibility facadeは外部利用証拠とdeprecation期間が定義できたものだけ削除する。

## 6. 受け入れ基準

### Functional

- default generationの100%で単一女性主人公が保持される。
- hard contradiction corpusで違反0件。
- legacy context、public node I/O、workflow round-tripが維持される。
- 同一入力・同一seedの出力とdebug decisionが再現可能。
- 旧版とのbyte一致は未切替stageに限定し、意図的切替stageはversioned expected-diffで承認される。

### Natural language

- 固定corpusで不完全文、dangling modifier、重複主語が0件。
- action、garnish、scene間の同義重複が自動検出される。
- 人手評価用の層化sampleで、少なくとも一貫性・自然さ・冗長性・多様性を5段階評価できる。
- Phase 0終了成果物として、固定sample数、評価者数、paired preferenceのpromotion条件、属性保持・画像prompt適合性の非回帰条件をversioned quality contractへ保存する。以降の変更には計画更新を要求する。

### Diversity

- exact duplicate率、repeated n-gram率、top verb/object/template shareに回帰がない。
- action verb、object、location、template part、syntax family、semantic familyのentropyがbaseline以上。template/syntaxは永続memoryではなくseed分布として評価する。
- variation countは品質gate通過candidateのみを数える。

### Compatibility and quality

- Python unittest全件成功。
- prompt/data/full-flow/widget/source-runtime check全件成功。
- Vitest frontend compatibility/round-trip成功。
- Playwright workflow import/save/reload成功。
- 新規dependencyなし。

## 7. リスクと緩和策

| Risk | Impact | Mitigation |
|---|---|---|
| 女性主体の強制が既存role語彙を不自然にする | subject diversity低下 | roleとgender presentationを分離し、surface realizationで女性主体を表現 |
| typed state導入でlegacy extrasが欠落 | workflow互換性破壊 | bidirectional adapter、unknown key passthrough、round-trip fixture |
| 制約を強めすぎて候補枯渇 | fallback固定化、反復増加 | hard/soft/diversityを分離し、候補数とfallback理由を監視 |
| 自然文realizerがtemplate diversityを減らす | 文体の単調化 | syntax familyとlexical choiceを別々に測定・選択 |
| 大規模snapshotが実装を固定しすぎる | 改善困難 | 少数behavior snapshot + 統計的品質gateの二層化 |
| historyが肥大化する | context JSON増大 | audit後にbounded summaryを別計画で検討。初期段階では形式のみ整理 |
| facade削除で外部利用者が壊れる | 外部回帰 | この計画では削除せず、利用証拠とdeprecation期間を要求 |

`history` リスクの緩和策はPhase 2の固定長SelectionMemory導入へ変更する。history自体はtraceとして残すが、生成判断の正規入力にしない。

## 8. 検証手順

各Phaseで最低限次を実行する。

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest discover -s assets -p "test_*.py"
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
python tools/check_widgets_values.py
python tools/build_compatibility_review.py --check
python tools/build_action_pools.py --check
```

renderer/node契約を変更するPhaseでは追加でfrontend Vitestとbrowser Playwright round-tripを実行する。Phase 0で定義した品質auditは全Phaseでbefore/after比較し、hard contradictionの増加、determinism差分、いずれかのdiversity metric回帰があれば切替を停止する。

## 9. ADR

### Decision

主人公中心のversioned GenerationModel、共通ConstraintResult protocol、既存action slotのActionFrame型昇格、role-aware natural-language realizerを既存context-first pipeline内に段階導入する。

### Drivers

- 主人公同一性とscene整合を明示的に保証する必要がある。
- 多様性を語彙件数ではなく意味・語彙・構文の各層で改善する必要がある。
- 既存workflow、seed、legacy payloadを維持する必要がある。

### Alternatives considered

- 語彙・templateのみ先行拡張。
- pipelineの一括再実装。
- 既存slot/selectorの局所強化だけに留める案。

### Why chosen

段階導入は、一貫性・自然文・多様性の改善を個別に測定でき、既存の豊富な回帰テストと互換性contractを最大限利用できるため。

### Consequences

- 初期は評価基盤とadapter整備が中心となり、見た目の語彙増加は少ない。
- 内部modelとdebug contractは増えるが、namespaced schema、legacy projection、typed SelectionMemoryにより真実の優先順位が明確になる。
- 完了後は新規subject/location/action/templateを同じ品質gateで追加できる。

### Follow-ups

- Phase 0で人手評価基準と統計閾値を確定する。
- 外部facade利用状況を別途調査する。
- history圧縮、performance、context schema version更新は独立計画として判断する。

## 10. Planning changelog

- Initial draft created from repository analysis and fresh 394-test baseline.
- Architect feedback applied: identity policy matrix、versioned GenerationModel precedence、SelectionMemory、Option D、existing-slot ActionFrame、ConstraintResult protocol、renderer activation/rollback、named RNG streams、cleanup tranche分離を追加。
- Architect re-review applied: template/syntaxを永続SelectionMemoryから除外し、Phase 7Bでnatural modeの推奨workflow・default採用gateを必須化。
