# -*- coding: utf-8 -*-
"""
test_bootstrap.py

テストスクリプト用ブートストラップモジュール。
各テストファイルの先頭で ``import test_bootstrap`` するだけで、
ComfyUI パッケージコンテキスト外でもモジュールのインポートが解決されます。

仕組み:
  1. 親ディレクトリ（promptbuilder2 の親）を sys.path に追加
  2. パッケージ名（ディレクトリ名）を自動検出
  3. 各モジュールをパッケージ経由でインポートし、
     フラットなモジュール名で sys.modules に登録
"""

import os
import sys
import types
import importlib

# ── パス設定 ──
_this_dir = os.path.dirname(os.path.abspath(__file__))
_repo_dir = os.path.dirname(_this_dir)
_parent_dir = os.path.dirname(_repo_dir)
_pkg_name = os.path.basename(_repo_dir)

if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# ── フラットなモジュール名 → パッケージ内パス のマッピング ──
_MODULE_MAP = {
    # ファサードモジュール
    "background_vocab":             f"{_pkg_name}.background_vocab",
    "clothing_vocab":               f"{_pkg_name}.clothing_vocab",
    "improved_pose_emotion_vocab":  f"{_pkg_name}.improved_pose_emotion_vocab",

    # ノードモジュール
    "nodes_prompt_cleaner":         f"{_pkg_name}.nodes_prompt_cleaner",
}

_loaded = 0
_failed = []

for flat_name, pkg_path in _MODULE_MAP.items():
    if flat_name in sys.modules:
        _loaded += 1
        continue
    try:
        mod = importlib.import_module(pkg_path)
        sys.modules[flat_name] = mod
        _loaded += 1
    except ImportError as e:
        _failed.append((flat_name, str(e)))

if _failed:
    print(f"[test_bootstrap] Warning: {len(_failed)} module(s) failed to load:")
    for name, err in _failed:
        print(f"  - {name}: {err}")

# テスト側で明示的に参照しなくても、import test_bootstrap の副作用で
# sys.modules に全モジュールが登録される。
