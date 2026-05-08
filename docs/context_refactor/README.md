# Context Refactor Summary

このディレクトリは、完了済みの context-first リファクタリングと、その後の
prompt-surface repetition 調整の要約入口です。

現在の扱いは次の2層です。

- 現在の方針と将来の拡張時に参照する文書
- 完了済みリファクタリングの履歴・計画・進捗ログ

## Current Status

リファクタリングは完了済みです。現在の repo は次の状態を前提にします。

- public surface は `Context*` ノード群と `PromptCleaner` のみ
- transport は `context_json`
- bridge / compat / legacy node family は退役済み
- shared generation logic は `pipeline/` に集約
- active workflow sample は `ComfyUI-workflow-context.json`
- 検証 baseline は `assets/`, `tools/`, `verification/` の context-only 構成

追加で、prompt surface の反復抑制リファクタも完了済みです。

- `mood_map` staging は固定全量付与ではなく deterministic subset に変更済み
- semantic-family ベースの repetition control を導入済み
- prompt repetition / template diversity の監査資産を追加済み

## Active Docs

現在の実装に対して通常参照するのは次です。

- [Current Status](../../CURRENT_STATUS.md)
- [Expansion Guide](../../EXPANSION_GUIDE.md)
- [Variation Expansion Workstream](../variation_expansion/README.md)
- [Context Refactor Summary](./README.md)
- [Context Schema Extension Guidance](./context_extension_guidance.md)

## Archived History

完了済みの planning / progress / migration / Codex 作業メモは
[archive/README.md](./archive/README.md) に集約しています。

履歴として残している主な内容:

- context-first への設計仕様
- phase/task ベースの進捗ログ
- migration / bridge / cutover の記録
- repetition refactor の spec / task board / operating notes

## Maintenance Policy

今後の変更では、完了済み migration task を live plan として再利用しません。

- 現在の仕様確認は repo root の `CURRENT_STATUS.md`, `README.md`, `REPO_STRUCTURE.md`, `assets/ARCHITECTURE.md` を優先
- context 拡張時の判断は `context_extension_guidance.md` を優先
- 過去の判断経緯や cutover 履歴が必要なときだけ archive を参照
