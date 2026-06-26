import os
import sys
import subprocess
import threading
import json
import re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
from PIL import Image
import numpy as np

# -------------------- 配置 --------------------
TEXCONV = "texconv.exe"
PRESET_FILE = "packing_presets.json"

RES_MAP = {
    "8K": 8192, "4K": 4096, "2K": 2048,
    "1K": 1024, "512": 512, "256": 256,
}

TEXTURE_TYPES = [
    "None", "AO", "Cavity", "Displacement", "Emissive", "Fuzz",
    "Gloss", "Height", "Metal", "Opacity", "Reflection",
    "Roughness", "Scattering", "Specular"
]

DEFAULT_PRESETS = {
    "ORDp": {"R": "AO", "G": "Roughness", "B": "Displacement", "A": "None", "suffix": "ORDp"},
    "ORM":  {"R": "AO", "G": "Roughness", "B": "Metal", "A": "None", "suffix": "ORM"}
}


class TextureProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PBR 贴图批量处理 & 通道打包工具")
        self.root.geometry("720x780")
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

        # 路径 & 覆盖
        self.base_dir = tk.StringVar()
        self.overwrite = tk.BooleanVar(value=False)

        # 分辨率
        self.bc_res = tk.StringVar(value="4K")
        self.n_res = tk.StringVar(value="2K")
        self.pack_res = tk.StringVar(value="2K")

        # 新增：透明 & Mipmap
        self.premultiply_alpha = tk.BooleanVar(value=False)
        self.generate_mipmaps = tk.BooleanVar(value=False)

        # 预设 & 通道
        self.preset_var = tk.StringVar(value="ORDp")
        self.custom_r = tk.StringVar(value="AO")
        self.custom_g = tk.StringVar(value="Roughness")
        self.custom_b = tk.StringVar(value="Displacement")
        self.custom_a = tk.StringVar(value="None")
        self.custom_suffix = tk.StringVar(value="ORDp")

        self.running = False
        self.presets = self._load_presets()

        if not self._check_texconv():
            messagebox.showerror("错误", "texconv.exe 未找到，请将其放在程序同目录下。")
            root.destroy()
            return

        self._build_ui()
        self._on_preset_change()

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

    def _build_ui(self):
        main = ttk.Frame(self.root, padding="15")
        main.pack(fill=tk.BOTH, expand=True)

        # ---------- 基础设置 ----------
        frame_dir = ttk.LabelFrame(main, text="源文件夹 & 输出选项", padding=10)
        frame_dir.pack(fill=tk.X, pady=(0,10))

        row1 = ttk.Frame(frame_dir)
        row1.pack(fill=tk.X)
        ttk.Label(row1, text="资产根目录:").pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.base_dir, width=45).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        ttk.Button(row1, text="浏览", width=8, command=self._browse).pack(side=tk.LEFT)

        # 覆盖 + 透明 + Mipmap
        opts_frame = ttk.Frame(frame_dir)
        opts_frame.pack(fill=tk.X, pady=(5,0))
        tk.Checkbutton(opts_frame, text="覆盖已存在的 DDS 文件", variable=self.overwrite,
            font=self.default_font, bg='#f5f5f5', activebackground='#f5f5f5').pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(opts_frame, text="半透明材质 (预乘Alpha)", variable=self.premultiply_alpha,
            font=self.default_font, bg='#f5f5f5', activebackground='#f5f5f5').pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(opts_frame, text="生成 Mipmap", variable=self.generate_mipmaps,
            font=self.default_font, bg='#f5f5f5', activebackground='#f5f5f5').pack(side=tk.LEFT, padx=5)
        # ---------- 分辨率 ----------
        frame_res = ttk.LabelFrame(main, text="输出分辨率", padding=10)
        frame_res.pack(fill=tk.X, pady=(0,10))

        res_opts = list(RES_MAP.keys())
        grid = ttk.Frame(frame_res)
        grid.pack(fill=tk.X)
        ttk.Label(grid, text="BaseColor:").grid(row=0, column=0, padx=5, pady=3, sticky=tk.W)
        ttk.OptionMenu(grid, self.bc_res, self.bc_res.get(), *res_opts).grid(row=0, column=1, padx=5, pady=3, sticky=tk.W)
        ttk.Label(grid, text="Normal:").grid(row=1, column=0, padx=5, pady=3, sticky=tk.W)
        ttk.OptionMenu(grid, self.n_res, self.n_res.get(), *res_opts).grid(row=1, column=1, padx=5, pady=3, sticky=tk.W)
        ttk.Label(grid, text="通道贴图:").grid(row=2, column=0, padx=5, pady=3, sticky=tk.W)
        ttk.OptionMenu(grid, self.pack_res, self.pack_res.get(), *res_opts).grid(row=2, column=1, padx=5, pady=3, sticky=tk.W)

        # ---------- 通道组合配置 ----------
        frame_pack = ttk.LabelFrame(main, text="通道组合配置", padding=10)
        frame_pack.pack(fill=tk.X, pady=(0,10))

        preset_row = ttk.Frame(frame_pack)
        preset_row.pack(fill=tk.X, pady=(0,5))
        ttk.Label(preset_row, text="当前预设:").pack(side=tk.LEFT)
        self.preset_combo = ttk.Combobox(preset_row, textvariable=self.preset_var, state='readonly', width=18)
        self.preset_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_row, text="保存当前为预设", command=self._save_preset).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_row, text="删除选中预设", command=self._delete_preset).pack(side=tk.LEFT)
        self._update_preset_list()

        ch_frame = ttk.Frame(frame_pack)
        ch_frame.pack(fill=tk.X, pady=5)
        labels = ["R 通道:", "G 通道:", "B 通道:", "A 通道:"]
        vars_ = [self.custom_r, self.custom_g, self.custom_b, self.custom_a]
        self.ch_combos = []
        for i, (label, var) in enumerate(zip(labels, vars_)):
            ttk.Label(ch_frame, text=label).grid(row=i, column=0, padx=5, pady=2, sticky=tk.W)
            combo = ttk.Combobox(ch_frame, textvariable=var, values=TEXTURE_TYPES, state='readonly', width=18)
            combo.grid(row=i, column=1, padx=5, pady=2, sticky=tk.W)
            self.ch_combos.append(combo)

        suffix_row = ttk.Frame(frame_pack)
        suffix_row.pack(fill=tk.X, pady=(5,0))
        ttk.Label(suffix_row, text="输出后缀:").pack(side=tk.LEFT)
        self.suffix_entry = ttk.Entry(suffix_row, textvariable=self.custom_suffix, width=12, font=self.default_font)
        self.suffix_entry.pack(side=tk.LEFT, padx=5)

        self.preset_combo.bind('<<ComboboxSelected>>', lambda e: self._on_preset_change())

        # ---------- 进度与日志 ----------
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.BOTH, expand=True)
        self.progress = ttk.Progressbar(bottom, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0,5))
        self.log_area = scrolledtext.ScrolledText(
            bottom, height=8, state='disabled', wrap=tk.WORD,
            font=("Consolas", 9), bg='white'
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # ⚡ 开始按钮
        ttk.Button(main, text="▶  开始批量处理", command=self._start).pack(pady=(10,0))

    # -------------------- 预设管理 --------------------
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
        # 控件始终可编辑
        for combo in self.ch_combos:
            combo.configure(state='readonly')
        self.suffix_entry.configure(state='normal')

    def _save_preset(self):
        name = simpledialog.askstring("保存预设", "请输入预设名称（不可与内置同名）:")
        if not name:
            return
        if name in DEFAULT_PRESETS:
            messagebox.showerror("错误", "不能覆盖内置预设，请使用其他名称。")
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
        self._log(f"预设 '{name}' 已保存。")

    def _delete_preset(self):
        name = self.preset_var.get()
        if not name:
            return
        if name in DEFAULT_PRESETS:
            messagebox.showerror("错误", "内置预设不可删除。")
            return
        if messagebox.askyesno("确认删除", f"确定要删除预设 '{name}' 吗？"):
            del self.presets[name]
            self._save_presets_to_file()
            self._update_preset_list()
            if self.presets:
                self.preset_var.set(next(iter(self.presets)))
            self._on_preset_change()
            self._log(f"预设 '{name}' 已删除。")

    # -------------------- UI 辅助 --------------------
    def _browse(self):
        path = filedialog.askdirectory(title="选择资产根目录（包含子文件夹）")
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

    def _start(self):
        if self.running:
            messagebox.showwarning("提示", "任务正在进行中...")
            return
        base = self.base_dir.get().strip()
        if not base or not Path(base).is_dir():
            messagebox.showerror("错误", "请先选择有效的资产根目录")
            return

        self.running = True
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
                self._log("❌ 未找到子文件夹，请检查目录结构。")
                return
            self._log(f"找到 {total} 个资产文件夹，开始处理...\n")
            for i, folder in enumerate(subdirs, 1):
                self._update_progress(i, total)
                self._process_folder(folder)
            self._update_progress(total, total)
            self._log("\n✅ 全部完成！")
        except Exception as e:
            self._log(f"❌ 发生异常: {str(e)}")
        finally:
            self.running = False

    # -------------------- 贴图处理核心 --------------------
    def _find_texture(self, folder: Path, type_key: str):
        if type_key == "None" or not type_key:
            return None
        keywords = [type_key.lower()]
        if type_key == "Metal":
            keywords = ["metal", "metallic"]
        elif type_key == "BaseColor":
            keywords = ["basecolor", "base_color", "diffuse"]
        elif type_key == "Normal":
            keywords = ["normal", "norm"]
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
            self._log(f"  ⏩ 跳过已存在: {final_dds.name}")
            return False

        cmd = [TEXCONV, "-y", "-f", "R8G8B8A8_UNORM", "-if", "FANT"]

        # 根据选项添加预乘和 Mipmap
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
        self._log(f"📁 {fname}")

        bc_path = self._find_texture(folder, "BaseColor")
        n_path = self._find_texture(folder, "Normal")

        if not bc_path:
            self._log("  ⚠ 缺少 BaseColor，跳过")
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
                self._log(f"  ✓ BaseColor -> {bc_path.stem}.dds")

            # Normal
            if n_path:
                n_img = Image.open(n_path).convert("RGBA")
                n_size = RES_MAP[self.n_res.get()]
                n_resized = self._resize(n_img, (n_size, n_size))
                n_png = tmp_dir / "n_temp.png"
                n_resized.save(n_png)
                n_stem = re.sub(r'_[24]K', f'_{self.n_res.get()}', n_path.stem, flags=re.IGNORECASE)
                if self._save_dds(n_png, n_stem, folder, tmp_dir, self.overwrite.get()):
                    self._log(f"  ✓ Normal -> {n_stem}.dds")
            else:
                self._log("  ⚠ 没有法线贴图")

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
                self._log("  ⚠ 合成通道所需贴图全部缺失，跳过")
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
                    self._log(f"  ✓ 通道贴图 -> {out_name}.dds")

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