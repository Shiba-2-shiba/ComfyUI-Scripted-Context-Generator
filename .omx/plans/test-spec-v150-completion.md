# V150 completion evidence

- Before edits: prior 802-test result plus focused reproduction tests for each new defect.
- Candidate: deterministic compatibility CSV matches generated rows with zero missing/extra pairs;
  action pool generation and prompt data checks have zero errors/warnings; full flow/widgets pass.
- Run complete Python regression in frozen candidate root; no skipped tests or active-root test/import leakage.
- Real frontend Vitest and browser roundtrip through the provided checkout, installed dependencies, isolated
  candidate backend; bind runtime revision/config and source sentinel. Screenshots/logs support UI diagnosis.
- Fresh automatic control64/exploration16 results, 20 semantic pairs with no identity/seed/record mismatch;
  two independent blind v7 lanes with actual judgments; user-approved consistency guard, all other thresholds unchanged.
- Three 256-seed confirmation objectives pass with source/content/cohort bindings and no overlapping iteration seeds.
- Eleven evidence/v2 files bind commands, logs/results, successful summaries, exact source/content hashes and roots.
- Promotion uses only passing bound artifacts and the closed allowlist, restores on failure, and reruns read-only
  active data/quality/runtime checks before writing final successful promotion evidence.
- Final source/code review, scoped deslop and meaningful regression recheck if it changes code.
