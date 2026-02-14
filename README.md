# ComfyUI-Scripted-Context-Generator
Generate rich, natural language character contexts using pure rule-based logic. No LLMs required.

 [日本語] LLM非依存。ルールベースのロジックで、文脈（コンテキスト）と物語性のあるキャラクター設定を生成する軽量 ComfyUI ノードです。

## 📖 Overview / 概要
Scripted Context Generator is a custom node for ComfyUI designed to generate detailed character descriptions and prompt contexts without relying on heavy Large Language Models (LLMs). Instead of simply listing tags (e.g., 1girl, solo, red hair), this node constructs natural language sentences (e.g., "A solo girl with a high ponytail, red hair, and green eyes") based on predefined character profiles and logic.

Scripted Context Generator は、LLM（大規模言語モデル）に依存せず、詳細なキャラクター描写やプロンプトの「文脈」を生成するために設計された ComfyUI 用カスタムノードです。 単なるタグの羅列（例: 1girl, solo, red hair）ではなく、定義済みのプロファイルとロジックに基づいて、自然な英文形式（例: "A solo girl with a high ponytail, red hair, and green eyes"）を構築します。

## ✨ Key Features / 特徴
### 1. Pure Rule-Based Logic (完全ルールベース)
No LLM Dependency: Does not require any external API keys or heavy local models. It runs purely on Python script logic.
Fast & Lightweight: Generation is instantaneous and consumes negligible resources.

LLM非依存: 外部APIキーや重いローカルモデルを必要としません。純粋な Python スクリプトのロジックで動作します。
高速・軽量: 生成は一瞬で行われ、リソース消費も無視できるほど軽量です。

### 2. Natural Language Context (自然言語コンテキスト)
Sentence Construction: Generates grammatically coherent sentences suitable for modern prompt engineering (e.g., SDXL, Flux).
Narrative Depth: Beyond visual traits, it incorporates personality and atmosphere into the description context.

文章構築: 最新のプロンプトエンジニアリング（SDXL, Fluxなど）に適した、文法的に一貫性のある文章を生成します。
物語的な深み: 単なる外見的特徴だけでなく、性格や雰囲気といった要素もコンテキストに組み込みます。

### 3. Consistent Personality (一貫した人格)
Defined Profiles: Uses a database of character archetypes to ensure consistency in hair, eyes, and personality traits across generations.
Context-Aware: The generated text changes dynamically based on the selected profile while maintaining the core identity.

定義済みプロファイル: キャラクターのアーキタイプ（原型）データベースを使用し、髪型・目の色・性格特性の一貫性を保ちます。
文脈意識: 選択されたプロファイルに基づき、コアとなるアイデンティティを保ちながら、動的にテキストを変化させます。

### 🛠 Usage / 使い方
Add the Scripted Context Generator node to your workflow.
Connect it to your prompt builder or text concatenation nodes.
Select a mode (random or fixed) and enjoy context-rich prompts instantly.

ワークフローにノードを追加し、プロンプト生成フローの一部として接続するだけで機能します。
