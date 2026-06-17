# EPIG Reference Refresh Specification

対象リポジトリ: `ComfyUI-Scripted-Context-Generator`
作成日: 2026-06-16
関連文書:

- `docs/emotion_epig/spec.md`
- `docs/emotion_epig/progress.md`
- `docs/semantic_epig/implementation_spec.md`
- `docs/semantic_epig/refactor_spec.md`
- `docs/semantic_epig/reference_refresh_progress.md`
- `docs/semantic_epig/reference_refresh_tasks.md`

---

## 1. 結論

現行の Semantic EPIG 実装は、論文から抽出した主要方針をすでに反映している。

- Valence-Arousal 座標による emotion garnish ranking
- subject-centric な身体表出への変換
- role-aware debug
- semantic space / descriptor ranking の共通化
- Action / Object Relation / Location / Clothing / Personality の all-active 化
- active/passive audit と validator
- builder responsibility split

ただし、追加で見つかった資料に含まれる実データは未反映である。

- `参考/EPIG/data/NRC_VAD_with_subject_centric.csv`
- `参考/EPIG/data/llm_expanded_prompts.csv`
- `参考/NRC-VAD-Lexicon-v2.1/...`
- `参考/2503.23547v1.pdf`
- `参考/lexicons.html`
- `参考/EmotionDynamics`

よって、追加リファクタは不要ではない。ただし大きなコード刷新ではなく、辞書参照・検証・小さな data-only 実験として進める。

Reference material handling policy:

- `C:\Users\inott\Downloads\新しいフォルダー (3)\参考` 配下の原資料は commit に含めない。
- 元リポや参照資料の raw data をそのまま流用・転載・dump して tracked data にしない。
- NRC/EPIG/EmotionDynamics 由来の raw data や score-bearing overlay は、local audit / calibration の入力として使用してよい。
- repo に採用するのは、現在のリポ用に加工・選別・再構成した data / rules / tests に限定する。
- 加工済み data は、元データの単なる行コピーではなく、このリポの semantic-only policy、domain schema、descriptor品質基準に合わせて作成する。
- score-bearing overlay を runtime に使う場合も、元ファイルをそのまま同梱するのではなく、このリポ用の派生形式・必要最小範囲・配布条件を明示する。

---

## 2. 追加資料から得た差分

### 2.1 EPIG repository

`参考/EPIG/README.md` によると、EPIG は training-free な emotional control 手法であり、心理学的 Valence-Arousal 次元と role-aware decomposition を使って prompt を補強する。

含まれる主要データ:

| File | 観察結果 | 現行実装との差分 |
|---|---|---|
| `NRC_VAD_with_subject_centric.csv` | 19,970 rows, `subject_centric=1` は 965 rows | 現行実装は subject-centric フラグ付き辞書を読まない |
| `llm_expanded_prompts.csv` | expanded prompt 例がある | camera / quality / style / render 語が多く、semantic-only 方針にそのまま使えない |
| notebooks | preprocessing / evaluation / LLM expansion | 新依存や notebook runtime は導入対象外 |

### 2.2 NRC-VAD-Lexicon-v2.1 and `2503.23547v1.pdf`

`参考/NRC-VAD-Lexicon-v2.1` には新版 VAD 辞書が含まれる。

`参考/2503.23547v1.pdf` is the NRC VAD Lexicon v2 paper:

- Title: `NRC VAD Lexicon v2: Norms for Valence, Arousal, and Dominance for over 55k English Terms`
- arXiv: `2503.23547v1`
- Submitted: 2025-03-30
- Key claims: human V/A/D ratings for more than 55,000 English words and phrases; about 25k additional words over v1.0; first inclusion of about 10k common multi-word phrases; VAD associations are reported as reliable; data is made freely available for research through the project webpage.

観察結果:

| File | Lines | Notes |
|---|---:|---|
| `NRC-VAD-Lexicon-v2.1.txt` | 54,802 | `term`, `valence`, `arousal`, `dominance`; score range は -1..1 |
| `Unigrams/unigrams-NRC-VAD-Lexicon-v2.1.txt` | 44,729 | unigram subset |
| `MWE/mwe-NRC-VAD-Lexicon-v2.1.txt` | 10,074 | multi-word expression subset |
| `OneFilePerDimension/PolarSubset/valence-polar-NRC-VAD-Lexicon-v2.1.txt` | 29,042 | polar subset |

