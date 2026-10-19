# -*- coding: utf-8 -*-
"""Caves of Lore 汉化 · 发布打包（两类包，产在 output/ 顶层 = GitHub 仓库根）。

产物（output/ 顶层，两个 *.zip 都是发布件）：
  Caves of Lore 简中汉化包 v1.0（玩家版）.zip
    └ Caves of Lore 简中汉化包/（安装.bat / 卸载.bat / 说明.txt / 术语说明.txt /
       Caves of Lore_Data/43 文件）
  Caves of Lore 简中汉化工程 v1.0（工程版）.zip
    └ Caves of Lore 简中汉化工程/（output/ 仓库内容快照：README/refer/tools/fonts/
       requirements/安装说明/提示词；origin/ 与 game/ 为空占位仅 说明.txt）

硬性守则：
  - 只读 origin/（工程根红线）：本脚本对 origin 仅 getsize（版本守卫），绝不写/删；
  - 两个 zip 内**不得**出现 SAVEGAME / StreamingAssets / .log / .l10nbak；
  - 玩家包 = 搬运式（整文件覆盖 + *.l10nbak 备份 + 卸载.bat 还原）；
  - bat 一律 GBK + CRLF；不含 chcp；if 块内 echo 无反斜杠/半角括号风险；
  - **不建 交付/ 目录、不保留解压副本**：两个 zip 由内存直接写盘；
  - 打包完成后把 output/game/ 清空为占位（仅 说明.txt）——生成物只进玩家包。

用法：python pack.py [--dry]
"""
import hashlib
import io
import os
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "output", "tools"))
import game_config as C  # noqa: E402

STAMP = "v1.0"
OUTPUT = os.path.join(ROOT, "output")
PLAYER_ROOT = "Caves of Lore 简中汉化包"
ENGINE_ROOT = "Caves of Lore 简中汉化工程"
ZP = os.path.join(OUTPUT, "Caves of Lore 简中汉化包 %s（玩家版）.zip" % STAMP)
ZE = os.path.join(OUTPUT, "Caves of Lore 简中汉化工程 %s（工程版）.zip" % STAMP)

FORBIDDEN = ("savegame", "streamingassets", ".log", ".l10nbak")


def load_files():
    lens = io.open(C.MODIFIED_LIST, encoding="utf-8").read().splitlines()
    out = []
    for ln in lens:
        ln = ln.strip().replace("\\", "/")
        if not ln:
            continue
        out.append(ln)
    return out


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------- bat / 说明 模板（GBK + CRLF） ----------------

HEADER = """@echo off
setlocal
title Caves of Lore 简中汉化 {STAMP} - {TITLE}
rem ============================================================
rem  本文件编码 GBK，勿另存为 UTF-8；勿加 chcp 65001。
rem  流程：定位游戏目录 - 版本指纹校验 - 备份原文件为 *.l10nbak - 覆盖。
rem ============================================================

set "SRC=%~dp0Caves of Lore_Data"
set "DST=%~dp0.."
if exist "%~dp0..\\Caves of Lore.exe" set "DST=%~dp0.."
if exist "%DST%\\Caves of Lore.exe" goto FOUND
set "DST=%~dp0"
if exist "%DST%\\Caves of Lore.exe" goto FOUND
goto NODIR
:FOUND

for %%A in ("%DST%\\Caves of Lore_Data\\resources.assets") do set "SZ=%%~zA"
if not exist "%DST%\\Caves of Lore_Data\\resources.assets" goto NODIR
if exist "%DST%\\Caves of Lore_Data\\resources.assets.l10nbak" goto SZOK
if "%SZ%"=="{ORIG_RES}" goto SZOK
echo ！！游戏版本不符：resources.assets 尺寸 %SZ%（预期 {ORIG_RES}）。
echo    本汉化包只适用于与之匹配的原版版本（通常为当前 Steam 正式版）。
echo    游戏更新后请等待对应版本汉化包，切勿强行安装。
pause
goto :eof
:SZOK

echo ============================================
echo    Caves of Lore 简中汉化 {STAMP}  {TITLE}
echo    游戏目录：%DST%
echo ============================================
echo.
echo  将处理 {NFILE} 个文件（原文件备份为 *.l10nbak，可用卸载.bat一键还原）
echo  按任意键开始
pause >nul
"""

