# -*- coding: utf-8 -*-
"""打印 loc_files 全部产物的 相对路径 大小 md5（构建可复现性对比用）。"""
import hashlib
import os

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "output", "game", "loc_files", "Caves of Lore_Data")

rows = []
for root, dirs, files in os.walk(BASE):
    for f in sorted(files):
        p = os.path.join(root, f)
        rel = os.path.relpath(p, BASE).replace(os.sep, "/")
        with open(p, "rb") as fh:
            data = fh.read()
        rows.append("%-32s %10d  %s" % (rel, len(data), hashlib.md5(data).hexdigest()))
for r in sorted(rows):
    print(r)
