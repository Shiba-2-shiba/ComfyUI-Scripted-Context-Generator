# Session Notes

このファイルには **現セッション以降も参照しやすい形に圧縮した作業メモ** を記録します。
詳細な履歴は `docs/context_refactor/archive/context_v2_progress.md` と archive 文書を優先し、
ここでは今の repo を扱う上で必要な要点だけを残します。

---

## [2026-03-18] Context-only 体制への圧縮後メモ

### 現在の repo 状態

- 公開ノード面は `nodes_context.py` と `nodes_prompt_cleaner.py` のみ
- `NODE_SURFACE_GROUPS` は `primary = nodes_context`, `utility = nodes_prompt_cleaner`
- compat / transition / bridge ノードは退役済み
- active workflow sample は `ComfyUI-workflow-context.json` だけ
- frontend / browser 検証資産の source-of-truth は `verification/` にあり、
  実行前に `tools/sync_upstream_verification_assets.ps1` で
  `ComfyUI_frontend` へ同期する

### 標準検証の考え方

- 最小 baseline:
  - `python -m unittest assets.test_node_registry assets.test_workflow_samples`
  - `python tools/check_widgets_values.py`
- 実装変更時の追加:
  - `python tools/verify_full_flow.py`
  - `pwsh -File tools/run_frontend_workflow_validation.ps1`
  - `pwsh -File tools/run_custom_workflow_roundtrip.ps1`

### historical 扱いに変わったもの

- `assets/runner.py` は archive 済みで標準入口ではない
- 旧 compat / bridge / legacy workflow fixture は `tools/archive/` に退避済み
- cutover plan / readiness report / cutover-specific test は archive 済み
- 旧 planning/spec 文書は `assets/archive/` と
  `docs/context_refactor/archive/` に退避済み

### 今後の前提

- 新機能追加は `Context*` 系と `pipeline/` を前提に行う
- upstream `ComfyUI` / `ComfyUI_frontend` は差し替え前提で扱う
- agent 側の記録も、旧 node 名ではなく context-first 用語を基準に保つ