FOOTER_OK = """echo.
echo  完成！共处理 {NFILE} 个文件。
echo  启动游戏即可（主菜单/对话/教程均为简体中文）。
echo  如需还原：双击 卸载.bat。
pause
goto :eof

:MISS_FILE
echo ！！游戏目录缺少预期文件：%F%
echo    请确认这是完整的 Caves of Lore 游戏目录。
pause
goto :eof

:NODIR
echo ！！未找到游戏目录（Caves of Lore.exe）。
echo    请把本文件夹放到游戏根目录，或与游戏目录同级后运行。
echo    建议先复制一份游戏目录做副本测试，不要直接改原版目录。
pause
goto :eof
"""


def gen_install(files, newset):
    parts = [HEADER.replace("{STAMP}", STAMP).replace("{TITLE}", "安装").replace(
        "{NFILE}", str(len(files))).replace("{ORIG_RES}", str(ORIG_RES_SIZE))]
    for rel in files:
        d = rel.replace("/", "\\")
        if rel in newset:
            # 新增文件（原版没有）：无备份、无存在性守卫，直接复制
            parts.append(
                "set \"F=%DST%\\Caves of Lore_Data\\{d}\"\n"
                "copy /y \"%SRC%\\{d}\" \"%F%\" >nul\n".format(d=d))
            continue
        parts.append(
            "set \"F=%DST%\\Caves of Lore_Data\\{d}\"\n"
            "if not exist \"%F%\" goto MISS_FILE\n"
            "if not exist \"%F%.l10nbak\" copy /y \"%F%\" \"%F%.l10nbak\" >nul\n"
            "copy /y \"%SRC%\\{d}\" \"%F%\" >nul\n".format(d=d))
    parts.append(FOOTER_OK.replace("{NFILE}", str(len(files))))
    return "".join(parts)


def gen_uninstall(files, newset):
    # 卸载不做版本守卫（已装的 resources.assets 尺寸本就与原版不同）
    parts = [HEADER.replace("{STAMP}", STAMP).replace("{TITLE}", "卸载还原").replace(
        "{NFILE}", str(len(files))).replace("{ORIG_RES}", str(ORIG_RES_SIZE))]
    # 移除版本守卫段（:SZOK 之前的部分保留目录定位）
    head = "".join(parts)
    idx = head.index("for %%A in")
    idx2 = head.index(":SZOK") + len(":SZOK")
    parts = [head[:idx] + head[idx2:]]
    for rel in files:
        d = rel.replace("/", "\\")
        if rel in newset:
            # 新增文件：无原版备份，卸载=直接删除
            parts.append(
                "set \"F=%DST%\\Caves of Lore_Data\\{d}\"\n"
                "if not exist \"%F%\" goto SKIP_{i}\n"
                "del \"%F%\" >nul\n"
                "echo   移除 {d}\n"
                ":SKIP_{i}\n".format(d=d, i=files.index(rel)))
            continue
        parts.append(
            "set \"F=%DST%\\Caves of Lore_Data\\{d}\"\n"
            "if not exist \"%F%.l10nbak\" goto SKIP_{i}\n"
            "copy /y \"%F%.l10nbak\" \"%F%\" >nul\n"
            "del \"%F%.l10nbak\" >nul\n"
            "echo   还原 {d}\n"
            ":SKIP_{i}\n".format(d=d, i=files.index(rel)))
    parts.append("""echo.
echo  还原完成，游戏已恢复原版（未安装过的文件自动跳过）。
pause
goto :eof

:MISS_FILE
echo ！！游戏目录缺少预期文件：%F%
pause
goto :eof

:NODIR
echo ！！未找到游戏目录（Caves of Lore.exe）。
echo    请把本文件夹放到游戏根目录，或与游戏目录同级后运行。
pause
goto :eof
""")
    return "".join(parts)


