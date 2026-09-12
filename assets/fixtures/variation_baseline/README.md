# Variation arithmetic baseline

These are real pre-V150 data inputs frozen on 2026-09-05: 120 subjects,
90 locations, 5,806 compatibility rows, and 103,212 base variations.

`assets/variation_test_fixtures.py` overlays these data and action-authoring inputs onto a disposable
copy of current code for the historical planner, analyzer, contribution, snapshot,
quality-contract, and coverage regression tests. Candidate-only action source
files are removed from that copy according to this baseline's source manifest.
Validators and generators still execute normally and regenerate bound reports.

These fixtures are test inputs, never production evidence. Live integrity tests
continue reading the actual repository or candidate data. Do not update this
baseline merely because the active variation scope grows.