現行 `vocab/data/emotion_vad_profiles.json` は小さな手書き profile で、0..1 scale の valence/arousal のみを扱う。NRC v2.1 の dominance と MWE は未使用。

Implication for this repo:

- Exact MWE phrase matching should be part of the overlay lookup, not only unigram token fallback.
- Dominance should be evaluated as an audit-only signal for personality confidence/restraint and action power/agency before any active runtime use.
- The current hand-authored V/A profiles should be calibrated by reporting distance to reference terms, not replaced wholesale.
- Because the paper points to the project webpage for the lexicon, the data usage gate is governed by the project/lexicon terms, not just the arXiv paper license.

### 2.3 lexicons.html

`参考/lexicons.html` は NRC/Saif Mohammad 系 lexicon の一覧ページ保存版である。

追加で有用な候補:

| Lexicon | Relevance | Use in this repo |
|---|---|---|
| NRC Emotion Lexicon / EmoLex | 8 emotion categories and positive/negative associations | emotion category coverage audit only |
| NRC Emotion Intensity Lexicon | emotion intensity for basic emotions | garnish intensity calibration audit |
| NRC VAD v2.1 | V/A/D scores for unigram and MWE terms | primary VAD reference alignment |
| NRC WorryWords | calmness-anxiety dimension | anxiety/tense nuance calibration, audit-only unless data is locally available |
| NRC Words of Warmth | warmth, competence, sociability, trust | personality axes audit for warmth/sociability/confidence |
| Sentiment Composition Lexicons | negator/modal/adverb effects | out of scope for prompt generation; possible future text parser audit |
| Colour Lexicon | word-colour association | out of scope for semantic EPIG; do not mix with prompt style/color control unless separately specified |

Terms note:

- The page states the resources are free for research use with citation/attribution expectations.
- Commercial/product use requires separate contact/licensing.
- Data redistribution is not allowed; direct users to the original source page instead.

Therefore, reference extraction should default to local generated artifacts under `assets/results/`. Raw NRC data or score-bearing overlays can be used for analysis, but tracked adoption must be transformed into this repo's own curated/derived format.

For this repo, the implementation path is:

```text
reference materials -> local audit/calibration -> repo-specific curated/derived data
```

This path is not allowed:

```text
reference materials -> copied raw rows / copied lexicon dump -> tracked project data
```

### 2.4 EmotionDynamics

`参考/EmotionDynamics` is available as a completed local clone. Git metadata commands are blocked by `safe.directory` ownership protection, but the worktree files are readable.

Observed structure:

```text
README.md
LICENSE
code/
data/
lexicons/
```

Relevant files:

| File | Use |
|---|---|
| `README.md` | Describes Utterance Emotion Dynamics (UED), rolling windows, and VAD/EmoLex references |
| `code/README.md` | Describes per-utterance average lexicon score and lexicon token ratio |
| `code/uedLib/README.md` | Describes UED config and metrics such as home base, displacement, rise/recovery |
| `code/uedLib/lib/ued.py` | Implements rolling-window emotion-state sequence and per-speaker dynamics |
| `code/avgEmoValues.py` | Computes average emotion values and lexicon coverage per text row |
| `lexicons/NRC_VAD_*.csv` | VAD single-dimension files with `word,val` columns |
| `code/uedLib/lexicons/NRC-VAD-Lexicon.csv` | VAD combined file with `word,valence,arousal,dominance` |
| `lexicons/NRC_EmoLex_*.csv` | Binary emotion/sentiment association files |

Notes:

- The code is MIT licensed.
- The repository README still directs users to the original lexicon sources and terms of use for lexicon data.
- Requirements include pandas, numpy, scipy, nltk, PyYAML, python_box, tqdm, and HTMLParser. These dependencies should not be imported into this repo.
- A `.gitmodules` entry references `code/twTokenizer`, but the current reference-refresh plan should not depend on it.

Conclusion:

- Treat EmotionDynamics as a usable reference for lexicon lookup format, average emotion scoring, rolling-window VAD, and audit metrics.
- Do not import its dependencies or pipeline shape wholesale.
- Treat its bundled lexicon score files under the same redistribution gate as other NRC-derived data.

---

## 3. 現行実装評価

### 3.1 十分反映済み

以下は追加資料を見ても作り直す必要がない。