README_TXT = """Caves of Lore 简体中文汉化 {STAMP}
====================================

这是什么
--------
把游戏内全部文本（对话 / 界面 / 物品与技能说明 / 任务 / 教程 / 提示浮字 /
战斗文案 / 高亮话题词等）替换为简体中文的完整汉化，共处理 {NFILE} 个游戏文件
（其中 2 个为"存档兼容组件"，安装与卸载脚本会自动处理）。文本直接写进游戏
文件，不需要 Mod 加载器。

存档兼容（重点）
----------------
本汉化把中文放在"显示层"：游戏内部数据与游戏存档始终书写英文原文——
  · 装了汉化的存档，可直接交给不打汉化的原版游戏读取（显示英文），不会损坏；
  · 原版游戏的英文存档，装汉化后直接读取，界面/物品/任务自动显示中文；
  · 卸载汉化后，任何存档照常可用，无需任何转换；
  · 存档文件保持原版格式，绝不写入中文（本汉化的硬性红线）。

安装
----
强烈建议用【游戏副本】测试（复制一份整个游戏目录再装）：
  1. 把本文件夹整个复制到游戏根目录（与 Caves of Lore.exe 同级）；
     ——也可以放到与游戏目录同级的任意位置（会自动识别）。
  2. 双击 安装.bat（会自动校验游戏版本，并把原文件备份为 *.l10nbak）。
  3. 启动游戏，主菜单/对话即为中文。

卸载
----
双击 卸载.bat —— 自动从 *.l10nbak 还原全部原文件，并移除新增的存档
兼容组件（Managed/CavesL10N.dll、Managed/CavesL10N.table.txt）。

适用版本
--------
原版 Caves of Lore（Steam 正式版，数据指纹 resources.assets = {ORIG_RES} 字节）。
游戏更新后文件尺寸会变，安装脚本会自动拒绝，请等待对应版本汉化包。

版本指纹（安装后核对）
----------------------
resources.assets        {RES_SIZE}  {RES_MD5}
sharedassets0.assets    {SA0_SIZE}  {SA0_MD5}
level0                  {LV0_SIZE}  {LV0_MD5}
Managed/Assembly-CSharp.dll  {DLL_SIZE}  {DLL_MD5}
Managed/CavesL10N.dll        {CL_SIZE}  {CL_MD5}
Managed/CavesL10N.table.txt  {CLT_SIZE}  {CLT_MD5}

已知说明（接受项）
------------------
- 游戏内术语（伤害 / 效果 / 记忆 / 法术持续时间 / 属性词缀等）的机制解释，
  见本文件同目录的 术语说明.txt。
- 存档：因"存档只存英文"的设计，旧存档里的物品名/任务名等本来就是英文，
  读取后由游戏自动对照重建成中文显示（自愈）；极少数无法对应的旧条目
  会显示英文原文，不影响游戏进程。
- 为保持游戏内部机制（枚举比对、存档迁移、角色匹配等），少数调试/内部
  文本有意保留英文（如开发日志、按键名、部分队伍人名选项）。
- 物品「材质」、怪物图鉴「类型/伤害」、物品属性说明（伤害/效果/元素伤害/击退）、
  配方通配材料（「任意食物」）现已汉化（显示层）；按键设置里的键名与
  队伍人名保留英文（匹配机制所限，已知接受）。
- 极少数对话句在名词后带一个逗号（如「叛徒，旁边」）：游戏要求高亮词后
  紧跟标点才能染色并解锁话题，中文没有空格，故以此作分隔；不是错字。
- 若游戏更新导致安装被拒，请不要强行覆盖。

反馈
----
遇到任何显示问题（方块字、错位、未翻译段落），请记录【场景 + 截图】反馈。
"""


# ---------------- 打包主体 ----------------

def chk_forbidden(zpath, label):
    bad = []
    with zipfile.ZipFile(zpath) as z:
        for n in z.namelist():
            low = n.lower()
            if ("savegame" in low or "streamingassets" in low
                    or low.endswith((".log", ".l10nbak", ".xml"))):
                bad.append(n)
    if bad:
        print("！%s 含禁用路径：%r" % (label, bad[:5]))
        sys.exit(1)
    print("  %s 禁用路径扫描：0" % label)


def write_gbk_bytes(text):
    text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    return text.encode("gbk")


