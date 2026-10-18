# -*- coding: utf-8 -*-
"""第八轮 · 排版统一（build_game 之后、verify 之前运行）。

实机反馈「同类型按钮文本大小却不同」的定位（2026-10-15，截图 + 数据双向取证）：
- 设置页开关行：BestFit 行的字号被【文本框高度 28.4】截断 → 渲染约 38px；
  固定字号行 (fs38) 渲染约 52px → 同列 38/52 混排。
  修：统一 fs38 固定（best=0）+ 文本框加宽 290（最长行「悬停查看生命值」7 字 = 266 < 290）。
- 标题「操作」fs32 → 34：相邻『更新日志』为贴图按钮（原生 12px 渲染 ≈ 38px），
  34×1.125 ≈ 38px 视觉一致。
- 知识菜单按钮：20/24/26 混排 + BestFit 高度截断。修：统一 fs38 固定 + 展宽 200
  （最长「符文与标记」5 字 = 190 < 200）。
- RectTransform 全为 pivot(0.5,0.5) + anchor(0.5,0.5) → 仅改 m_SizeDelta.x 对称生长，
  不出条、不影响其他行。

流程：python build_game.py && python b7_fix.py && python b8_fontsize.py && python verify_build.py
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "output", "tools"))
import col_lib as CL  # noqa: E402
import col_schemas as CS  # noqa: E402
import game_config as C  # noqa: E402
import UnityPy  # noqa: E402

FN = "level0"

# path_id -> (fontSize, bestFit, minSize, maxSize)
# 第九轮教训：编辑前必须核对对象归属（父链 GO 名）——#20752 是**设置界面**的「操作」，
# 标题界面的「操作」是 #25079（IntroButtonsLeft）。
# v1.8 终版口径（2026-10-16 第九轮反馈，「墨量对齐」）：
#   动态字体(CN 设计栅格≈21.5px) vs 像素贴图(栅格=1 texel×显示倍率≈3.16px)——同样外框高度
#   贴图笔画粗 1.5-2.6 倍，「看起来大小不同」的根源是**墨量(stroke×height)**。
#   解：#25079 fs84（44px，笔画≈2.05px）↔ #181 12px 原生渲染（28px，笔画=1 texel=3.16px），
#   墨量 44×2.05 ≈ 28×3.16 = 88 ∶ 88 → 视觉等重。
# 暂停菜单三兄弟（信息/成就/操作，原版 fs32≈33px）墨量对齐做不到时走"外框对齐"：
#   fs41 → 42px，与同屏贴图按钮(42px)外框同高。
TEXT_EDITS = {
    25079: (84, False, 1, 56),   # 标题「操作」：墨量对齐（配 #181 12px）
    20752: (41, False, 2, 48),   # 暂停菜单「操作」（原 32≈33px → 41≈42px 外框对齐）
    28122: (41, False, 2, 48),   # 暂停菜单「信息」（原 32 → 41）
    27860: (41, False, 2, 48),   # 暂停菜单「成就」（原 32 → 41）
    # 教程卡正文三框（TutorialManager displayText1/2/3，配 b16 重排）：
    # 原 BestFit max=32；重排后短行文本会顶到 24-32（58-75px）过大——封顶 16(≈37px)。
    # 长方格 360.7×89.3：≤5 行时 fs≤14.9 自然回落；更长的文本照旧缩小，不受影响。
    22684: (16, True, 10, 16),
    26149: (16, True, 10, 16),
    27588: (16, True, 10, 16),
    # —— 第十轮：#2/#4/#9 三处「字体大小不一」统一（收窄 BestFit 区间；min≈max×0.8）——
    # 技能面板（UI_SkillSelection → SkillPanel；iOS 副本一并）：
    23165: (20, True, 20, 20),   # 技能正文——第十一轮：min=max=20 彻底统一
    22590: (20, True, 20, 20),
    23581: (20, True, 20, 20),   # 技能细节——统一 20
    23288: (20, True, 20, 20),
    26798: (20, True, 20, 20),   # 技能弹窗正文——统一 20
    23540: (20, True, 20, 20),
    23008: (20, True, 20, 20),   # 技能名/黄标题——统一 20
    21226: (20, True, 20, 20),
    27787: (20, True, 20, 20),
    24766: (20, True, 20, 20),
    27026: (20, True, 20, 20),
    # 物品面板（DefaultItemInfoHolder）：
    20484: (20, True, 16, 20),   # 物品名（原 20/1/20，长名缩到 ~14）
    22810: (20, True, 16, 20),   # 材质值
    23233: (20, True, 16, 20),   # 材质标签
    21010: (20, True, 16, 20),   # 统一说明框（描述+法术列表，最大变动源）
    27647: (32, True, 26, 32),   # 角色名（CharNameBoxDup）
    27133: (18, True, 15, 18),   # 笔记信息（NoteInfoBox）
    # 制作名单「致谢」：原 fs20≈20px。第十轮 fs41+按钮放大 → 实机反馈"更不如没改前"
    # （底板被拉伸难看/出框）→ 回退按钮与文本框不动，字号取原框能吃满的 29（≈30px）。
    22542: (29, False, 2, 48),
    # —— 设置页行：统一 fs38 固定 ——
    19880: (38, False, 2, 40),   # 英雄待机动画（原 26 → 与同列 38 统一）
    25455: (38, False, 2, 40),   # 询问留下战利品（原 BestFit34 受高度截断）
    22699: (38, False, 2, 40),   # 移除界面描边
    26575: (38, False, 2, 40),   # 鼠标 + 摇杆
    21035: (38, False, 2, 40),   # 悬停查看生命值
    26820: (38, False, 2, 40),   # 始终显示生命值
    # —— 知识菜单按钮：统一 fs38 固定 ——
    20136: (38, False, 2, 40),   # 技能
    23367: (38, False, 2, 40),   # 属性
    20186: (38, False, 2, 40),   # 阵型
    20290: (38, False, 2, 40),   # 月相
    25997: (38, False, 2, 40),   # 符文标记（4 字，见 b9_refer_fix）
    23835: (38, False, 2, 40),   # 物品
    20931: (38, False, 2, 40),   # 露营
    22795: (38, False, 2, 40),   # 特质
    20783: (38, False, 2, 40),   # 战斗机制（单行化，见 b9_refer_fix）
    23139: (38, False, 2, 40),   # 战斗机制（另一副本，双保险）
    # —— 营地页签：急救/音乐/疲劳 原为固定 30，守夜(24049)为 BestFit（CN 短 → 撑到 40）
    #    → 统一固定 30（原版多数值）——
    24049: (30, False, 2, 40),   # 守夜
    # —— 附魔服务面板：「剥除附魔」是动态 Text（BestFit 10..40，框高 26.2 会被撑到
    #    ~20px），与左右两个像素贴图按钮（附魔/增幅，原生 12px）大小不一 →
    #    固定 12px 与贴图标签统一（截图 2026-10-18 用户反馈）。
    22831: (12, False, 2, 40),   # Strip Enchant（剥除附魔）
}
# 注：营地面板说明（20412/20435/20760/24610）第九轮曾改固定 38 + 加宽，实机与面板内
# 图形（血条/箭头示意）重叠错乱 → 已全部还原为原版 BestFit/原 rect（见 git 历史）。

# Outline 组件 path_id -> (effectDistance.x, effectDistance.y)
# v1.27：对话/教程字幕三框（TutorialManager displayText1-3，即 DisplayTextSpeaker1-3）
# 原版 Outline 距离 (2,-2)、alpha 0.5；中文像素字 BestFit 后约 15px，2px 四向描边
# 在实机里被读成「重影」。游戏内其余 100+ 处 Outline 均为标准 (1,-1)
# → 这三处统一为 1px（保留黑描边的可读性，不删除组件）。
OUTLINE_EDITS = {
    22685: (1.0, -1.0),   # DisplayTextSpeaker
    26148: (1.0, -1.0),   # DisplayTextSpeaker2
    27587: (1.0, -1.0),   # DisplayTextSpeaker3
}

# Text path_id -> (新宽度, 新高度)；高度 ≥ 38（fs38 单行），否则垂直截断。
# 尺寸变化时须确认 pivot=(0.5,0.5) + 居中锚点（本作 level0 全部满足，脚本内断言）。
RECT_EDITS = {
    19880: (290.0, None), 25455: (290.0, 42.6), 22699: (290.0, 42.6),
    26575: (290.0, 42.6), 21035: (290.0, 42.6), 26820: (290.0, 42.6),
    20136: (200.0, 42.6), 23367: (200.0, 42.6), 20186: (200.0, 42.6), 20290: (200.0, 42.6),
    25997: (200.0, 42.6), 23835: (200.0, 42.6), 20931: (200.0, 42.6), 22795: (200.0, 42.6),
    20783: (200.0, None), 23139: (200.0, 42.6),
    25079: (363.2, 110.0),   # 标题「操作」：fs84 行高≈101，rect 47.4→110 防垂直截断
    # 第十轮：物品面板三行的 18.9 高框容不下 fs16-20（行高≈19-24）→ 加高到 24
    20484: (216.0, 24.0),    # ItemNameBox
    22810: (114.2, 24.0),    # MaterialBox
    23233: (86.5, 24.0),     # MaterialGuideBox
}
# 直接 RT 键（按 RectTransform pid 而非 Text pid）——当前为空。
# （第十轮曾用 #19307 放大「致谢」按钮本体 95×48；第十一轮实机反馈"更不如没改前"
#   （底板拉伸难看）→ 已回退，本体不动，只调字号。）
DOC_RECTS = {}


def main():
    loc = os.path.join(ROOT, "output", "game", "loc_files", C.DATA_SUB, FN)
    if not os.path.exists(loc):
        raise SystemExit("未找到构建产物：%s" % loc)
    # .resS 相对路径解析（与 b7 相同的 CWD 处理）
    os.chdir(os.path.join(C.ORIGIN_DIR, C.DATA_SUB))
    env = UnityPy.load(loc)
    objs = {o.path_id: o for o in env.objects}
    # UnityPy 1.25.3 保存坑：data=None 的对象 save 时会经共享 reader 重读为空 → 预缓存
    for o in env.objects:
        if getattr(o, "data", None) is None:
            o.data = o.get_raw_data()

    schema = CS.SCHEMAS["UnityEngine.UI.Text"]

    # ---- 1) Text 字段（字号/BestFit）----
    go_of_text = {}
    n_text = 0
    for pid, (fs, best, mn, mx) in sorted(TEXT_EDITS.items()):
        o = objs.get(pid)
        if o is None:
            raise SystemExit("#%d 不存在" % pid)
        raw = o.get_raw_data()
        prefix, fields = CL.parse_obj(raw, schema)
        go_of_text[pid] = prefix["m_GameObject"][1]
        fd = fields["m_FontData"]
        old = (fd["m_FontSize"], fd["m_BestFit"], fd["m_MinSize"], fd["m_MaxSize"])
        fd["m_FontSize"], fd["m_BestFit"] = fs, best
        fd["m_MinSize"], fd["m_MaxSize"] = mn, mx
        new_raw = CL.encode_obj(prefix, fields, schema)
        _, chk = CL.parse_obj(new_raw, schema)
        if CL.encode_obj(prefix, chk, schema) != new_raw:
            raise SystemExit("#%d 编解码自证失败" % pid)
        o.set_raw_data(new_raw)
        n_text += 1
        print("  · Text #%d fs/best %s -> %s" % (pid, old[:2], (fs, best)))

    # ---- 1b) Outline 描边距离（对话字幕重影）----
    outline_schema = CS.SCHEMAS["UnityEngine.UI.Outline"]
    n_outline = 0
    for pid, (dx, dy) in sorted(OUTLINE_EDITS.items()):
        o = objs.get(pid)
        if o is None:
            raise SystemExit("#%d Outline 不存在" % pid)
        raw = o.get_raw_data()
        prefix, fields = CL.parse_obj(raw, outline_schema)
        old = tuple(fields["m_EffectDistance"])
        fields["m_EffectDistance"] = [dx, dy]
        new_raw = CL.encode_obj(prefix, fields, outline_schema)
        _, chk = CL.parse_obj(new_raw, outline_schema)
        if CL.encode_obj(prefix, chk, outline_schema) != new_raw:
            raise SystemExit("#%d Outline 编解码自证失败" % pid)
        o.set_raw_data(new_raw)
        n_outline += 1
        print("  · Outline #%d dist %s -> %s" % (pid, old, (dx, dy)))

    # ---- 2) RectTransform 宽度（按同 GO 找 RT；typetree 改宽）
    # 注意：UnityPy 的 get_raw_data()/read_typetree() 一律从磁盘原文件重读，
    # 修改只在内存对象里生效（set_raw_data 存 self.data，save 时使用）——
    # 因此一切回写校验必须在「保存后的新文件」上做（见步骤 3）。
    n_rect = 0
    done_go = {}
    for o in env.objects:
        if o.type.name != "RectTransform":
            continue
        tree = o.read_typetree()
        g = tree["m_GameObject"]["m_PathID"]
        for pid, (w, h) in RECT_EDITS.items():
            if go_of_text.get(pid) != g:
                continue
            # 只允许 pivot/anchor 居中的对象（改 m_SizeDelta 才会对称生长）
            if (abs(tree["m_Pivot"]["x"] - 0.5) > 1e-4 or abs(tree["m_Pivot"]["y"] - 0.5) > 1e-4
                    or abs(tree["m_AnchorMin"]["x"] - 0.5) > 1e-4 or abs(tree["m_AnchorMin"]["y"] - 0.5) > 1e-4
                    or abs(tree["m_AnchorMax"]["x"] - 0.5) > 1e-4 or abs(tree["m_AnchorMax"]["y"] - 0.5) > 1e-4):
                raise SystemExit("#%d 的 RectTransform 非居中锚点，布局改动不安全，中止" % pid)
            old_w = tree["m_SizeDelta"]["x"]
            old_h = tree["m_SizeDelta"]["y"]
            tree["m_SizeDelta"]["x"] = w
            if h is not None:
                tree["m_SizeDelta"]["y"] = h
            o.save_typetree(tree)
            done_go[pid] = o.path_id
            n_rect += 1
            print("  · Rect #%d (Text #%d) w %.1f->%.1f h %.1f->%.1f"
                  % (o.path_id, pid, old_w, w, old_h, (h if h is not None else old_h)))

    for pid in RECT_EDITS:
        if pid not in done_go:
            raise SystemExit("#%d 的 RectTransform 未找到" % pid)

    # ---- 2b) 按 RectTransform pid 直接指定的对象（如致谢按钮本体 #19307）----
    doc_done = []
    for rtpid, (w, h) in DOC_RECTS.items():
        o = objs.get(rtpid)
        if o is None or o.type.name != "RectTransform":
            raise SystemExit("#%d 直指 RT 未找到" % rtpid)
        tree = o.read_typetree()
        if (abs(tree["m_Pivot"]["x"] - 0.5) > 1e-4 or abs(tree["m_Pivot"]["y"] - 0.5) > 1e-4
                or abs(tree["m_AnchorMin"]["x"] - 0.5) > 1e-4 or abs(tree["m_AnchorMin"]["y"] - 0.5) > 1e-4
                or abs(tree["m_AnchorMax"]["x"] - 0.5) > 1e-4 or abs(tree["m_AnchorMax"]["y"] - 0.5) > 1e-4):
            raise SystemExit("#%d 直指 RT 非居中锚点，中止" % rtpid)
        old_w = tree["m_SizeDelta"]["x"]
        old_h = tree["m_SizeDelta"]["y"]
        tree["m_SizeDelta"]["x"] = w
        if h is not None:
            tree["m_SizeDelta"]["y"] = h
        o.save_typetree(tree)
        doc_done.append(rtpid)
        n_rect += 1
        print("  · 直指 Rect #%d w %.1f->%.1f h %.1f->%.1f" % (rtpid, old_w, w, old_h, (h if h is not None else old_h)))

    # 白名单清单（verify_build 用）：允许改动的 RectTransform 对象 + 无 CN 的 Text 对象
    # （如教程卡三框 #22684/#26149/#27588：m_Text 为空、无 refer 条目，b8 改的是字号字段）
    import json
    man = os.path.join(ROOT, "output", "game", "_b8_rect_objs.json")
    text_only = sorted(set(TEXT_EDITS) - set(RECT_EDITS))
    with io.open(man, "w", encoding="utf-8", newline="\n") as f:
        json.dump({FN: sorted(set(done_go.values()) | set(text_only) | set(doc_done) | set(OUTLINE_EDITS))},
                  f, ensure_ascii=False, indent=1)
    print("白名单清单 → %s（Rect %d + Text %d + 直指 %d + Outline %d）"
          % (man, len(done_go), len(text_only), len(doc_done), len(OUTLINE_EDITS)))

    out = env.file.save()
    with io.open(loc, "wb") as f:
        f.write(out)
    print("写出 %s：Text %d 个、Rect %d 个、Outline %d 个；文件 %d 字节"
          % (FN, n_text, n_rect, n_outline, len(out)))

    # ---- 3) 读回复核（重新打开保存后的文件）----
    env2 = UnityPy.load(loc)
    ok_t = 0
    ok_r = 0
    ok_o = 0
    for o in env2.objects:
        if o.path_id in TEXT_EDITS:
            _, f2 = CL.parse_obj(o.get_raw_data(), schema)
            fs, best = TEXT_EDITS[o.path_id][0], TEXT_EDITS[o.path_id][1]
            got = (f2["m_FontData"]["m_FontSize"], f2["m_FontData"]["m_BestFit"])
            if got != (fs, best):
                raise SystemExit("#%d 读回不符 %s" % (o.path_id, got))
            ok_t += 1
        elif o.path_id in OUTLINE_EDITS:
            _, f2 = CL.parse_obj(o.get_raw_data(), outline_schema)
            got = tuple(f2["m_EffectDistance"])
            if got != OUTLINE_EDITS[o.path_id]:
                raise SystemExit("#%d Outline 读回不符 %s" % (o.path_id, got))
            ok_o += 1
        elif o.path_id in done_go.values() or o.path_id in doc_done:
            t = o.read_typetree()
            if o.path_id in doc_done:
                w, h = DOC_RECTS[o.path_id]
            else:
                pid = [k for k, v in done_go.items() if v == o.path_id][0]
                w, h = RECT_EDITS[pid]
            if abs(t["m_SizeDelta"]["x"] - w) > 1e-3:
                raise SystemExit("RT 读回不符 #%d（x=%s）" % (o.path_id, t["m_SizeDelta"]["x"]))
            if h is not None and abs(t["m_SizeDelta"]["y"] - h) > 1e-3:
                raise SystemExit("RT 读回不符 #%d（y=%s）" % (o.path_id, t["m_SizeDelta"]["y"]))
            ok_r += 1
    if ok_t != len(TEXT_EDITS) or ok_r != len(done_go) + len(doc_done) or ok_o != len(OUTLINE_EDITS):
        raise SystemExit("复核计数不符 Text %d/%d Rect %d/%d Outline %d/%d"
                         % (ok_t, len(TEXT_EDITS), ok_r, len(done_go), ok_o, len(OUTLINE_EDITS)))
    print("读回复核通过（Text %d / Rect %d / Outline %d）" % (ok_t, ok_r, ok_o))


if __name__ == "__main__":
    main()
