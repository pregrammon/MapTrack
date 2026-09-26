# -*- coding: utf-8 -*-
"""骑行轨迹地图 GUI：选择 gpx 文件 -> 生成地图 -> 自动打开浏览器。"""
import os, sys, threading
import tkinter as tk
from tkinter import filedialog, messagebox
import generate

BASE = os.path.dirname(os.path.abspath(__file__))
# 打包成 exe 后，把目录定位到 exe 所在位置
if getattr(sys, "frozen", False):
    BASE = os.path.dirname(sys.executable)


class App:
    def __init__(self, root):
        self.root = root
        root.title("骑行轨迹地图生成器")
        root.geometry("480x220")
        root.resizable(False, False)

        frm = tk.Frame(root, padx=18, pady=16)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="骑行轨迹地图生成器", font=("Microsoft YaHei", 14, "bold")).pack(anchor="w")
        tk.Label(frm, text="选择 GPX 轨迹文件，生成高德地图并自动打开浏览器。",
                 fg="#666", font=("Microsoft YaHei", 9)).pack(anchor="w", pady=(2, 12))

        # 文件选择行
        row = tk.Frame(frm)
        row.pack(fill="x", pady=4)
        self.path_var = tk.StringVar()
        self.entry = tk.Entry(row, textvariable=self.path_var, state="readonly",
                              readonlybackground="#f5f5f5", font=("Microsoft YaHei", 9))
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(row, text="选择 GPX…", command=self.choose_file, width=12).pack(side="left")

        # 生成按钮
        self.gen_btn = tk.Button(frm, text="生成并打开地图", command=self.generate,
                                 bg="#1a9c3c", fg="white", font=("Microsoft YaHei", 11, "bold"),
                                 padx=10, pady=6)
        self.gen_btn.pack(anchor="w", pady=(12, 8))

        # 状态栏
        self.status_var = tk.StringVar(value="请选择一个 GPX 文件。")
        tk.Label(frm, textvariable=self.status_var, fg="#2a7de1",
                 font=("Microsoft YaHei", 9), anchor="w").pack(fill="x")

        # 默认预填本目录下的 gpx（若有）
        cands = [f for f in os.listdir(BASE) if f.lower().endswith(".gpx")]
        if cands:
            self.path_var.set(os.path.join(BASE, cands[0]))
            self.status_var.set("已找到轨迹文件，可直接生成。")

    def choose_file(self):
        p = filedialog.askopenfilename(
            title="选择 GPX 轨迹文件",
            filetypes=[("GPX 轨迹文件", "*.gpx"), ("所有文件", "*.*")],
            initialdir=BASE)
        if p:
            self.path_var.set(p)
            self.status_var.set("已选择：%s" % os.path.basename(p))

    def generate(self):
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("未选择文件", "请先选择一个 GPX 文件。")
            return
        self.gen_btn.config(state="disabled")
        self.status_var.set("正在解析并生成地图，请稍候…")
        threading.Thread(target=self._work, args=(path,), daemon=True).start()

    def _work(self, path):
        def done(ok, msg):
            self.gen_btn.config(state="normal")
            self.status_var.set(msg)
            if not ok:
                messagebox.showerror("生成失败", msg)
        try:
            out = generate.gen_map(path, open_browser=True)
            base = os.path.basename(out)
            self.root.after(0, lambda: done(True, "生成成功：%s，已在浏览器打开。" % base))
        except Exception as e:
            self.root.after(0, lambda: done(False, "生成失败：%s" % e))


def main():
    try:
        root = tk.Tk()
    except Exception as e:
        # 无图形环境时退回命令行模式
        print("[GUI 不可用，改用命令行模式]", e)
        path = sys.argv[1] if len(sys.argv) > 1 else None
        generate.gen_map(path)
        return
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