def main():
    dry = "--dry" in sys.argv
    files = load_files()
    newset = set(rel for rel in files if not os.path.exists(
        os.path.join(C.ORIGIN_DIR, C.DATA_SUB, *rel.split("/"))))
    print("搬运清单 %d 个文件（其中新增 %d：%s）"
          % (len(files), len(newset), sorted(newset)))
    global ORIG_RES_SIZE
    ORIG_RES_SIZE = os.path.getsize(
        os.path.join(C.ORIGIN_DIR, C.DATA_SUB, "resources.assets"))
    print("原版 resources.assets = %d 字节（版本守卫）" % ORIG_RES_SIZE)

    lf = os.path.join(C.LOC_FILES, C.DATA_SUB)
    for rel in files:
        p = os.path.join(lf, *rel.split("/"))
        if not os.path.isfile(p):
            print("！缺文件 %s" % p)
            sys.exit(1)

    if dry:
        print("（dry：不生成 zip）")
        return

    # ---- 玩家包：内存直接写盘（不落解压副本）----
    txt = (README_TXT.replace("{STAMP}", STAMP).replace("{NFILE}", str(len(files)))
           .replace("{ORIG_RES}", str(ORIG_RES_SIZE)))
    for key, rel in (("RES", "resources.assets"), ("SA0", "sharedassets0.assets"),
                     ("LV0", "level0"), ("DLL", "Managed/Assembly-CSharp.dll"),
                     ("CL", "Managed/CavesL10N.dll"),
                     ("CLT", "Managed/CavesL10N.table.txt")):
        p = os.path.join(lf, *rel.split("/"))
        txt = txt.replace("{%s_SIZE}" % key, str(os.path.getsize(p)))
        txt = txt.replace("{%s_MD5}" % key, md5_of(p))
    if os.path.exists(ZP):
        os.remove(ZP)
    term_txt = io.open(os.path.join(OUTPUT, "术语说明.txt"), encoding="utf-8").read()
    with zipfile.ZipFile(ZP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr(PLAYER_ROOT + "/安装.bat", write_gbk_bytes(gen_install(files, newset)))
        z.writestr(PLAYER_ROOT + "/卸载.bat", write_gbk_bytes(gen_uninstall(files, newset)))
        z.writestr(PLAYER_ROOT + "/说明.txt", write_gbk_bytes(txt))
        z.writestr(PLAYER_ROOT + "/术语说明.txt", write_gbk_bytes(term_txt))
        for rel in files:
            z.write(os.path.join(lf, *rel.split("/")),
                    PLAYER_ROOT + "/" + C.DATA_SUB + "/" + rel)

    # ---- 工程包：output/（GitHub 仓库根）内容快照 ----
    #   origin/ 与 game/ 只保留占位 说明.txt；排除发布 zip 自身与缓存。
    if os.path.exists(ZE):
        os.remove(ZE)
    with zipfile.ZipFile(ZE, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for dp, dns, fns in os.walk(OUTPUT):
            dns[:] = sorted(d for d in dns if d not in
                            ("__pycache__", ".git", "game", "origin"))
            rel = os.path.relpath(dp, OUTPUT).replace(os.sep, "/")
            for f in sorted(fns):
                if f.endswith((".zip", ".pyc")) or f.lower().endswith(".log"):
                    continue
                p = os.path.join(dp, f)
                arc = ENGINE_ROOT + "/" + (rel + "/" if rel != "." else "") + f
                z.write(p, arc)
        for ph in ("origin/说明.txt", "game/说明.txt"):
            p = os.path.join(OUTPUT, *ph.split("/"))
            z.write(p, ENGINE_ROOT + "/" + ph)

    print("玩家包：%.1f MB  %s" % (os.path.getsize(ZP) / 1048576.0, ZP))
    print("工程包：%.1f MB  %s" % (os.path.getsize(ZE) / 1048576.0, ZE))
    chk_forbidden(ZP, "玩家包")
    chk_forbidden(ZE, "工程包")

    # ---- 打包后把 game/ 清空为占位（生成物只进玩家包）----
    import shutil
    import time

    def _rm(p):
        # Windows 上刚写完的大目录可能被杀软/索引短暂占用（WinError 32）→ 重试
        for _ in range(10):
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
                return
            except PermissionError:
                time.sleep(0.5)
        raise

    game = os.path.join(OUTPUT, "game")
    for name in os.listdir(game):
        if name == "说明.txt":
            continue
        _rm(os.path.join(game, name))
    print("game/ 已清空为占位（仅 说明.txt）")


if __name__ == "__main__":
    ORIG_RES_SIZE = 0
    main()