- `semantic_epig_config.json` による all-active domain control
- `vocab/semantic_space.py` の ranking utility
- `pipeline/semantic_epig.py` の debug helper
- `tools/audit_semantic_epig_outputs.py` の active/passive prompt audit
- Action / Object Relation / Location / Clothing / Personality の domain-specific modules
- public `Context*` node I/O を変えない方針
- semantic-only policy
- no new dependency policy

### 3.2 追加資料で改善できる余地

| Area | 現状 | 改善余地 |
|---|---|---|
| Emotion VAD | 手書き category / nuance profile | NRC/EPIG CSV で prototype と nuance の根拠を監査できる |
| Subject-centric garnish | subject-centric 方針は実装済み | EPIG CSV の `subject_centric=1` を descriptor候補や除外基準として使える |
| Dominance | 未使用 | personality confidence / restraint / action power感の補助軸として検証できる |
| MWE | 未使用 | multi-word emotion/state descriptor の候補抽出に使える |
| LLM expanded prompts | 未使用 | 直接利用は危険だが、anti-pattern / banned-term テスト素材として使える |

---

## 4. Refactor Principles

### 4.1 Behavior lock first

既存 active output をいきなり変えない。

最初に行うこと:

- 現在の emotion/personality/audit 出力を fixture 化する
- `validate_assets()` と focused unittest を通す
- new reference-derived data は passive/debug-only で接続する

### 4.2 Data-only first

NRC/EPIG の実データは、最初は runtime prompt を変えない。

許可:

- 辞書解析 script
- derived summary JSON
- audit report
- debug-only score comparison
- small fixture

禁止:

- public node UI 変更
- 新規 dependency 追加
- full raw NRC lexicon の無条件 repo 同梱
- LLM expanded prompt の直接 prompt insertion
- camera / quality / render / body-type 語の導入

### 4.3 License and redistribution gate

NRC VAD and related lexicons are external resources with Terms of Use. `lexicons.html` explicitly blocks redistribution of the data. repo に raw data または score-bearing 派生 data を追加する前に、配布可否を確認する。

この gate を通るまでの実装は、`参考/` 配下のローカル資料を読み取る analysis tool に留める。

### 4.4 Scale normalization

現行実装は 0..1 scale を使う。NRC v2.1 は -1..1 scale を使う。

変換:

```text
normalized = (raw + 1.0) / 2.0
```

EPIG `NRC_VAD_with_subject_centric.csv` は 0..1 scale なので変換不要。

---

## 5. Proposed Architecture

### 5.1 New reference audit tool

候補:

```text
tools/audit_epig_reference_alignment.py
assets/fixtures/epig_reference_terms.json
assets/test_epig_reference_alignment.py
```

役割:

- current `emotion_vad_profiles.json` と EPIG/NRC reference の距離を出す
- category / nuance / personality descriptor の VAD coverage を見る
- subject-centric descriptor候補を抽出する
- LLM expanded prompts から policy violation語を検出する
- lexicons catalog から利用可能な参照軸を report する
- EmotionDynamics local code and lexicon CSV availabilityを report する

この tool は repo config を変更しない。

### 5.2 Current-vocabulary reference overlay

ユーザー提案の「現在のリポで使用している語彙だけを追加資料から抜き出し、別ファイルとして参照する」方式を採用候補にする。

推奨 flow:

```text
repo vocab/data + garnish/action/location/clothing descriptors
  -> normalize terms and phrases
  -> lookup in EPIG subject-centric CSV / NRC VAD / EmotionDynamics local VAD/EmoLex / optional WorryWords / optional WoW
  -> write local overlay under assets/results/
  -> runtime reads overlay only in passive/debug mode
```

初期 output:

```text
assets/results/epig_reference_overlay.local.json
```

Do not commit this generated overlay by default. It can contain derived lexicon scores and therefore falls under the redistribution gate.

If runtime adoption is later approved, either of these adoption paths is acceptable:

- keep overlay local/generated and use it at development/audit time only
- use the overlay to guide creation of repo-specific curated data
- generate a minimal repo-specific derived overlay with documented source, transformation, and scope

### 5.3 Optional reference adapter

候補:

```text
vocab/epig_reference.py
```

責務:

- TSV/CSV の安全な読み取り
- score normalization
- subject-centric filtering
- term lookup
- MWE lookup
- lexicons catalog parsing summary
- EmotionDynamics lexicon CSV parsing summary

