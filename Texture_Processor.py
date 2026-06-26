import os
import sys
import subprocess
import threading
import json
import re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog, Menu
from PIL import Image
import numpy as np

# -------------------- 配置 --------------------
if getattr(sys, 'frozen', False):
    TEXCONV = os.path.join(sys._MEIPASS, 'texconv.exe')
else:
    TEXCONV = "texconv.exe"
PRESET_FILE = "packing_presets.json"
LANG_FILE = "lang.json"
RULES_FILE = "match_rules.json"

RES_MAP = {
    "8K": 8192, "4K": 4096, "2K": 2048,
    "1K": 1024, "512": 512, "256": 256,
}

TEXTURE_TYPES = [
    "None", "AO", "Cavity", "Displacement", "Emissive", "Fuzz",
    "Gloss", "Height", "Metal", "Opacity", "Reflection",
    "Roughness", "Scattering", "Specular"
]

DEFAULT_RULES = {
    "AO": ["ao"],
    "BaseColor": ["basecolor", "base_color", "diffuse"],
    "Normal": ["normal", "norm"],
    "Roughness": ["roughness", "rough"],
    "Displacement": ["displacement", "disp"],
    "Cavity": ["cavity"],
    "Emissive": ["emissive"],
    "Fuzz": ["fuzz"],
    "Gloss": ["gloss"],
    "Height": ["height"],
    "Metal": ["metal", "metallic"],
    "Opacity": ["opacity"],
    "Reflection": ["reflection"],
    "Scattering": ["scattering"],
    "Specular": ["specular"],
}

DEFAULT_PRESETS = {
    "ORDp": {"R": "AO", "G": "Roughness", "B": "Displacement", "A": "None", "suffix": "ORDp"},
    "ORM":  {"R": "AO", "G": "Roughness", "B": "Metal", "A": "None", "suffix": "ORM"}
}

