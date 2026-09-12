# R44 Realizer v2 Coverage Engineering Design

**Repository:** `Shiba-2-shiba/ComfyUI-Scripted-Context-Generator`  
**Target development branch:** `refactor/realizer-v2`  
**Authoring baseline HEAD:** `b16a4dbca7d91d6d1cdefbfd521fd6a44787765a`  
**Runtime candidate source identity at the latest verified AS01 checkpoint:** `53a4fe8048cfd71cdcd9f3a7cb414e0b96ec6c0450b96795c465470d6963b56e`  
**Current measured ordinary coverage:** `11 / 512`, `3` ordinarily executed syntax families  
**Forced real-input proof:** all `6` required families  
**Remaining ordinary fallback:** `501 / 512`

## 1. Purpose

R44 is a bounded development wave whose purpose is to increase **ordinary Realizer v2 reachability** without weakening semantic preservation, source binding, grammar proof, or deterministic replay.

The development target is:

- ordinary v2 applications: **>= 64 / 512**
- ordinarily executed required syntax families: **>= 5 / 6**
- all six required families retain real-input forced proof
- all pre-R44 ordinary v2 successes remain preserved
- remaining fallback cases remain exact v1-compatible outputs unless they are newly, explicitly proved for v2
- upstream semantic choices, `ActionFrame`, context, public node I/O, and V150 protected data remain unchanged

Reaching `64/512` and `5` ordinary families is a **development-readiness guide**, not formal adoption. R44 does not automatically run the heavy formal 8192/2048/fixed80/blind-review/release gates and does not authorize N2.8 or D3.

## 2. Why R44 exists

The current branch has already solved the hard architectural problem: v2 realization is no longer authorized merely by a family label or by a permissive text heuristic. Current code reconstructs producer evidence, binds it to the exact current inputs/source, derives grammar/ownership facts, builds `FamilyProof`, and fails closed when proof is unknown.

The limiting factor is now **coverage economics**. Recent work increased ordinary v2 coverage from 10 to 11 cases while adding substantial grammar, evidence, and adversarial testing. Continuing by manually recognizing one whole phrase at a time will scale poorly.

R44 therefore shifts from **case-first expansion** to **profile-first capability expansion**.

## 3. Architectural classification

This is an architectural follow-up, not a small patch. It changes how coverage work is selected and verified across Action, Scene, support-domain evidence, and family proof. It must still preserve all current public contracts.

## 4. Approaches considered

### Approach A — Continue case-by-case regex expansion

Add new exact or near-exact grammar patterns for each observed fallback case.

**Advantages**
- smallest local code changes
- easy to make fail-closed
- straightforward adversarial tests

**Rejected because**
- poor coverage gain per change
- encourages accidental whole-clause allowlists
- grows lexical special cases faster than reusable structural capability
- does not answer which blocker cluster is worth fixing next

### Approach B — Add a general English parser or NLP dependency

Use a parser/POS tagger/dependency parser to infer clause ownership and grammar.

**Advantages**
- broad theoretical coverage
- less hand-authored lexical grammar

**Rejected because**
- violates the no-new-NLP/LLM dependency direction
- weakens deterministic/source-bound guarantees
- introduces a second semantic/linguistic authority that can disagree with producer state
- creates much larger validation and deployment surface for a ComfyUI custom node

### Approach C — Profile-first producer-bound capability expansion

Reuse the existing R43 reachability audit and `RealizationEvidence`/`FamilyProof` architecture. Add **diagnostic-only structural coverage signatures** that describe why groups of real workflow inputs remain blocked without storing whole prompt text as a cluster key. Select the highest-yield repairable clusters, then implement small bounded coverage packets using producer roles, exact source binding, ownership, attachment, and closed grammar.

**Selected.**

This approach preserves the current safety model and changes only how development effort is prioritized.

## 5. Non-goals

R44 must not:

- activate Realizer v2 as the stable default
- merge or promote to `main`
- implement Deterministic Diversity Scheduler D3
- change A1.6 thresholds
- add new character/location/action vocabulary to manufacture coverage
- add LLM, embedding, POS-tagger, dependency-parser, or other NLP runtime dependencies
- add camera/style/quality/artist/render language
- change public `Context*` node inputs/outputs
- change `context_json` schema/version
- replace Semantic EPIG
- use seed allowlists
- use complete prompt or complete action strings as authorization keys
- make UNKNOWN evidence implicitly safe
- count forced family execution as ordinary family observation
- treat a source hash or serialized proof as sufficient authorization without reconstructing current evidence

