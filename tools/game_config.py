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
    "Caves of Lore_Data/resources.assets": (35113344, "f02b8f2fa9d2958200ee883d7eae0813"),
    "Caves of Lore_Data/sharedassets0.assets": (51323608, "714a6fc7fb1579c5a2584d09c22b463d"),
    "Caves of Lore_Data/level0": (24283776, "a645985dd3afa5e2ecd38941df415e4b"),
    "Caves of Lore_Data/Managed/Assembly-CSharp.dll": (2745344, "3d744baea13ad1861be697f0d1239a17"),
    "Caves of Lore_Data/Managed/CavesL10N.dll": (14848, "ee8638d422419a987c7b6f06354bf122"),
    "Caves of Lore_Data/Managed/CavesL10N.table.txt": (375660, "015a63a3920e423583ce53f434548204"),
}
