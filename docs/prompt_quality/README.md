# Prompt Quality Release Baseline

Last verified: 2026-08-31

This file is the canonical documentation entry for the currently accepted
prompt-quality baseline. The final durable authority is the completed G010
strict aggregate receipt in `.omx/ultragoal/goals.json` and its append-only
audit record in `.omx/ultragoal/ledger.jsonl`.

## Accepted Release

```text
release: G010 strict aggregate receipt
protected source tree: 40848f5c9b37ffbcc7dec0e89f60d52e59a23ec5877536b24134a19b43fc3447
verification SHA-256: 05bf5c9c7d95c11e282b401805434e23e27b38805e3b7497735045c88fd838d3
promotion SHA-256: d37b3f58df45987b6cb0165ab5d77eabee662069b9f83473e54a87690bbd552d
blind review: final-blind-review-attempt-015, pass
Python regression: 540/540
verification inventory: 11/11 gates
independent review: code-reviewer APPROVE / architect CLEAR
```

Confirmation evidence used three independent 256-seed domain runs:

- G004 semantic consistency confirmation
- G005 natural-language confirmation
- G006 diversity confirmation

This completed receipt supersedes the earlier in-progress status recorded at
the top of `HANDOFF.md`. `final-review-summary.json` is a historical pre-final
review summary and is not the G010 release receipt.

## Downstream Preservation Contract

Any variation, Semantic EPIG, vocabulary, or rendering change that can affect
prompts must:

1. Bind its baseline to the accepted release receipt and current candidate
   source/data hashes.
2. Reuse the workflow-faithful runner, analyzer, policy, comparison, and review
   contracts without weakening thresholds.
3. Use the deterministic 64-control + 16-exploration cohort for iteration work.
4. Pass three independent 256-seed confirmations for semantic consistency,
   naturalness, and diversity before promotion.
5. Pass a comparison-bound blind review and the full applicable verification
   inventory.
6. Record an evidence-bound `PROMOTED`, `REJECTED`, or `ABORTED` verdict.

If the prompt-quality contract is superseded, the newer completed receipt must
name its predecessor, hashes, changed thresholds, and independent approval. An
in-progress experiment or local generated artifact cannot replace this baseline.

## Supporting Documents

- `final-review-contract.json`: final review contract bound by the G010 receipt
- `final-review-summary.json`: historical pre-final summary
- `HANDOFF.md`: historical in-progress handoff, retained for audit context
- `ledger.jsonl`: tracked prompt-quality experiment decisions
- `experiments/`: append-only experiment state and durable evidence
