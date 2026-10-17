# -*- coding: utf-8 -*-
"""冷缓存验收：玩家包在"冷状态"（全新副本）下跑 安装.bat / 卸载.bat 全流程自证。

流程（全程只读 origin/，沙盒全用真实副本——不用硬链接，避免 copy 覆盖穿透到 origin）：
  1. 从 output/ 顶层取玩家包 zip（发布件；打包后 game/ 已清空，故清单以 zip 内文件为准）；
  2. 建 test/冷缓存验收/游戏/（Caves of Lore.exe + 目标文件 + 3 个对照文件的真实副本）；
  3. 解压玩家包到 游戏/<包目录>/；用 zip 内的 Caves of Lore_Data 文件集作为期望清单；
  4. cmd 运行 安装.bat → 全部目标文件必须与 zip 内副本逐字节相同；对照文件必须未变；
     备份数 = 非新增文件数；
  5. cmd 运行 卸载.bat → 非新增文件必须与原版 origin 逐字节相同；新增文件被删除；
     .l10nbak 清除；对照文件未变。
用法：python cold_test.py
"""
import hashlib
import io
import os
import shutil
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "output", "tools"))
import game_config as C  # noqa: E402

SANDBOX = os.path.join(ROOT, "test", "冷缓存验收")
GAME = os.path.join(SANDBOX, "游戏")
EXTRA_FILES = ["globalgamemanagers.assets", "sharedassets3.assets",
               "level30"]  # 不动的对照文件


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    out = os.path.join(ROOT, "output")
    zips = [f for f in os.listdir(out) if f.endswith("（玩家版）.zip")]
    assert len(zips) == 1, zips
    zp = os.path.join(out, zips[0])

    dd = os.path.join(C.ORIGIN_DIR, C.DATA_SUB)

    if os.path.isdir(SANDBOX):
        shutil.rmtree(SANDBOX)
    os.makedirs(GAME)

    # 1) 解压玩家包（发布件；清单 = zip 内 Caves of Lore_Data 下的文件）
    with zipfile.ZipFile(zp) as z:
        z.extractall(GAME)
    inner = None
    for d in os.listdir(GAME):
        cand = os.path.join(GAME, d)
        if os.path.isdir(cand) and os.path.exists(os.path.join(cand, "安装.bat")):
            inner = cand
    assert inner, "未找到解压后的包根"
    payload = os.path.join(inner, C.DATA_SUB)
    files = []
    for dp, _, fns in os.walk(payload):
        for f in fns:
            p = os.path.join(dp, f)
            files.append(os.path.relpath(p, payload).replace(os.sep, "/"))
    files.sort()
    assert files, "玩家包内没有数据文件"
    # 新增文件（原版没有：CavesL10N.*）——沙盒不预置、卸载后期望被删除、无备份
    newset = set(r for r in files if not os.path.exists(os.path.join(dd, *r.split("/"))))
    payload_md5 = {r: md5(os.path.join(payload, *r.split("/"))) for r in files}

    # 2) 冷副本（原版 exe + 非新增目标文件 + 对照文件）
    shutil.copy2(os.path.join(C.ORIGIN_DIR, C.EXE_NAME), os.path.join(GAME, C.EXE_NAME))
    for rel in files + EXTRA_FILES:
        if rel in newset:
            continue
        src = os.path.join(dd, *rel.split("/"))
        dst = os.path.join(GAME, C.DATA_SUB, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    orig_md5 = {r: md5(os.path.join(GAME, C.DATA_SUB, *r.split("/")))
                for r in (files + EXTRA_FILES) if r not in newset}
    print("沙盒就绪：%d 目标（新增 %d）+ %d 对照"
          % (len(files), len(newset), len(EXTRA_FILES)))

    # 3) 安装
    r = subprocess.run(["cmd", "/c", os.path.join(inner, "安装.bat")],
                       cwd=inner, input=b"\n\n\n\n", capture_output=True)
    outb = r.stdout.decode("gbk", "replace")
    print("安装 bat 退出码", r.returncode, "| 输出尾部：",
          outb.strip().splitlines()[-1] if outb.strip() else "(空)")
    ok = True
    n_bak = 0
    for rel in files:
        a = md5(os.path.join(GAME, C.DATA_SUB, *rel.split("/")))
        if a != payload_md5[rel]:
            print("！安装后与包内副本不一致 %s" % rel)
            ok = False
        if os.path.exists(os.path.join(GAME, C.DATA_SUB, *rel.split("/")) + ".l10nbak"):
            n_bak += 1
    for rel in EXTRA_FILES:
        if md5(os.path.join(GAME, C.DATA_SUB, *rel.split("/"))) != orig_md5[rel]:
            print("！对照文件被改动 %s" % rel)
            ok = False
    print("安装校验：%d 文件逐字节==包内副本：%s；备份数 %d/%d"
          % (len(files), ok, n_bak, len(files) - len(newset)))

    # 4) 卸载
    r = subprocess.run(["cmd", "/c", os.path.join(inner, "卸载.bat")],
                       cwd=inner, input=b"\n\n\n\n", capture_output=True)
    outb = r.stdout.decode("gbk", "replace")
    print("卸载 bat 退出码", r.returncode, "| 输出尾部：",
          outb.strip().splitlines()[-1] if outb.strip() else "(空)")
    left = 0
    for rel in files:
        p = os.path.join(GAME, C.DATA_SUB, *rel.split("/"))
        if rel in newset:
            if os.path.exists(p):
                print("！卸载后新增文件未移除 %s" % rel)
                ok = False
            continue
        if md5(p) != orig_md5[rel]:
            print("！卸载后未还原 %s" % rel)
            ok = False
        if os.path.exists(p + ".l10nbak"):
            left += 1
    for rel in EXTRA_FILES:
        if md5(os.path.join(GAME, C.DATA_SUB, *rel.split("/"))) != orig_md5[rel]:
            print("！对照文件被改动 %s" % rel)
            ok = False
    print("卸载校验：%d 文件==原版（新增加文件已删）：%s；残留备份 %d（应 0）"
          % (len(files), ok, left))
    expect_bak = len(files) - len(newset)
    print("冷缓存验收：", "PASS" if ok and n_bak == expect_bak and left == 0 else "FAIL")
    sys.exit(0 if ok and n_bak == expect_bak and left == 0 else 1)


if __name__ == "__main__":
    main()