## 6. Core invariants

### 6.1 Compatibility-first

Stable V150 semantics and public workflow behavior have priority over R44 coverage. If a proposed packet cannot prove preservation, the packet is rejected rather than repaired by relaxing a guard.

### 6.2 Fail-closed tri-state semantics

`Truth.UNKNOWN` remains distinct from `FALSE`. Family requirements need explicit `TRUE`; family forbids need explicit `FALSE`. R44 must not convert unknown facts to false merely to increase eligibility.

### 6.3 Exact producer/source binding

A grammar rule may authorize a transformation only when it is bound to the current producer/source role and the current received value. Catalog membership alone is not grammar proof.

### 6.4 No whole-clause/seed permission

A new runtime branch must not be keyed by:

- `run_seed`
- fixture ID
- complete `legacy_text`
- complete prompt string
- a hash of a complete phrase used as an allowlist

Exact text equality remains valid for **binding/replay verification**, but not as the sole reason a new grammar construction is declared safe.

### 6.5 Productive grammar requirement

Each new grammar capability needs:

1. at least one real-workflow positive case,
2. at least one productive recombination using already source-bound parts from different positive examples or synthetic part-level fixtures,
3. adversarial near-miss tests for ownership/source/attachment/order/tail changes,
4. exact fallback preservation for unsupported variants.

### 6.6 Development vs formal evaluation

R44 uses development cohorts only. Heavy formal evaluation starts only after the development guide is met and a new source/config freeze is explicitly prepared.

## 7. Target architecture

```text
Existing workflow / Builder replay
            |
            v
Existing audit_sink snapshot
            |
            +------------------------------+
            |                              |
            v                              v
RealizationEvidence / FamilyProof     R44 diagnostic-only
(existing authority)                  CoverageSignature
            |                              |
            |                              v
            |                       cluster aggregation
            |                              |
            |                              v
            |                       CoveragePacket plan
            |                              |
            +--------------+---------------+
                           |
                           v
             bounded producer-bound grammar/evidence change
                           |
                           v
                  ordinary 512 replay
                           |
               +-----------+-----------+
               |                       |
          preserved                  expanded
          fallback/v2                 proven v2
```

The new diagnostic layer must never be consulted by runtime family authorization. It decides **what developers work on next**, not **what runtime accepts**.

## 8. New diagnostic concept: CoverageSignature

R43 reachability already records blocker IDs, blocker combinations, domain support, family eligibility, and ordinary execution. R44 adds a coarse structural signature so cases can be grouped by reusable capability rather than by exact text.

`realizer-coverage-signature/v1` contains only structural categories such as:

- route: `common_evidence`, `legacy_direct`, `simple_legacy_compatible`, `fallback`
- blocked domains
- Action producer constructor ID
- Action source field/slot sequence
- Action atom forms and attachments
- coarse owner categories (`protagonist`, `protagonist_body_part`, `primary_object_part`, `scene_event`, `unknown`)
- Scene producer constructor ID
- Scene source-field sequence and catalog-source categories
- Template constructor/topology ID
- Clothing/support constructor IDs when available
- per-family blocker ID sets rebuilt from current `RealizationEvidence`/`prove_all_families` when valid common inputs exist, even when ordinary dispatch fell back
- currently eligible family keys from that diagnostic re-proof

It must not include complete rendered prompt text or complete action/scene text in the grouping key.

The signature is diagnostic and canonically serialized/hashable. When `common_inputs` are present, the profiler reconstructs `RealizationEvidence` and calls the existing `prove_all_families` authority in read-only mode; it does not trust stored proof receipts and does not change ordinary selection.

## 9. Coverage packet selection

A **CoveragePacket** is the smallest R44 runtime change worth a separate reviewer gate.

A packet is eligible for selection only when:

- cases are ordinary fallback cases in the current 512 cohort,
- blockers are repairable grammar/source/ownership/topology unknowns,
- there is no `policy.conflict`, stale/current-input mismatch, replay mismatch, or proof/constructor mismatch,
- the packet is not selected merely because specific seeds share a phrase,
- the packet has at least 4 distinct ordinary seeds,
- the proposed capability can be expressed using existing producer roles/source categories or a narrowly justified internal producer trace.

