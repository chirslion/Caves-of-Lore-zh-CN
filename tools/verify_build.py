# -*- coding: utf-8 -*-
"""M6 产物校验：loc_files vs origin 白名单 diff + CN 读回验证。

门禁：
  1. 每个修改文件的对象集合与 origin 相同（path_id 全集一致）；
  2. 白名单对象（refer 有 CN 的 (short,pid)）之外的对象必须与 origin 逐字节相同
     （sharedassets0 的 Font 对象为已声明的例外；unifont 必须未变）；
  3. 白名单对象的每个 CN 字段读回 == refer 译文（用与 build 相同的 schema 解析）；
  4. 产物目录不得含 SAVEGAME / StreamingAssets / 存档类文件。
用法：python verify_build.py
"""
import io
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
OUT_TOOLS = os.path.join(os.path.dirname(os.path.dirname(TOOLS)), "output", "tools")
sys.path.insert(0, TOOLS)
sys.path.insert(0, OUT_TOOLS)
import game_config as C  # noqa: E402
import col_lib as CL  # noqa: E402
import col_schemas as CS  # noqa: E402
import build_game as BG  # noqa: E402

import UnityPy  # noqa: E402


def main():
    maps = BG.build_script_maps()
    edits, charset = BG.load_refer_edits()
    expect = {}
    for (short, pid, path, cn, en) in edits:
        expect.setdefault((short, pid), []).append((path, cn, en))
    print("期望变更对象：%d 个（%d 条译文）" % (len(expect), len(edits)))

    # b7 按钮贴图重绘对象（白名单：Texture2D 允许像素改动）
    b7set = set()
    try:
        import b7_fix
        for (fn, kind, tid, rect, cn) in b7_fix.ENTRIES:
            b7set.add((CL.short_name(fn), tid))
    except Exception as e:
        print("（b7 白名单加载失败：%r）" % e)
    b7_changed = 0

    # b8 排版修正对象（白名单：RectTransform 允许宽度改动）
    b8set = set()
    try:
        import json as _json
        _man = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "output", "game", "_b8_rect_objs.json")
        for _fn, _pids in _json.load(io.open(_man, encoding="utf-8")).items():
            for _p in _pids:
                b8set.add((CL.short_name(_fn), _p))
    except Exception as e:
        print("（b8 白名单加载失败：%r）" % e)
    b8_changed = 0
    if not b8set:
        raise SystemExit("b8 白名单为空——请先运行 b8_fontsize.py 生成 _b8_rect_objs.json")

    # b13 外科修补对象（GameVariables 成就副本；schema 无法解析 → 内容自证）
    b13set = set()
    b13_changed = 0
    try:
        import json as _json2
        _m2 = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "output", "game", "_b13_objs.json")
        for _fn, _pids in _json2.load(io.open(_m2, encoding="utf-8")).items():
            for _p in _pids:
                b13set.add((CL.short_name(_fn), _p))
    except Exception:
        pass

    modified = [l.strip().replace("\\", "/")
                for l in io.open(C.MODIFIED_LIST, encoding="utf-8") if l.strip()]
    problems = []
    total_chg = total_same = 0
    n_keep = 0
    fonts_changed = []

    for rel in modified:
        if rel.lower().endswith((".dll", ".txt")):
            p = os.path.join(C.LOC_FILES, C.DATA_SUB, *rel.split("/"))
            print("[dll] %s (%d 字节)" % (rel, os.path.getsize(p)))
            continue
        fn = rel
        short = CL.short_name(fn)
        ap = os.path.join(C.ORIGIN_DIR, C.DATA_SUB, fn)
        bp = os.path.join(C.LOC_FILES, C.DATA_SUB, fn)
        envA = UnityPy.load(ap)
        envB = UnityPy.load(bp)
        A = {o.path_id: o for o in envA.objects}
        B = {o.path_id: o for o in envB.objects}
        if set(A) != set(B):
            problems.append("%s 对象集合不一致（%d vs %d）" % (fn, len(A), len(B)))
            continue
        ex = dict((pid, v) for (s, pid), v in expect.items() if s == short)
        exts = [(getattr(x, "path", "") or "").replace("\\", "/").split("/")[-1]
                for x in getattr(envB.file, "externals", [])]
        n_chg = 0
        for pid, ob in B.items():
            rb = ob.get_raw_data()
            ra = A[pid].get_raw_data()
            if (short, pid) in b13set:
                # b13 外科修补对象（GameVariables 类 schema 解析失败，走内容自证）
                if rb == ra:
                    problems.append("%s#%d b13 对象未变化" % (fn, pid))
                else:
                    import struct as _st
                    bad = []
                    for (_p, _cn, _en) in ex.get(pid, []):
                        if _cn == _en:
                            continue
                        _b = _cn.encode("utf-8")
                        _needle = _st.pack("<i", len(_b)) + _b
                        if _needle not in rb:
                            bad.append(_cn)
                    if bad:
                        problems.append("%s#%d b13 CN 读回缺失 %r" % (fn, pid, bad[:3]))
                    else:
                        b13_changed += 1
                        n_chg += 1
                continue
            if pid in ex:
                # CN 读回
                fid = CL.u32(rb, 16)
                pscript = CL.i64(rb, 20)
                tgt = fn if fid == 0 else (exts[fid - 1] if fid - 1 < len(exts) else None)
                info = maps.get(tgt, {}).get(pscript)
                if not info:
                    problems.append("%s#%d 类未知" % (fn, pid))
                    continue
                key = info[2] if not info[0] else (info[0] + "." + info[2])
                schema = CS.SCHEMAS.get(key)
                if schema is None:
                    problems.append("%s#%d 无 schema %s" % (fn, pid, key))
                    continue
                _, fields = CL.parse_obj(rb, schema)
                for (path, cn, en) in ex[pid]:
                    node = CL.get_field(fields, path)
                    v = node.v if isinstance(node, CL.Str) else node
                    if v != cn:
                        problems.append("%s#%d/%s 读回不符: %r != %r"
                                        % (fn, pid, path, v, cn))
                if rb != ra:
                    n_chg += 1
                elif any(cn != en for (_, cn, en) in ex[pid]):
                    problems.append("%s#%d 白名单对象但字节未变（译文==原文？）" % (fn, pid))
                else:
                    n_keep += 1   # 全为有意保留（CN==EN）→ 不变正确
            elif ob.type.name == "Font":
                d = ob.read()
                name = getattr(d, "m_Name", "") or ""
                if rb == ra:
                    if name != "unifont":
                        problems.append("%s Font %s 未变化" % (fn, name))
                else:
                    fonts_changed.append((fn, name))
                    n_chg += 1
            else:
                if rb != ra:
                    if ob.type.name == "Texture2D" and (short, pid) in b7set:
                        b7_changed += 1
                        n_chg += 1
                    elif (short, pid) in b8set:
                        # b8 白名单：RectTransform（宽度/高度）或无 CN 的 Text（字号字段）
                        b8_changed += 1
                        n_chg += 1
                    else:
                        problems.append("%s#%d 非白名单对象被改动" % (fn, pid))
                else:
                    total_same += 1
        total_chg += n_chg
        print("  %-20s 变更 %3d（白名单 %d）/ 逐字节相同 %d"
              % (fn, n_chg, len(ex), len(B) - n_chg))
        del envA, envB

    # 4) 目录安全
    bad = []
    for root, dirs, files in os.walk(C.LOC_FILES):
        for f in files:
            low = f.lower()
            if "savegame" in low or "streamingassets" in low or low.endswith(".log") \
                    or low.endswith(".xml"):
                bad.append(os.path.join(root, f))
    if bad:
        problems.append("产物目录含存档/日志类文件：%r" % bad[:5])

    print("字体变更：%s" % ["%s" % n for (f, n) in fonts_changed])
    print("白名单外逐字节相同对象合计：%d" % total_same)
    print("白名单内全为有意保留（CN==EN）而未变对象：%d" % n_keep)
    print("b7 按钮贴图重绘对象：%d 个" % b7_changed)
    print("b8 排版修正对象（RectTransform）：%d 个" % b8_changed)
    print("b13 成就修补对象：%d 个" % b13_changed)
    if problems:
        print("！！问题 %d 条：" % len(problems))
        for p in problems[:40]:
            print("   ", p)
        sys.exit(1)
    print("PASS：白名单 diff 无越界、CN 读回全部一致、无存档类文件")


if __name__ == "__main__":
    main()
