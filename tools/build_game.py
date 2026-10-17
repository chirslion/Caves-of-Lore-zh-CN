# -*- coding: utf-8 -*-
"""Caves of Lore 汉化 · 构建：refer → 游戏文件（output/game/loc_files 搬运式）。

流程：
  1. 读 refer 全部 json（有 CN 的行）；
  2. 按文件聚类 → UnityPy 加载 → 逐对象：裸解析 → set_string → 重编码 → set_raw_data
     （每个对象编解码自证：重解析再重编码必须与原 bytes 相同）；
  3. sharedassets0.assets 追加字体合并（charset = 全部 CN 字符并集；排除 unifont 图标字体）；
  4. 保存到 output/game/loc_files/Caves of Lore_Data/；
  5. DLL 补丁产物与存档边界辅助程序集登记进 Managed/——优先取开发工作区
     （workspace/colpatch/out_dll、workspace/savefix/out）的最新产物；工程包内
     没有 workspace/，则回退到 tools/prebuilt/ 随包预编译件（一一对应、md5 见其说明）；
     （colpatch 生成命令：dotnet run --project workspace/colpatch -- apply-map
       "origin/Caves of Lore_Data/Managed/Assembly-CSharp.dll"
       "workspace/colpatch/out_dll/Assembly-CSharp.dll"
       workspace/colpatch/tr_map.tsv --d1；spec 由 tools/dll_spec_build.py 生成）
  6. 输出 modified_files.txt（搬运清单）与统计报告。

用法：python build_game.py [--dry]
"""
import io
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_config as C  # noqa: E402
import col_lib as CL  # noqa: E402
import col_schemas as CS  # noqa: E402

import UnityPy  # noqa: E402

SHORT2FILE = {}
for fn in CL.FILES:
    SHORT2FILE[CL.short_name(fn)] = fn

SKIP_FONT_NAMES = {"unifont"}      # 图标字体：不合并
MERGE_FONT_FILES = {"sharedassets0.assets", "resources.assets"}

PATCHED_DLL = os.path.join(C.PROJECT_DIR, "workspace", "colpatch", "out_dll", "Assembly-CSharp.dll")
DLL_REL = os.path.join("Managed", "Assembly-CSharp.dll")
# 工程包内置的预编译件（workspace/ 不进工程包，收件人靠这里逐字节复现产物）
PREBUILT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prebuilt")


def _prebuilt(name):
    p = os.path.join(PREBUILT_DIR, name)
    return p if os.path.exists(p) else None


def build_script_maps():
    maps = {}
    for fn in ("globalgamemanagers.assets", "resources.assets"):
        p = os.path.join(C.ORIGIN_DIR, C.DATA_SUB, fn)
        if not os.path.exists(p):
            continue
        env = UnityPy.load(p)
        m = {}
        for o in env.objects:
            if o.type.name == "MonoScript":
                pr = CL.parse_monoscript(o.get_raw_data())
                if pr:
                    m[o.path_id] = (pr[1], pr[2], pr[3])
        maps[fn] = m
        del env
    return maps


def load_refer_edits():
    """返回 [(short, pid, path, cn, en, rid)], 以及全 CN 字符集。"""
    edits = []
    charset = set()
    def take(fp):
        try:
            d = json.load(io.open(fp, encoding="utf-8"))
        except Exception as e:
            print("  ! 读取失败 %s：%r" % (fp, e))
            return
        for row in d.get("entries", []):
            rid = row[0]
            if rid.startswith("dll:"):
                # DLL 字面量行不生成资源改写（置入 DLL 补丁），但译文同样会显示在
                # 游戏里（运行时由 DLL 的 ldstr 渲染）——字符必须进字体字符集。
                # 2026-10-16 实测坑：「沓」（"一沓切得极薄的木片"）只存在于 DLL 行，
                # 被此 continue 漏掉 → 成品字体缺字 → 游戏回退默认字体（大小/基线不一致）。
                _cn = row[-1]
                if isinstance(_cn, str):
                    charset.update(_cn)
                continue
            cn = row[-1]
            # 对话行 [id, speaker, en, cn]；其余 [id, en, cn] —— 两者 row[-2] 都是 EN
            en = row[-2]
            if not cn:
                continue
            parts = rid.split("/", 1)
            if len(parts) != 2 or "#" not in parts[0]:
                continue
            short, pid = parts[0].split("#")
            if short not in SHORT2FILE or not pid.isdigit():
                continue
            edits.append((short, int(pid), parts[1], cn, en))
            charset.update(cn)
    # 对话
    dd = os.path.join(C.REFER_DIR, "对话")
    if os.path.isdir(dd):
        for f in sorted(os.listdir(dd)):
            if f.endswith(".json"):
                take(os.path.join(dd, f))
    # 顶层 json 与 数据文本/
    top = [f for f in os.listdir(C.REFER_DIR) if f.endswith(".json")]
    for f in sorted(top):
        take(os.path.join(C.REFER_DIR, f))
    ddm = os.path.join(C.REFER_DIR, "数据文本")
    if os.path.isdir(ddm):
        for f in sorted(os.listdir(ddm)):
            if f.endswith(".json"):
                take(os.path.join(ddm, f))
    return edits, charset