Packets are ranked by:

1. distinct ordinary seeds potentially affected,
2. number of currently unobserved required families the packet can potentially enable,
3. fewer blocked domains,
4. fewer new runtime modules needed,
5. stable deterministic tie-breaking by coverage signature hash.

At most **three** runtime coverage packets are implemented in R44. If three bounded packets do not reach `64/512` and `5` ordinary families, R44 ends **BLOCKED** with a fresh handoff rather than broadening scope indefinitely.

## 10. Packet implementation rules

For each packet:

1. Freeze packet signature IDs and example seeds in a tracked packet manifest before runtime edits.
2. Add failing tests from real-workflow cases.
3. Add productive recombination tests.
4. Add adversarial near-miss tests.
5. Implement the smallest producer-bound grammar/evidence capability.
6. Run focused tests.
7. Run regression tests relevant to the touched domains.
8. Run a fresh 512 ordinary reachability audit against the preserved pre-packet baseline.
9. Confirm all prior v2 successes are preserved and only newly proved cases change.
10. Commit the packet independently.

A packet is rejected if it requires a seed allowlist, whole-clause authorization list, threshold relaxation, or speculative ownership inference.

## 11. Producer trace policy

R44 prefers existing exact history/source reconstruction. It may add a new ephemeral internal producer trace only when a failing test proves that the currently required ownership/source fact is **not reconstructable** from existing received context/history.

Any new trace must:

- be internal only,
- not change public `context_json`,
- contain source/selection structure rather than derived permission booleans,
- be reproducible from the same source/config/seed/context,
- be validated against current output,
- not grant family permission by itself.

## 12. Family proof policy

`FamilyProof` remains the only common-route family authorization object. R44 may improve the evidence/facts feeding it, but must not add a second permission authority.

Direct-route code remains for compatibility during R44. R44 may add **shadow diagnostics** that determine whether common proof can reproduce direct successes, but direct-route retirement is out of scope unless it becomes a zero-behavior-change deletion proven across the full 512 development cohort. The implementation plan does not require retirement.

## 13. Quantitative acceptance

### R44 development success

All must be true:

- ordinary v2 `>=64/512`
- ordinarily executed required families `>=5`
- all six required families retain forced real-input proof
- all pre-R44 ordinary v2 successes remain successful with exact prompt/context semantics required by the existing preservation harness
- no previously safe input becomes a policy/identity/replay error
- remaining fallback inputs preserve their pre-R44 raw/cleaned output and upstream semantic selection
- no public I/O/schema change
- no V150 protected-data expansion
- deterministic root/package/clean-copy replay remains canonical-byte stable
- focused/regression/validators/full-flow pass with zero unexplained skips/xfail/errors

### R44 bounded failure

R44 ends `BLOCKED`, not `REJECTED`, when:

- architecture and tests remain sound,
- fewer than 64 ordinary cases or fewer than 5 ordinary families are reached after three accepted packets,
- no formal adoption threshold has been measured.

A packet may be individually `REJECTED` when its measured behavior violates a packet acceptance condition.

## 14. Formal evaluation boundary

When the R44 development guide is met:

1. freeze and tag a recoverable R44 development source,
2. capture source/config/workflow identities,
3. prepare a formal-evaluation handoff,
4. leave candidate 8192 reference, 2048 gate, paired formal comparison, fixed80, blind review, fresh confirmations, frontend/browser, release8192 as `NOT_RUN` unless a subsequent explicitly authorized task runs them.

R44 itself does not infer formal acceptance from the 512 development cohort.

## 15. Documentation outputs

R44 execution should leave:

- `docs/diversity_refactor/r44_progress.md`
- `docs/diversity_refactor/r44_handoff.md`
- `docs/diversity_refactor/r44_handoff_summary.json`
- packet manifests and compact receipts under `docs/diversity_refactor/` or the existing results policy
- recoverable source/tag identity for every accepted comparison checkpoint

The existing `CURRENT_STATUS.md`, `tasks.md`, and `progress.md` are updated only with measured facts.

## 16. Design decision summary

R44 does **not** attempt to make the Realizer permissive. It makes development selection more intelligent and expands only reusable source-bound capabilities. The target is to turn the current system from “prove one unusual sentence at a time” into “identify and prove a recurring producer structure once,” while preserving the compiler-like evidence/proof model already established in R43.