STRINGS = {
    "zh": {
        "title": "PBR 贴图批量处理 & 通道打包工具",
        "source_group": "源文件夹 & 输出选项",
        "source_label": "资产根目录:",
        "browse": "浏览",
        "overwrite": "覆盖已存在的 DDS 文件",
        "premul_alpha": "半透明材质 (预乘Alpha)",
        "gen_mipmap": "生成 Mipmap",
        "res_group": "输出分辨率",
        "res_basecolor": "基础颜色/漫反射贴图:",
        "res_normal": "法线贴图:",
        "res_packed": "通道贴图:",
        "packing_group": "通道组合配置",
        "preset_label": "当前预设:",
        "save_preset": "保存当前为预设",
        "del_preset": "删除选中预设",
        "r_ch": "R 通道:",
        "g_ch": "G 通道:",
        "b_ch": "B 通道:",
        "a_ch": "A 通道:",
        "suffix_label": "输出后缀:",
        "start_btn": "▶  开始批量处理",
        "lang_menu": "语言",
        "adv_menu": "高级",
        "rules_menu": "编辑匹配规则",
        "help_menu": "帮助",
        "about_menu": "关于",
        "about_text": "作者: William_Wang (Confused_Bear)\n使用 DeepSeek Vibe Coding 制作",
        "dir_error": "错误",
        "dir_error_msg": "请先选择有效的资产根目录",
        "texconv_missing": "texconv.exe 未找到，请将其放在程序同目录下。",
        "preset_save_title": "保存预设",
        "preset_save_prompt": "请输入预设名称（不可与内置同名）:",
        "preset_overwrite": "不能覆盖内置预设，请使用其他名称。",
        "preset_delete_confirm": "确定要删除预设 '{name}' 吗？",
        "preset_deleted": "预设 '{name}' 已删除。",
        "preset_saved": "预设 '{name}' 已保存。",
        "no_folder": "未找到子文件夹，请检查目录结构。",
        "found_folders": "找到 {} 个资产文件夹，开始处理...\n",
        "done": "全部完成！",
        "rule_editor_title": "编辑匹配规则",
        "rule_save": "保存规则",
        "rule_cancel": "取消",
        "rule_tip": "每行一个关键词，小写英文",
        "lang_restart_title": "语言更改",
        "lang_restart_msg": "语言已更改，需要重启程序才能完全生效。\n是否立即重启？",
        "lang_restart_korean_msg": "语言已更改为韩语。\n请关闭本窗口后，重新运行程序即可生效。",
        "log_skip_exist": "  ⏩ 跳过已存在: {name}",
        "log_basecolor_ok": "  ✓ 基础颜色 -> {name}.dds",
        "log_normal_ok": "  ✓ 法线贴图 -> {name}.dds",
        "log_normal_missing": "  ⚠ 没有法线贴图",
        "log_packed_ok": "  ✓ 通道贴图 -> {name}.dds",
        "log_packed_missing": "  ⚠ 合成通道所需贴图全部缺失，跳过",
        "log_basecolor_missing": "  ⚠ 缺少基础颜色贴图，跳过",
        "log_folder_header": "📁 {name}",
        "pause": "暂停",
        "resume": "继续",
        "cancel": "取消",
        "cancel_confirm": "确定要取消当前任务吗？",
        "delete_files_confirm": "是否删除本次处理已生成的所有 DDS 文件？",
        "paused_msg": "⏸️ 已暂停",
        "resumed_msg": "▶️ 继续处理",
        "cancelled_msg": "❌ 处理已取消",
        "task_running": "任务正在进行中...",
    },
    "en": {
        "title": "PBR Texture Batch Processor & Channel Packer",
        "source_group": "Source Folder & Output Options",
        "source_label": "Asset Root:",
        "browse": "Browse",
        "overwrite": "Overwrite existing DDS",
        "premul_alpha": "Translucent (Premultiplied Alpha)",
        "gen_mipmap": "Generate Mipmaps",
        "res_group": "Output Resolution",
        "res_basecolor": "BaseColor:",
        "res_normal": "Normal:",
        "res_packed": "Packed Map:",
        "packing_group": "Channel Packing Config",
        "preset_label": "Preset:",
        "save_preset": "Save as Preset",
        "del_preset": "Delete Preset",
        "r_ch": "R Channel:",
        "g_ch": "G Channel:",
        "b_ch": "B Channel:",
        "a_ch": "A Channel:",
        "suffix_label": "Suffix:",
        "start_btn": "▶  Start Processing",
        "lang_menu": "Language",
        "adv_menu": "Advanced",
        "rules_menu": "Edit Matching Rules",
        "help_menu": "Help",
        "about_menu": "About",
        "about_text": "Author: William_Wang (Confused_Bear)\nMade with DeepSeek Vibe Coding",
        "dir_error": "Error",
        "dir_error_msg": "Please select a valid asset root directory",
        "texconv_missing": "texconv.exe not found. Place it in the same folder as the program.",
        "preset_save_title": "Save Preset",
        "preset_save_prompt": "Enter preset name (cannot be same as built-in):",
        "preset_overwrite": "Cannot overwrite built-in presets.",
        "preset_delete_confirm": "Are you sure you want to delete '{name}'?",
        "preset_deleted": "Preset '{name}' deleted.",
        "preset_saved": "Preset '{name}' saved.",
        "no_folder": "No subfolders found. Check directory structure.",
        "found_folders": "Found {} asset folders, starting...\n",
        "done": "All done!",
        "rule_editor_title": "Edit Matching Rules",
        "rule_save": "Save Rules",
        "rule_cancel": "Cancel",
        "rule_tip": "One keyword per line, lowercase English",
        "lang_restart_title": "Language Changed",
        "lang_restart_msg": "Language has been changed. Restart the program to apply.\nRestart now?",
        "lang_restart_korean_msg": "Language changed to Korean.\nPlease close this window and reopen the program to apply.",
        "log_skip_exist": "  ⏩ Skipped: {name} already exists",
        "log_basecolor_ok": "  ✓ BaseColor -> {name}.dds",
        "log_normal_ok": "  ✓ Normal -> {name}.dds",
        "log_normal_missing": "  ⚠ Normal map not found",
        "log_packed_ok": "  ✓ Packed map -> {name}.dds",
        "log_packed_missing": "  ⚠ No source maps for packing, skipped",
        "log_basecolor_missing": "  ⚠ BaseColor missing, skipped",
        "log_folder_header": "📁 {name}",
        "pause": "Pause",
        "resume": "Resume",
        "cancel": "Cancel",
        "cancel_confirm": "Are you sure you want to cancel the current task?",
        "delete_files_confirm": "Delete all generated DDS files from this session?",
        "paused_msg": "⏸️ Paused",
        "resumed_msg": "▶️ Resumed",
        "cancelled_msg": "❌ Processing cancelled",
        "task_running": "Task is already running...",
    },
    "ja": {
        "title": "PBRテクスチャバッチ処理＆チャンネルパッカー",
        "source_group": "ソースフォルダ & 出力オプション",
        "source_label": "アセットルート:",
        "browse": "参照",
        "overwrite": "既存のDDSを上書き",
        "premul_alpha": "半透明 (乗算済みアルファ)",
        "gen_mipmap": "ミップマップ生成",
        "res_group": "出力解像度",
        "res_basecolor": "ベースカラー:",
        "res_normal": "ノーマル:",
        "res_packed": "パックマップ:",
        "packing_group": "チャンネルパック設定",
        "preset_label": "プリセット:",
        "save_preset": "プリセット保存",
        "del_preset": "プリセット削除",
        "r_ch": "Rチャンネル:",
        "g_ch": "Gチャンネル:",
        "b_ch": "Bチャンネル:",
        "a_ch": "Aチャンネル:",
        "suffix_label": "サフィックス:",
        "start_btn": "▶  処理開始",
        "lang_menu": "言語",
        "adv_menu": "詳細設定",
        "rules_menu": "マッチングルール編集",
        "help_menu": "ヘルプ",
        "about_menu": "について",
        "about_text": "作者: William_Wang (Confused_Bear)\nDeepSeek Vibe Coding で作成",
        "dir_error": "エラー",
        "dir_error_msg": "有効なアセットルートディレクトリを選択してください",
        "texconv_missing": "texconv.exe が見つかりません。プログラムと同じフォルダに置いてください。",
        "preset_save_title": "プリセット保存",
        "preset_save_prompt": "プリセット名を入力（ビルトインと重複不可）:",
        "preset_overwrite": "ビルトインプリセットは上書きできません。",
        "preset_delete_confirm": "'{name}' を削除しますか？",
        "preset_deleted": "プリセット '{name}' を削除しました。",
        "preset_saved": "プリセット '{name}' を保存しました。",
        "no_folder": "サブフォルダが見つかりません。ディレクトリ構造を確認してください。",
        "found_folders": "{} 個のアセットフォルダを発見、処理開始...\n",
        "done": "完了！",
        "rule_editor_title": "マッチングルール編集",
        "rule_save": "ルール保存",
        "rule_cancel": "キャンセル",
        "rule_tip": "1行に1キーワード、小文字の英語",
        "lang_restart_title": "言語変更",
        "lang_restart_msg": "言語が変更されました。再起動しますか？\n今すぐ再起動しますか？",
        "lang_restart_korean_msg": "言語が韓国語に変更されました。\nこのウィンドウを閉じてプログラムを再起動してください。",
        "log_skip_exist": "  ⏩ スキップ: {name} は既に存在します",
        "log_basecolor_ok": "  ✓ ベースカラー -> {name}.dds",
        "log_normal_ok": "  ✓ ノーマル -> {name}.dds",
        "log_normal_missing": "  ⚠ ノーマルマップが見つかりません",
        "log_packed_ok": "  ✓ パックマップ -> {name}.dds",
        "log_packed_missing": "  ⚠ パック用のソースマップがありません、スキップ",
        "log_basecolor_missing": "  ⚠ ベースカラーが見つかりません、スキップ",
        "log_folder_header": "📁 {name}",
        "pause": "一時停止",
        "resume": "再開",
        "cancel": "キャンセル",
        "cancel_confirm": "現在のタスクをキャンセルしますか？",
        "delete_files_confirm": "このセッションで生成されたDDSファイルをすべて削除しますか？",
        "paused_msg": "⏸️ 一時停止中",
        "resumed_msg": "▶️ 再開しました",
        "cancelled_msg": "❌ 処理がキャンセルされました",
        "task_running": "タスクは既に実行中です...",
    },
    "ko": {
        "title": "PBR 텍스처 배치 처리 및 채널 패커",
        "source_group": "소스 폴더 & 출력 옵션",
        "source_label": "에셋 루트:",
        "browse": "찾아보기",
        "overwrite": "기존 DDS 덮어쓰기",
        "premul_alpha": "반투명 (프리멀티플라이드 알파)",
        "gen_mipmap": "밉맵 생성",
        "res_group": "출력 해상도",
        "res_basecolor": "베이스컬러:",
        "res_normal": "노멀:",
        "res_packed": "패킹 맵:",
        "packing_group": "채널 패킹 설정",
        "preset_label": "프리셋:",
        "save_preset": "프리셋 저장",
        "del_preset": "프리셋 삭제",
        "r_ch": "R 채널:",
        "g_ch": "G 채널:",
        "b_ch": "B 채널:",
        "a_ch": "A 채널:",
        "suffix_label": "접미사:",
        "start_btn": "▶  처리 시작",
        "lang_menu": "언어",
        "adv_menu": "고급",
        "rules_menu": "매칭 규칙 편집",
        "help_menu": "도움말",
        "about_menu": "정보",
        "about_text": "제작자: William_Wang (Confused_Bear)\nDeepSeek Vibe Coding으로 제작",
        "dir_error": "오류",
        "dir_error_msg": "유효한 에셋 루트 디렉토리를 선택하세요",
        "texconv_missing": "texconv.exe를 찾을 수 없습니다. 프로그램과 같은 폴더에 넣어주세요.",
        "preset_save_title": "프리셋 저장",
        "preset_save_prompt": "프리셋 이름 입력 (내장과 중복 불가):",
        "preset_overwrite": "내장 프리셋은 덮어쓸 수 없습니다.",
        "preset_delete_confirm": "'{name}'을(를) 삭제하시겠습니까?",
        "preset_deleted": "프리셋 '{name}' 삭제됨.",
        "preset_saved": "프리셋 '{name}' 저장됨.",
        "no_folder": "하위 폴더가 없습니다. 디렉토리 구조를 확인하세요.",
        "found_folders": "{}개의 에셋 폴더 발견, 처리 시작...\n",
        "done": "완료!",
        "rule_editor_title": "매칭 규칙 편집",
        "rule_save": "규칙 저장",
        "rule_cancel": "취소",
        "rule_tip": "한 줄에 하나의 키워드, 소문자 영어",
        "lang_restart_title": "언어 변경",
        "lang_restart_msg": "언어가 변경되었습니다. 프로그램을 다시 시작해야 적용됩니다.\n지금 다시 시작하시겠습니까?",
        "lang_restart_korean_msg": "언어가 한국어로 변경되었습니다.\n이 창을 닫고 프로그램을 다시 실행하세요.",
        "log_skip_exist": "  ⏩ 건너뜀: {name} 이미 존재함",
        "log_basecolor_ok": "  ✓ 베이스컬러 -> {name}.dds",
        "log_normal_ok": "  ✓ 노멀 -> {name}.dds",
        "log_normal_missing": "  ⚠ 노멀 맵을 찾을 수 없음",
        "log_packed_ok": "  ✓ 패킹 맵 -> {name}.dds",
        "log_packed_missing": "  ⚠ 패킹할 소스 맵이 없음, 건너뜀",
        "log_basecolor_missing": "  ⚠ 베이스컬러 누락, 건너뜀",
        "log_folder_header": "📁 {name}",
        "pause": "일시정지",
        "resume": "계속",
        "cancel": "취소",
        "cancel_confirm": "현재 작업을 취소하시겠습니까?",
        "delete_files_confirm": "이번 세션에서 생성된 모든 DDS 파일을 삭제하시겠습니까?",
        "paused_msg": "⏸️ 일시정지됨",
        "resumed_msg": "▶️ 계속합니다",
        "cancelled_msg": "❌ 처리 취소됨",
        "task_running": "작업이 이미 실행 중입니다...",
    }
}