def main():
    dry = "--dry" in sys.argv
    print("origin =", os.path.join(C.ORIGIN_DIR, C.DATA_SUB))
    maps = build_script_maps()
    edits, charset = load_refer_edits()
    # 按钮贴图汉化（tools/b7_fix.py）用到的字符也并入字库
    try:
        import b7_fix
        for (_fn, _kind, _tid, _rect, _cn) in b7_fix.ENTRIES:
            charset.update(_cn)
    except Exception as e:
        print("  （b7 标签字库并入跳过：%r）" % e)
    print("refer 有译文的条目：%d；字符集：%d 个" % (len(edits), len(charset)))

    by_file = {}
    for e in edits:
        by_file.setdefault(e[0], []).append(e)

    # 字体字符集（含标点保底）
    # + DLL 显示层注入（CavesL10N.OreName/AbilityName）的输出字符：这些字不出现在
    #   refer 里（数据侧=英文标识符），若不并入会变豆腐块——2026-10-16 实测
    #   specialAbilityName 还原英文后「咆哮」二字掉出字库（AbilityName("Roar") 输出）。
    # 属性后缀词表（--affix helper 输出；与 DLL 注入共用同一词表 TSV）
    # 开发时用 workspace/savefix/affix_words.tsv；工程包内回退 tools/prebuilt/affix_words.tsv
    affix_chars = ""
    _affix_path = os.path.join(C.PROJECT_DIR, "workspace", "savefix", "affix_words.tsv")
    if not os.path.exists(_affix_path):
        _affix_path = os.path.join(PREBUILT_DIR, "affix_words.tsv")
    if os.path.exists(_affix_path):
        for _ln in io.open(_affix_path, encoding="utf-8").read().splitlines():
            if "\t" in _ln:
                affix_chars += _ln.split("\t")[0]
    font_charset = set(charset) | set("，。、！？：；（）《》…——·「」“”‘’") | set(
        "铁矿石银矿刚玉符文感知虚张声势咆哮风之献曲洞察矿脉追踪灵魂世界嗅探"
        "毁灭束缚防护召唤位移转化转移"
        "布料纸张血肉木头硬币书籍皮革甲壳泥土节肢宠物家畜两栖软体异变构造巨龙元素巨人哥布林妖精黏液挥砍穿刺钝击酸蚀"
        "钥匙墓园图书馆矿井生锈地窖铲镐桶典籍蝴蝶月长石晶"
        "基础虚体无定形大地石质熔岩水流寒冰闪电气流木质虚空需要一把刚玉飞行大型距离时"
        # 第二十四轮：ItemAttributeModifier 说明片段 + --recipe 物品类型名 helper 输出
        "伤害效果击退武器法术火焰冰霜闪电毒素神圣食物原料药水护甲衣物乐器配方箭矢"
        "护符宝箱跟随图标货币项链戒指空白特殊书笔记盾牌法术书武器盾法球箭袋") | set(affix_chars)  # + --school/--enumdisp/--itemalias/--affix/--recipe helper 输出
    font_file = None
    if os.path.isdir(C.FONTS_DIR):
        for fn in sorted(os.listdir(C.FONTS_DIR)):
            if fn.lower().endswith((".ttf", ".otf")):
                font_file = os.path.join(C.FONTS_DIR, fn)
                break

    modified = []
    for short, items in sorted(by_file.items()):
        fn = SHORT2FILE[short]
        src = os.path.join(C.ORIGIN_DIR, C.DATA_SUB, fn)
        env = UnityPy.load(src)
        objs = {o.path_id: o for o in env.objects}   # 轻量索引（不读 raw）
        exts = [(getattr(x, "path", "") or "").replace("\\", "/").split("/")[-1]
                for x in getattr(env.file, "externals", [])]
        n_applied = 0
        by_pid = {}
        for e in items:
            by_pid.setdefault(e[1], []).append(e)
        for pid, es in sorted(by_pid.items()):
            o = objs.get(pid)
            if o is None:
                print("  ! %s#%d 对象不存在（跳过 %d 条）" % (short, pid, len(es)))
                continue
            raw = o.get_raw_data()
            fid = CL.u32(raw, 16)
            pscript = CL.i64(raw, 20)
            tgt = fn if fid == 0 else (exts[fid - 1] if fid - 1 < len(exts) else None)
            info = maps.get(tgt, {}).get(pscript)
            if not info:
                print("  ! %s#%d 类未知（跳过）" % (short, pid))
                continue
            key = info[2] if not info[0] else (info[0] + "." + info[2])
            schema = CS.SCHEMAS.get(key)
            if schema is None:
                print("  ! %s#%d 无 schema（%s，跳过）" % (short, pid, key))
                continue
            prefix, fields = CL.parse_obj(raw, schema)
            for (_, _, path, cn, en) in es:
                try:
                    CL.set_string(fields, path, cn)
                except Exception as ex:
                    print("  ! %s#%d/%s 写入失败：%r" % (short, pid, path, ex))
            new_raw = CL.encode_obj(prefix, fields, schema)
            _, chk = CL.parse_obj(new_raw, schema)
            if CL.encode_obj(prefix, chk, schema) != new_raw:
                print("  ！%s#%d 编解码自证失败，跳过" % (short, pid))
                continue
            if not dry:
                o.set_raw_data(new_raw)
            n_applied += 1

        # 字体合并
        n_font = 0
        if fn in MERGE_FONT_FILES and font_file and not dry:
            for o in env.objects:
                if o.type.name != "Font":
                    continue
                try:
                    d = o.read()
                    name = getattr(d, "m_Name", "") or ""
                    if name in SKIP_FONT_NAMES:
                        continue
                    raw_ttf = bytes(d.m_FontData)
                    if not raw_ttf:
                        continue
                    import font_tool as FT
                    merged = FT.merge_cjk(raw_ttf, font_file, font_charset)
                    d.m_FontData = list(merged)
                    d.save()
                    n_font += 1
                    print("  · 字体 %s：%d → %d 字节" % (name, len(raw_ttf), len(merged)))
                except Exception as ex:
                    print("  ! 字体 %s 合并失败：%r" % (getattr(o, "path_id", "?"), str(ex)[:80]))
        if dry:
            continue
        if n_applied or n_font:
            out_dir = os.path.join(C.LOC_FILES, C.DATA_SUB)
            os.makedirs(out_dir, exist_ok=True)
            out = os.path.join(out_dir, fn)
            with io.open(out, "wb") as f:
                f.write(env.file.save())
            modified.append(fn)
            print("写出 %s（对象 %d，字体 %d）" % (fn, n_applied, n_font))
        del env

    # DLL（补丁产物：优先 workspace/colpatch 最新产物，否则回退 tools/prebuilt 随包件）
    if not dry:
        dll_staged = os.path.join(C.LOC_FILES, C.DATA_SUB, DLL_REL)
        dll_src = PATCHED_DLL if os.path.exists(PATCHED_DLL) else _prebuilt("Assembly-CSharp.dll")
        if dll_src:
            os.makedirs(os.path.dirname(dll_staged), exist_ok=True)
            shutil.copyfile(dll_src, dll_staged)
            modified.append(DLL_REL)
            print("登记 Managed/Assembly-CSharp.dll（补丁版，%.1f KB，来源 %s）"
                  % (os.path.getsize(dll_staged) / 1024.0,
                     "workspace/colpatch" if dll_src == PATCHED_DLL else "tools/prebuilt"))
        else:
            print("！未找到补丁版 DLL（workspace/colpatch/out_dll 与 tools/prebuilt 均缺）")
        # 存档边界翻译辅助程序集 + 翻译表（--savefix 依赖；随包安装到 Managed/）
        for _name, _rel in (("CavesL10N.dll", os.path.join("Managed", "CavesL10N.dll")),
                            ("CavesL10N.table.txt", os.path.join("Managed", "CavesL10N.table.txt"))):
            _src = os.path.join(C.PROJECT_DIR, "workspace", "savefix", "out", _name)
            if not os.path.exists(_src):
                _src = _prebuilt(_name)
            if _src:
                _dst = os.path.join(C.LOC_FILES, C.DATA_SUB, _rel)
                os.makedirs(os.path.dirname(_dst), exist_ok=True)
                shutil.copyfile(_src, _dst)
                modified.append(_rel)
                print("登记 %s（%.1f KB）" % (_rel, os.path.getsize(_dst) / 1024.0))
            else:
                print("！缺 %s（workspace/savefix/out 与 tools/prebuilt 均缺）" % _name)

    if not dry:
        with io.open(C.MODIFIED_LIST, "w", encoding="utf-8", newline="\n") as f:
            for m in sorted(modified):
                f.write(m + "\n")
        print("完成：%d 个文件 → %s" % (len(modified), C.LOC_FILES))


if __name__ == "__main__":
    main()
