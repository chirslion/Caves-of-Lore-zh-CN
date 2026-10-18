# -*- coding: utf-8 -*-
"""Caves of Lore 汉化 · 路径与常量配置。"""
import os

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.dirname(TOOLS_DIR)                 # output/
PROJECT_DIR = os.path.dirname(OUTPUT_DIR)

REFER_DIR = os.path.join(OUTPUT_DIR, "refer")
FONTS_DIR = os.path.join(OUTPUT_DIR, "fonts")
GAME_DIR = os.path.join(OUTPUT_DIR, "game")
LOC_FILES = os.path.join(GAME_DIR, "loc_files")

DATA_SUB = "Caves of Lore_Data"
EXE_NAME = "Caves of Lore.exe"

# origin：优先 output/origin（收件人流程），否则工程根 origin（本机开发）
_ORIG_A = os.path.join(OUTPUT_DIR, "origin")
_ORIG_B = os.path.join(PROJECT_DIR, "origin")
ORIGIN_DIR = _ORIG_A if os.path.exists(os.path.join(_ORIG_A, DATA_SUB)) else _ORIG_B

# 打包时必须存在的原版文件（由 build 生成覆盖清单）
MODIFIED_LIST = os.path.join(GAME_DIR, "modified_files.txt")

# 指纹（构建后回填；三处同步：本文件 ↔ 玩家包说明.txt ↔ README）
CN_FINGERPRINTS = {
    "Caves of Lore_Data/resources.assets": (37275968, "1930c597403407cb9353809b717a1acf"),
    "Caves of Lore_Data/sharedassets0.assets": (51419552, "0d659384a14113caf795353f83667ab9"),
    "Caves of Lore_Data/level0": (24283776, "4d3772c9037df359654339bb805b33aa"),
    "Caves of Lore_Data/Managed/Assembly-CSharp.dll": (2745344, "934dc80a794b9de02be2a4e85c5ae729"),
    "Caves of Lore_Data/Managed/CavesL10N.dll": (16384, "e3077c8ce7808d79c9c136018c203be3"),
    "Caves of Lore_Data/Managed/CavesL10N.table.txt": (375660, "015a63a3920e423583ce53f434548204"),
}