class TextureProcessorApp:
    def __init__(self, root):
        self.root = root
        self.lang = tk.StringVar(value="zh")
        self._load_language()
        self.current_lang = self.lang.get()
        self.lang.trace_add('write', self._on_lang_change_full)

        self._load_match_rules()

        self.root.title(self.tr("title"))
        self.root.geometry("720x850")
        self.root.resizable(True, True)
        self.root.configure(bg='#f5f5f5')

        self.default_font = ("Microsoft YaHei UI", 9)
        self.bold_font = ("Microsoft YaHei UI", 10, "bold")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', font=self.default_font, background='#f5f5f5')
        style.configure('TLabel', background='#f5f5f5')
        style.configure('TButton', font=self.default_font)
        style.configure('TEntry', font=self.default_font)
        style.configure('TCheckbutton', background='#f5f5f5')
        style.configure('TCombobox', font=self.default_font)
        style.configure('TLabelframe.Label', font=self.bold_font)

        self.base_dir = tk.StringVar()
        self.overwrite = tk.BooleanVar(value=False)
        self.bc_res = tk.StringVar(value="4K")
        self.n_res = tk.StringVar(value="2K")
        self.pack_res = tk.StringVar(value="2K")
        self.premultiply_alpha = tk.BooleanVar(value=False)
        self.generate_mipmaps = tk.BooleanVar(value=False)

        self.preset_var = tk.StringVar(value="ORDp")
        self.custom_r = tk.StringVar(value="AO")
        self.custom_g = tk.StringVar(value="Roughness")
        self.custom_b = tk.StringVar(value="Displacement")
        self.custom_a = tk.StringVar(value="None")
        self.custom_suffix = tk.StringVar(value="ORDp")

        self.running = False
        self.paused = threading.Event()
        self.paused.set()
        self.cancelled = False
        self.generated_files = []
        self.file_lock = threading.Lock()

        self.presets = self._load_presets()

        if not self._check_texconv():
            messagebox.showerror(self.tr("dir_error"), self.tr("texconv_missing"))
            root.destroy()
            return

        self._build_menu()
        self._build_ui()
        self._on_preset_change()
        self._refresh_texts()

    # ---------------- 辅助方法 ----------------
    def tr(self, key):
        return STRINGS.get(self.lang.get(), STRINGS["en"]).get(key, key)

    def _load_language(self):
        if Path(LANG_FILE).exists():
            try:
                with open(LANG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.lang.set(data.get("lang", "zh"))
            except Exception:
                pass

    def _on_lang_change_full(self, *args):
        new_lang = self.lang.get()
        if new_lang == self.current_lang:
            return
        self._save_language()

        if new_lang == "ko":
            messagebox.showinfo(
                self.tr("lang_restart_title"),
                self.tr("lang_restart_korean_msg")
            )
            self.root.destroy()
            sys.exit(0)
        else:
            self.current_lang = new_lang
            self._refresh_texts()
            self._rebuild_menu()

    def _save_language(self):
        with open(LANG_FILE, 'w', encoding='utf-8') as f:
            json.dump({"lang": self.lang.get()}, f)

    def _load_match_rules(self):
        if Path(RULES_FILE).exists():
            try:
                with open(RULES_FILE, 'r', encoding='utf-8') as f:
                    self.match_rules = json.load(f)
            except Exception:
                self.match_rules = DEFAULT_RULES.copy()
        else:
            self.match_rules = DEFAULT_RULES.copy()

    def _save_match_rules(self):
        with open(RULES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.match_rules, f, indent=2, ensure_ascii=False)

    def _check_texconv(self):
        try:
            subprocess.run([TEXCONV, "--version"], capture_output=True, check=True)
            return True
        except Exception:
            return False

    def _load_presets(self):
        if Path(PRESET_FILE).exists():
            try:
                with open(PRESET_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return DEFAULT_PRESETS.copy()

    def _save_presets_to_file(self):
        with open(PRESET_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.presets, f, indent=2, ensure_ascii=False)

    # ---------------- 菜单 ----------------
    def _build_menu(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        lang_menu = Menu(menubar, tearoff=0)
        lang_menu.add_radiobutton(label="中文", variable=self.lang, value="zh")
        lang_menu.add_radiobutton(label="English", variable=self.lang, value="en")
        lang_menu.add_radiobutton(label="日本語", variable=self.lang, value="ja")
        lang_menu.add_radiobutton(label="한국어", variable=self.lang, value="ko")
        menubar.add_cascade(label=self.tr("lang_menu"), menu=lang_menu)

        adv_menu = Menu(menubar, tearoff=0)
        adv_menu.add_command(label=self.tr("rules_menu"), command=self._edit_rules)
        menubar.add_cascade(label=self.tr("adv_menu"), menu=adv_menu)

        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label=self.tr("about_menu"), command=self._show_about)
        menubar.add_cascade(label=self.tr("help_menu"), menu=help_menu)

    def _rebuild_menu(self):
        self.root.config(menu=None)
        self._build_menu()

    def _edit_rules(self):
        win = tk.Toplevel(self.root)
        win.title(self.tr("rule_editor_title"))
        win.geometry("400x500")
        win.resizable(True, True)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=self.tr("rule_tip")).pack(anchor=tk.W)
        text = tk.Text(frame, wrap=tk.WORD, font=("Consolas", 10))
        text.pack(fill=tk.BOTH, expand=True, pady=5)

        for tex_type in self.match_rules:
            text.insert(tk.END, f"[{tex_type}]\n")
            for kw in self.match_rules[tex_type]:
                text.insert(tk.END, kw + "\n")
            text.insert(tk.END, "\n")

        def save():
            content = text.get("1.0", tk.END)
            new_rules = {}
            current_type = None
            for line in content.splitlines():
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    current_type = line[1:-1]
                    new_rules[current_type] = []
                elif current_type and line:
                    new_rules[current_type].append(line.lower())
            for t in DEFAULT_RULES.keys():
                if t not in new_rules:
                    new_rules[t] = []
            self.match_rules = new_rules
            self._save_match_rules()
            messagebox.showinfo(self.tr("rule_editor_title"), "Rules saved.")
            win.destroy()

        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text=self.tr("rule_save"), command=save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=self.tr("rule_cancel"), command=win.destroy).pack(side=tk.RIGHT)

    def _show_about(self):
        messagebox.showinfo(self.tr("about_menu"), self.tr("about_text"))

    # ---------------- UI 构建 ----------------
    def _build_ui(self):
        main = ttk.Frame(self.root, padding="15")
        main.pack(fill=tk.BOTH, expand=True)

        # 基础设置
        self.frame_dir = ttk.LabelFrame(main, text=self.tr("source_group"), padding=10)
        self.frame_dir.pack(fill=tk.X, pady=(0,10))

        row1 = ttk.Frame(self.frame_dir)
        row1.pack(fill=tk.X)
        self.lbl_dir = ttk.Label(row1, text=self.tr("source_label"))
        self.lbl_dir.pack(side=tk.LEFT)
        self.entry_dir = ttk.Entry(row1, textvariable=self.base_dir, width=45)
        self.entry_dir.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.btn_browse = ttk.Button(row1, text=self.tr("browse"), width=8, command=self._browse)
        self.btn_browse.pack(side=tk.LEFT)

        opts_frame = ttk.Frame(self.frame_dir)
        opts_frame.pack(fill=tk.X, pady=(5,0))
        self.chk_overwrite = tk.Checkbutton(opts_frame, text=self.tr("overwrite"), variable=self.overwrite,
                                            font=self.default_font, bg='#f5f5f5', activebackground='#f5f5f5')
        self.chk_overwrite.pack(side=tk.LEFT, padx=5)
        self.chk_alpha = tk.Checkbutton(opts_frame, text=self.tr("premul_alpha"), variable=self.premultiply_alpha,
                                        font=self.default_font, bg='#f5f5f5', activebackground='#f5f5f5')
        self.chk_alpha.pack(side=tk.LEFT, padx=5)
        self.chk_mip = tk.Checkbutton(opts_frame, text=self.tr("gen_mipmap"), variable=self.generate_mipmaps,
                                      font=self.default_font, bg='#f5f5f5', activebackground='#f5f5f5')
        self.chk_mip.pack(side=tk.LEFT, padx=5)

        # 分辨率
        self.frame_res = ttk.LabelFrame(main, text=self.tr("res_group"), padding=10)
        self.frame_res.pack(fill=tk.X, pady=(0,10))
        res_opts = list(RES_MAP.keys())
        grid = ttk.Frame(self.frame_res)
        grid.pack(fill=tk.X)
        self.lbl_bc = ttk.Label(grid, text=self.tr("res_basecolor"))
        self.lbl_bc.grid(row=0, column=0, padx=5, pady=3, sticky=tk.W)
        ttk.OptionMenu(grid, self.bc_res, self.bc_res.get(), *res_opts).grid(row=0, column=1, padx=5, pady=3, sticky=tk.W)
        self.lbl_n = ttk.Label(grid, text=self.tr("res_normal"))
        self.lbl_n.grid(row=1, column=0, padx=5, pady=3, sticky=tk.W)
        ttk.OptionMenu(grid, self.n_res, self.n_res.get(), *res_opts).grid(row=1, column=1, padx=5, pady=3, sticky=tk.W)
        self.lbl_pk = ttk.Label(grid, text=self.tr("res_packed"))
        self.lbl_pk.grid(row=2, column=0, padx=5, pady=3, sticky=tk.W)
        ttk.OptionMenu(grid, self.pack_res, self.pack_res.get(), *res_opts).grid(row=2, column=1, padx=5, pady=3, sticky=tk.W)

        # 通道组合
        self.frame_pack = ttk.LabelFrame(main, text=self.tr("packing_group"), padding=10)
        self.frame_pack.pack(fill=tk.X, pady=(0,10))

        preset_row = ttk.Frame(self.frame_pack)
        preset_row.pack(fill=tk.X, pady=(0,5))
        self.lbl_preset = ttk.Label(preset_row, text=self.tr("preset_label"))
        self.lbl_preset.pack(side=tk.LEFT)
        self.preset_combo = ttk.Combobox(preset_row, textvariable=self.preset_var, state='readonly', width=18)
        self.preset_combo.pack(side=tk.LEFT, padx=5)
        self.btn_save_preset = ttk.Button(preset_row, text=self.tr("save_preset"), command=self._save_preset)
        self.btn_save_preset.pack(side=tk.LEFT, padx=2)
        self.btn_del_preset = ttk.Button(preset_row, text=self.tr("del_preset"), command=self._delete_preset)
        self.btn_del_preset.pack(side=tk.LEFT)
        self._update_preset_list()

        ch_frame = ttk.Frame(self.frame_pack)
        ch_frame.pack(fill=tk.X, pady=5)
        self.ch_labels = []
        self.ch_combos = []
        lbls = [self.tr("r_ch"), self.tr("g_ch"), self.tr("b_ch"), self.tr("a_ch")]
        vars_ = [self.custom_r, self.custom_g, self.custom_b, self.custom_a]
        for i, (label, var) in enumerate(zip(lbls, vars_)):
            lbl = ttk.Label(ch_frame, text=label)
            lbl.grid(row=i, column=0, padx=5, pady=2, sticky=tk.W)
            self.ch_labels.append(lbl)
            combo = ttk.Combobox(ch_frame, textvariable=var, values=TEXTURE_TYPES, state='readonly', width=18)
            combo.grid(row=i, column=1, padx=5, pady=2, sticky=tk.W)
            self.ch_combos.append(combo)

        suffix_row = ttk.Frame(self.frame_pack)
        suffix_row.pack(fill=tk.X, pady=(5,0))
        self.lbl_suffix = ttk.Label(suffix_row, text=self.tr("suffix_label"))
        self.lbl_suffix.pack(side=tk.LEFT)
        self.suffix_entry = ttk.Entry(suffix_row, textvariable=self.custom_suffix, width=12, font=self.default_font)
        self.suffix_entry.pack(side=tk.LEFT, padx=5)

        self.preset_combo.bind('<<ComboboxSelected>>', lambda e: self._on_preset_change())

        # 进度与日志
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.BOTH, expand=True)

        self.progress = ttk.Progressbar(bottom, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0,5))

        ctrl_frame = ttk.Frame(bottom)
        ctrl_frame.pack(fill=tk.X, pady=(0,5))
        self.btn_pause = ttk.Button(ctrl_frame, text=self.tr("pause"), command=self._toggle_pause, state='disabled')
        self.btn_pause.pack(side=tk.LEFT, padx=5)
        self.btn_cancel = ttk.Button(ctrl_frame, text=self.tr("cancel"), command=self._cancel_process, state='disabled')
        self.btn_cancel.pack(side=tk.LEFT, padx=5)

        self.log_area = scrolledtext.ScrolledText(
            bottom, height=8, state='disabled', wrap=tk.WORD,
            font=("Consolas", 9), bg='white'
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.btn_start = ttk.Button(main, text=self.tr("start_btn"), command=self._start)
        self.btn_start.pack(pady=(10,0))

    def _refresh_texts(self):
        self.root.title(self.tr("title"))
        self.frame_dir.config(text=self.tr("source_group"))
        self.lbl_dir.config(text=self.tr("source_label"))
        self.btn_browse.config(text=self.tr("browse"))
        self.chk_overwrite.config(text=self.tr("overwrite"))
        self.chk_alpha.config(text=self.tr("premul_alpha"))
        self.chk_mip.config(text=self.tr("gen_mipmap"))
        self.frame_res.config(text=self.tr("res_group"))
        self.lbl_bc.config(text=self.tr("res_basecolor"))
        self.lbl_n.config(text=self.tr("res_normal"))
        self.lbl_pk.config(text=self.tr("res_packed"))
        self.frame_pack.config(text=self.tr("packing_group"))
        self.lbl_preset.config(text=self.tr("preset_label"))
        self.btn_save_preset.config(text=self.tr("save_preset"))
        self.btn_del_preset.config(text=self.tr("del_preset"))
        lbls = [self.tr("r_ch"), self.tr("g_ch"), self.tr("b_ch"), self.tr("a_ch")]
        for lbl, text in zip(self.ch_labels, lbls):
            lbl.config(text=text)
        self.lbl_suffix.config(text=self.tr("suffix_label"))
        self.btn_start.config(text=self.tr("start_btn"))
        if self.running and self.paused.is_set():
            self.btn_pause.config(text=self.tr("pause"))
        elif self.running:
            self.btn_pause.config(text=self.tr("resume"))
        else:
            self.btn_pause.config(text=self.tr("pause"))
        self.btn_cancel.config(text=self.tr("cancel"))

    # ---------------- 预设管理 ----------------
    def _update_preset_list(self):
        names = sorted(self.presets.keys())
        self.preset_combo['values'] = names
        if self.preset_var.get() not in self.presets:
            if names:
                self.preset_var.set(names[0])
                self._on_preset_change()

    def _on_preset_change(self):
        name = self.preset_var.get()
        if name not in self.presets:
            return
        preset = self.presets[name]
        self.custom_r.set(preset["R"])
        self.custom_g.set(preset["G"])
        self.custom_b.set(preset["B"])
        self.custom_a.set(preset["A"])
        self.custom_suffix.set(preset["suffix"])
        for combo in self.ch_combos:
            combo.configure(state='readonly')
        self.suffix_entry.configure(state='normal')

    def _save_preset(self):
        name = simpledialog.askstring(self.tr("preset_save_title"), self.tr("preset_save_prompt"))
        if not name:
            return
        if name in DEFAULT_PRESETS:
            messagebox.showerror(self.tr("dir_error"), self.tr("preset_overwrite"))
            return
        self.presets[name] = {
            "R": self.custom_r.get(),
            "G": self.custom_g.get(),
            "B": self.custom_b.get(),
            "A": self.custom_a.get(),
            "suffix": self.custom_suffix.get()
        }
        self._save_presets_to_file()
        self._update_preset_list()
        self.preset_var.set(name)
        self._log(self.tr("preset_saved").format(name=name))

    def _delete_preset(self):
        name = self.preset_var.get()
        if not name:
            return
        if name in DEFAULT_PRESETS:
            messagebox.showerror(self.tr("dir_error"), self.tr("preset_overwrite"))
            return
        if messagebox.askyesno(self.tr("del_preset"), self.tr("preset_delete_confirm").format(name=name)):
            del self.presets[name]
            self._save_presets_to_file()
            self._update_preset_list()
            if self.presets:
                self.preset_var.set(next(iter(self.presets)))
            self._on_preset_change()
            self._log(self.tr("preset_deleted").format(name=name))

    # ---------------- UI 操作 ----------------
    def _browse(self):
        path = filedialog.askdirectory(title=self.tr("browse"))
        if path:
            self.base_dir.set(path)

    def _log(self, msg):
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state='disabled')
        self.root.update_idletasks()

    def _update_progress(self, value, max_val):
        self.progress['maximum'] = max_val
        self.progress['value'] = value
        self.root.update_idletasks()

    def _toggle_pause(self):
        if self.paused.is_set():
            self.paused.clear()
            self.btn_pause.config(text=self.tr("resume"))
            self._log(self.tr("paused_msg"))
        else:
            self.paused.set()
            self.btn_pause.config(text=self.tr("pause"))
            self._log(self.tr("resumed_msg"))

    def _cancel_process(self):
        if not self.running:
            return
        if messagebox.askyesno(self.tr("cancel"), self.tr("cancel_confirm")):
            self.cancelled = True
            self.paused.set()
            if messagebox.askyesno(self.tr("cancel"), self.tr("delete_files_confirm")):
                with self.file_lock:
                    for fpath in self.generated_files:
                        try:
                            Path(fpath).unlink()
                        except Exception:
                            pass
                    self.generated_files.clear()
            self._log(self.tr("cancelled_msg"))

    def _start(self):
        if self.running:
            messagebox.showwarning("提示", self.tr("task_running"))
            return
        base = self.base_dir.get().strip()
        if not base or not Path(base).is_dir():
            messagebox.showerror(self.tr("dir_error"), self.tr("dir_error_msg"))
            return

        self.running = True
        self.cancelled = False
        self.generated_files = []
        self.paused.set()
        self.btn_pause.configure(state='normal', text=self.tr("pause"))
        self.btn_cancel.configure(state='normal')
        self._clear_log()
        self.progress['value'] = 0
        threading.Thread(target=self._run_process, args=(base,), daemon=True).start()

    def _clear_log(self):
        self.log_area.configure(state='normal')
        self.log_area.delete(1.0, tk.END)
        self.log_area.configure(state='disabled')

    def _run_process(self, base_dir):
        try:
            base = Path(base_dir)
            subdirs = [d for d in base.iterdir() if d.is_dir()]
            total = len(subdirs)
            if total == 0:
                self._log(self.tr("no_folder"))
                return
            self._log(self.tr("found_folders").format(total))
            for i, folder in enumerate(subdirs, 1):
                if self.cancelled:
                    break
                self.paused.wait()
                self._update_progress(i, total)
                self._process_folder(folder)
            self._update_progress(total, total)
            if not self.cancelled:
                self._log(self.tr("done"))
        except Exception as e:
            self._log(f"❌ 发生异常: {str(e)}")
        finally:
            self.running = False
            self.btn_pause.configure(state='disabled')
            self.btn_cancel.configure(state='disabled')

    # ---------------- 贴图处理 ----------------
    def _find_texture(self, folder: Path, type_key: str):
        if type_key == "None" or not type_key:
            return None
        keywords = self.match_rules.get(type_key, [type_key.lower()])
        for f in folder.glob("*.jpg"):
            f_lower = f.name.lower()
            for kw in keywords:
                if kw in f_lower:
                    return f
        return None

    def _resize(self, img, size):
        return img.resize(size, Image.Resampling.LANCZOS)

    def _save_dds(self, src_png, final_name, output_dir, tmp_dir, overwrite):
        final_dds = output_dir / f"{final_name}.dds"
        if final_dds.exists() and not overwrite:
            self._log(self.tr("log_skip_exist").format(name=final_dds.name))
            return False

        cmd = [TEXCONV, "-y", "-f", "R8G8B8A8_UNORM", "-if", "FANT"]
        if self.premultiply_alpha.get():
            cmd.append("-pmalpha")
        if self.generate_mipmaps.get():
            cmd.extend(["-m", "0"])
        cmd.extend(["-o", str(tmp_dir), str(src_png)])
        subprocess.run(cmd, check=True, capture_output=True)

        generated = tmp_dir / src_png.with_suffix(".dds").name
        if final_dds.exists():
            final_dds.unlink()
        generated.rename(final_dds)

        with self.file_lock:
            self.generated_files.append(str(final_dds))
        return True

    def _clean_basename(self, bc_path):
        name = bc_path.stem
        name = re.sub(r'_[24]K', '', name, flags=re.IGNORECASE)
        for kw in ["BaseColor", "basecolor", "Diffuse", "diffuse"]:
            name = name.replace(kw, "")
        name = re.sub(r'_+', '_', name).strip('_')
        return name

    def _process_folder(self, folder):
        fname = folder.name
        self._log(self.tr("log_folder_header").format(name=fname))

        bc_path = self._find_texture(folder, "BaseColor")
        n_path = self._find_texture(folder, "Normal")

        if not bc_path:
            self._log(self.tr("log_basecolor_missing"))
            return

        tmp_dir = folder / "_temp"
        tmp_dir.mkdir(exist_ok=True)

        try:
            # BaseColor
            bc_img = Image.open(bc_path).convert("RGBA")
            bc_size = RES_MAP[self.bc_res.get()]
            bc_resized = self._resize(bc_img, (bc_size, bc_size))
            bc_png = tmp_dir / "bc_temp.png"
            bc_resized.save(bc_png)
            if self._save_dds(bc_png, bc_path.stem, folder, tmp_dir, self.overwrite.get()):
                self._log(self.tr("log_basecolor_ok").format(name=bc_path.stem))

            # Normal
            if n_path:
                n_img = Image.open(n_path).convert("RGBA")
                n_size = RES_MAP[self.n_res.get()]
                n_resized = self._resize(n_img, (n_size, n_size))
                n_png = tmp_dir / "n_temp.png"
                n_resized.save(n_png)
                n_stem = re.sub(r'_[24]K', f'_{self.n_res.get()}', n_path.stem, flags=re.IGNORECASE)
                if self._save_dds(n_png, n_stem, folder, tmp_dir, self.overwrite.get()):
                    self._log(self.tr("log_normal_ok").format(name=n_stem))
            else:
                self._log(self.tr("log_normal_missing"))

            # 合成通道
            ch_r = self.custom_r.get()
            ch_g = self.custom_g.get()
            ch_b = self.custom_b.get()
            ch_a = self.custom_a.get()
            suffix = self.custom_suffix.get().strip() or "Packed"

            tex_r = self._find_texture(folder, ch_r) if ch_r != "None" else None
            tex_g = self._find_texture(folder, ch_g) if ch_g != "None" else None
            tex_b = self._find_texture(folder, ch_b) if ch_b != "None" else None
            tex_a = self._find_texture(folder, ch_a) if ch_a != "None" else None

            if not any([tex_r, tex_g, tex_b, tex_a]):
                self._log(self.tr("log_packed_missing"))
            else:
                pack_size = RES_MAP[self.pack_res.get()]
                packed = np.zeros((pack_size, pack_size, 4), dtype=np.uint8)
                for idx, (tex, is_alpha) in enumerate([(tex_r, False), (tex_g, False), (tex_b, False), (tex_a, True)]):
                    if tex is not None:
                        img = Image.open(tex).convert("L")
                        img = self._resize(img, (pack_size, pack_size))
                        packed[:, :, idx] = np.array(img)
                    else:
                        packed[:, :, idx] = 255 if is_alpha else 0

                packed_img = Image.fromarray(packed, "RGBA")
                packed_png = tmp_dir / "packed_temp.png"
                packed_img.save(packed_png)

                clean_base = self._clean_basename(bc_path)
                res_tag = self.pack_res.get()
                out_name = f"{clean_base}_{res_tag}_{suffix}"
                if self._save_dds(packed_png, out_name, folder, tmp_dir, self.overwrite.get()):
                    self._log(self.tr("log_packed_ok").format(name=out_name))

        except Exception as e:
            self._log(f"  ❌ 失败: {str(e)}")
        finally:
            for f in tmp_dir.glob("*"):
                f.unlink()
            try:
                tmp_dir.rmdir()
            except OSError:
                pass


if __name__ == "__main__":
    root = tk.Tk()
    app = TextureProcessorApp(root)
    root.mainloop()