標準 library のみで実装する。

### 5.4 Derived data candidates

license gate 後にのみ追加を検討する。

```text
vocab/data/emotion_vad_reference_overrides.json
vocab/data/subject_centric_descriptor_candidates.json
```

最初は small curated subset にする。full lexicon import はしない。license gate が通らない限り、これらは tracked file ではなく local/generated artifact として扱う。

Tracked data must be authored as repo-native curated data:

- allowed: small hand-authored descriptors, hand-authored axis adjustments, fixture terms written for tests
- allowed: minimal derived overlays transformed for this repo's schemas and scope
- not allowed: raw rows copied from `参考/`, bulk score tables, full or partial lexicon dumps, unreviewed generated overlays

---

## 6. Domain-Specific Plan

### 6.1 Emotion VAD calibration

目的:

- current category VAD が EPIG/NRC reference と大きくずれていないか確認する
- `nuances` に入っている `tense`, `absorbed`, `relieved`, `awkward`, `content`, `bored` を reference lookup する

Acceptance:

- current profile と reference の distance report が出る
- default output は変わらない
- 差分が大きい term は override候補として docs に記録される

### 6.2 Subject-centric descriptor candidate audit

目的:

- EPIG CSV の `subject_centric=1` term を、expression/gaze/behavior/hands に使える候補へ分類できるか検証する

Guardrail:

- 単語だけでは prompt descriptor として弱いものが多いため、直接挿入しない
- 既存 garnish descriptor の validation/weight補助に使う

Acceptance:

- 既存 garnish tags のうち reference coverage があるものを report できる
- `subject_centric=0` の情景/物体寄り term を subject garnish に使わない
- report は `direct`, `needs_phrase`, `reject`, `unmatched` に分類する
- `needs_phrase` は参照語の直接採用ではなく、このリポ用に書き直す候補として扱う
- `assets/results/subject_centric_descriptor_candidates.json` は local/generated とし、runtime は読まない

### 6.3 Dominance pilot

目的:

- NRC dominance を personality/action の補助軸として使う価値を検証する
- 初期実装では runtime axis を追加せず、ランキング差分とリスク例だけを report する

候補マッピング:

| NRC dimension | Existing axis candidate |
|---|---|
| dominance high | confidence high / restraint low |
| dominance low | confidence low / restraint high |
| arousal high | motion_energy / time_pressure |
| valence high | warmth / sociability |

Acceptance:

- current personality descriptor ranking と dominance-projected ranking の差分を出す
- exact descriptor match と token fallback を区別する
- high-risk rank shift を review 対象として出す
- exact match が不足する場合は runtime 採用を延期する

Current decision:

- `assets/results/reference_dimension_projection.json` では personality projection 比較 99件がすべて token fallback 由来だった。
- high-risk rank shift は 15件あるが、自動採用には弱いため dominance の runtime axis adoption は `deferred`。
- dominance は当面 audit lens として維持し、runtime 反映する場合は別途 active/passive audit と regression test を要求する。

Acceptance:

- pilot は audit-only
- personality descriptors の ranking変化を JSON で比較できる
- active runtime には入れない

### 6.4 LLM expanded prompt negative corpus

目的:

- `llm_expanded_prompts.csv` は prompt品質の参考ではなく、policy/banned-term regression corpus として使う

Acceptance:

- camera / quality / style / render語の検出結果を report する
- body_type terms are counted explicitly, including zero-count results
- semantic-only validator の test corpus として使える候補を抽出する
- expanded prompt を runtime output に混ぜない
- full `llm_expanded_prompts.csv` is not copied into the repo
- tracked negative examples must be small and repo-authored, not copied reference rows

Current output:

```text
assets/results/llm_expanded_prompt_policy_audit.json
```

Current decision:

- The reference CSV is useful as a negative corpus because it contains camera / quality / style / render terms.
- Runtime prompt generation must not use expanded prompts as source data.
- The tracked fixture `assets/fixtures/semantic_policy_negative_examples.json` is hand-authored and only locks semantic policy detection.

### 6.5 EmotionDynamics audit lanes

EmotionDynamics suggests several useful audit-only metrics that fit this repo without adopting the external dependency stack:

| Metric idea | Source in EmotionDynamics | Use here |
|---|---|---|
| Lexicon token ratio | `avgEmoValues.py` / `numLexTokens`, `lexRatio` | coverage quality for current repo vocabulary |
| Average lexicon score | `avgEmoValues.py` / `avgLexVal` | compare current category/descriptor scores to reference VAD |
| Rolling VAD window | `uedLib/lib/ued.py` rolling window over token scores | prompt fragment sequence audit, not runtime generation |
| Home base | `uedLib/lib/ued.py` mean/std by speaker | optional long-sequence context audit |
| Displacement / rise / recovery | `uedLib/lib/ued.py` line analysis | likely out of scope for prompt generation; keep as research note |

Acceptance:

- Implement only stdlib-compatible readers for CSV score files if needed.
- Do not add pandas/numpy/scipy/nltk/PyYAML/python_box/tqdm dependencies.
- Do not copy EmotionDynamics code into runtime modules.
- Treat bundled lexicon score files as local reference inputs only.

### 6.6 Warmth / WorryWords audit lanes

`lexicons.html` から、VAD 以外に次の2軸は現行 semantic EPIG と相性がよい。

- WorryWords: `tense`, `anxiety`, `calm` nuance の audit
- Words of Warmth: personality axes `warmth`, `sociability`, `confidence` の audit

ただし、現時点で対応する data file は `参考/` に存在しない。まずは `lexicons.html` に存在する lexicon metadata を docs/audit report に記録し、data が追加された場合だけ local overlay lookup 対象にする。

Acceptance:

- missing data は warning として report する
- runtime prompt output は変えない
- optional lexicon が無くても audit tool は成功する

---

## 7. Verification Gates

Focused baseline:

```bash
python -m unittest assets.test_emotion_vad_profiles assets.test_emotion_vad_alignment assets.test_personality_semantics assets.test_personality_garnish assets.test_semantic_epig_audit
python tools/validate_prompt_data.py
python -c "from asset_validator import validate_assets; issues=validate_assets(); print(len(issues)); print(issues[:20])"
```

Reference audit smoke:

```bash
python tools/audit_epig_reference_alignment.py --epig-dir "../参考/EPIG" --nrc-dir "../参考/NRC-VAD-Lexicon-v2.1/NRC-VAD-Lexicon-v2.1" --output assets/results/epig_reference_alignment.json
python tools/extract_epig_reference_overlay.py --reference-root "../参考" --output assets/results/epig_reference_overlay.local.json
```

Before active behavior changes:

```bash
python -m unittest discover -s assets -p "test_*.py"
python tools/audit_semantic_epig_outputs.py --samples assets/fixtures/semantic_epig_audit_cases.json --seed-count 8 --output assets/results/semantic_epig_audit_reference_refresh.json
python tools/validate_prompt_data.py
python tools/verify_full_flow.py
```

---

## 8. Adoption Decision For This Wave

Decision:

```text
overall_decision=no_runtime_adoption_now
```

Rationale:

- Current Semantic EPIG runtime is sufficient for now.
- Reference overlays and score-bearing outputs stay local/generated.
- Subject-centric `needs_phrase` records are useful hints, but require repo-authored phrase rewriting before tracked adoption.
- Dominance remains audit-only because current projection evidence is token-fallback based.
- LLM expanded prompts contain semantic-only policy violations and remain negative corpus only.
- The small repo-authored negative fixture is acceptable because it does not copy reference rows.

Any future runtime adoption requires a new active/passive behavior spec, regression tests before code changes, and before/after prompt audit.

---

## 9. Definition of Done

This reference refresh is complete when:

- Current implementation is documented as mostly sufficient, not rewritten
- EPIG/NRC reference data gaps are measured
- A reference alignment audit tool exists
- No public node I/O changes are introduced
- No new dependency is introduced
- Runtime prompt output remains unchanged until explicit active adoption
- License/redistribution decision is recorded before adding derived reference data
- Current-repo vocabulary overlay is generated locally rather than tracked by default
- `参考/` remains an uncommitted local reference source
- Any tracked adoption is transformed for this repo's schema/scope, not copied from source data
- Repo-native curated artifacts remain the default adoption path
- LLM expanded prompts are treated as negative/policy corpus, not prompt source
- EmotionDynamics is reviewed as a reference source without importing its dependency stack
- Remaining active behavior changes, if any, are backed by before/after audit
