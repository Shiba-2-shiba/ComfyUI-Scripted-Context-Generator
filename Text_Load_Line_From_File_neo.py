import os
import random
import hashlib
import json

# --------------------------------------------------------------------------------
# 簡易ヒストリー管理クラス
# WAS Suiteのデータベースの代わりに、同じフォルダにJSONファイルを作ってカウンターを保存します
# --------------------------------------------------------------------------------
class SimpleHistoryManager:
    def __init__(self):
        self.history_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "text_loader_history.json")
        self.data = self._load_data()

    def _load_data(self):
        if not os.path.exists(self.history_file):
            return {}
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_data(self):
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"[TextLoaderNeo] Error saving history: {e}")

    def get_count(self, label):
        return self.data.get(label, 0)

    def set_count(self, label, count):
        self.data[label] = count
        self._save_data()

# インスタンス化
history_manager = SimpleHistoryManager()

# --------------------------------------------------------------------------------
# メインノードクラス
# --------------------------------------------------------------------------------
class Text_Load_Line_From_File_neo:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": '', "multiline": False}),
                "dictionary_name": ("STRING", {"default": '[filename]', "multiline": False}),
                "label": ("STRING", {"default": 'TextBatch', "multiline": False}),
                "mode": (["automatic", "index", "random"],),
                "index": ("INT", {"default": 0, "min": 0, "step": 1}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "optional": {
                "multiline_text": ("STRING", {"forceInput": True, "multiline": True}),
            }
        }

    # ComfyUIに再実行が必要かどうかを伝えるメソッド
    @classmethod
    def IS_CHANGED(cls, mode, file_path, multiline_text=None, index=0, seed=0, **kwargs):
        # random または automatic の場合は、常に再実行させるために NaN を返す
        if mode in ["random", "automatic"]:
            return float("NaN")
        
        # index モードの場合は、ファイルの内容またはインデックスが変わった時のみ更新
        m = hashlib.sha256()
        
        # テキスト入力がある場合はそのハッシュ
        if multiline_text:
            m.update(multiline_text.encode('utf-8'))
        # ファイルパスがある場合はファイルのハッシュ
        elif file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                m.update(f.read())
        
        # index もハッシュに含める
        m.update(str(index).encode('utf-8'))
        
        return m.digest().hex()

    RETURN_TYPES = ("STRING", "DICT")
    RETURN_NAMES = ("line_text", "dictionary")
    FUNCTION = "load_file"

    CATEGORY = "Text/Loader"

    def load_file(self, file_path='', dictionary_name='[filename]', label='TextBatch',
                  mode='automatic', index=0, seed=0, multiline_text=None):
        
        lines = []

        # 1. データの読み込み (multiline_text 優先)
        if multiline_text is not None and multiline_text.strip() != "":
            # 文字列から読み込み（空行除去）
            lines = [line.strip() for line in multiline_text.strip().split('\n') if line.strip()]
        elif file_path and os.path.exists(file_path):
            # ファイルから読み込み
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # 空行を除去してリスト化
                    lines = [line.strip() for line in f if line.strip()]
            except Exception as e:
                print(f"[TextLoaderNeo] Error reading file: {e}")
                return ('', {dictionary_name: []})
        else:
            print(f"[TextLoaderNeo] File not found or empty path: {file_path}")
            return ('', {dictionary_name: []})

        if not lines:
            print("[TextLoaderNeo] No valid lines found.")
            return ('', {dictionary_name: []})

        # 辞書名の設定
        if dictionary_name == '[filename]':
            dictionary_name = os.path.basename(file_path) if file_path else "text_data"

        # 2. モード別の処理
        selected_line = ""

        if mode == 'random':
            # ランダム選択 (シード固定可能)
            random.seed(seed)
            selected_line = random.choice(lines)

        elif mode == 'index':
            # 指定インデックス
            safe_index = index % len(lines)
            selected_line = lines[safe_index]

        elif mode == 'automatic':
            # 順番に呼び出し (ヒストリー管理を使用)
            current_count = history_manager.get_count(label)
            
            # リストの範囲を超えたらループ
            safe_index = current_count % len(lines)
            selected_line = lines[safe_index]
            
            # 次回のためにカウントアップして保存
            history_manager.set_count(label, current_count + 1)
            print(f"[TextLoaderNeo] Label: '{label}' | Index: {safe_index} / {len(lines)}")

        return (selected_line, {dictionary_name: lines})

# ノードのマッピング
NODE_CLASS_MAPPINGS = {
    "Text_Load_Line_From_File_neo": Text_Load_Line_From_File_neo
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Text_Load_Line_From_File_neo": "Text Load Line From File (Neo)"
}