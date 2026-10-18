# -*- coding: utf-8 -*-
"""第七轮修复 · 按钮贴图汉化（Sprite/Texture2D 上烘焙的英文标签 -> 重绘 CN）。

背景：标题菜单 / 角色创建 / 存档面板等大量按钮文字是**图片**（Texture2D 烘焙），
文本提取管线天然覆盖不到 → 实机反馈「按钮大部分没汉化」。本工具用游戏自身的
合并像素字体（NESCyrillic+CJK，字形风格与按钮美术一致）重绘这些贴图：

  1) 独立贴图：整个 Texture2D 即按钮（43 张，像素存于 sharedassets0.assets.resS）；
  2) 图集精灵：UI Atlas(#23) 内矩形（~25 个标签，如 NEW GAME/LOAD GAME/QUIT/…）。

写入策略（防 resS 膨胀）：把像素数据**内联**回 .assets（置 m_StreamData.path 空）
→ 不改 .resS 文件 → 交付文件清单不变（sa0/resources 已在列）。

流程：build_game 之后运行（后处理）：
  python build_game.py && python b7_fix.py
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "output", "tools"))
import game_config as C  # noqa: E402
import UnityPy  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FONT_PATH = os.path.join(ROOT, "output", "fonts", "融合像素字体12px_zh_hans.ttf")

# ---------------- 词条表 ----------------
# ('tex', 纹理 id, None, 译文) / ('atlas', 图集纹理 id, (x, y, w, h), 译文)
SA0 = "sharedassets0.assets"
RES = "resources.assets"
ENTRIES = [
    # —— 标题菜单（图集）——
    (SA0, "atlas", 23, (552, 141, 68, 36), "新游戏"),
    (SA0, "atlas", 23, (370, 260, 68, 36), "读取游戏"),
    (SA0, "atlas", 23, (693, 156, 68, 36), "退出"),
    (SA0, "atlas", 23, (0, 434, 68, 36), "继续"),
    (SA0, "atlas", 23, (833, 0, 68, 36), "跳过开场"),
    (SA0, "tex", 57, None, "偏好设置"),
    (SA0, "tex", 254, None, "制作名单"),
    (SA0, "tex", 181, None, "更新日志"),
    (RES, "tex", 134, None, "新游戏+"),
    # —— 角色创建（图集 68x32 + 独立）——
    (SA0, "atlas", 23, (833, 40, 68, 32), "能力"),
    (SA0, "tex", 402, None, "特质"),
    (SA0, "tex", 280, None, "种族"),
    (SA0, "tex", 285, None, "类型"),
    (SA0, "tex", 72, None, "随机"),
    (SA0, "tex", 155, None, "分配"),
    (SA0, "tex", 139, None, "重置"),
    (SA0, "tex", 32, None, "确定"),
    (SA0, "tex", 147, None, "躯干"),
    # —— 存档 / 对话框（图集 + 独立；浅色底深字）——
    (SA0, "atlas", 23, (693, 116, 68, 36), "保存游戏"),
    (SA0, "tex", 79, None, "保存"),
    (SA0, "tex", 64, None, "打开"),
    (SA0, "tex", 76, None, "新存档"),
    (SA0, "tex", 301, None, "是"),
    (SA0, "tex", 317, None, "否"),
    (SA0, "tex", 161, None, "导入"),
    (SA0, "tex", 172, None, "恢复备份"),
    (SA0, "atlas", 23, (552, 101, 68, 36), "命名"),
    # —— 拾取 / 查看（图集）——
    (SA0, "atlas", 23, (140, 348, 68, 36), "全部拿走"),
    (SA0, "atlas", 23, (230, 300, 68, 36), "查看"),
    (SA0, "atlas", 23, (793, 80, 68, 36), "阅读"),
    (SA0, "atlas", 23, (92, 258, 131, 34), "双手持握"),  # 第十轮：原 (90,260,68,36) 偏窄，
    # 原版 "TWO-HANDED" 横跨 131px 板（92-223），右段残影 ILD/ANDED 可见 → 按实测板界重绘
    # —— 第十轮全图集普查补漏（此前从未处理的格）——
    (SA0, "atlas", 23, (688, 80, 100, 40), "增加技能"),   # INCREASE SKILL（技能页大按钮板）
    (SA0, "atlas", 23, (0, 470, 68, 40), "模组"),          # MODS
    # 2026-10-16 第十三轮校定：真实格 = (0,390,100,44)——此前登记的 (0,402,…)
    # 纵向偏差 12 行（目测估计遗留），文字被贴到按钮可视区下缘、上缘遭裁；
    # 且 (0,402,100,44) 与上方邻格内容重叠（重绘曾误擦邻格像素，重建自 origin 恢复）。
    (SA0, "atlas", 23, (0, 390, 100, 44), "物品栏"),       # INVENTORY 页签（能力界面第 5 页签）
    (SA0, "atlas", 23, (552, 253, 68, 32), "拆分"),        # SPLIT（堆叠拆分，位于被动上方一格）
    (SA0, "atlas", 23, (212, 348, 68, 36), "停止"),
    (SA0, "atlas", 23, (284, 340, 68, 36), "完成"),
    # —— 露营 / 休息（图集 136 组）——
    (SA0, "atlas", 23, (693, 0, 136, 36), "停止休息"),
    (SA0, "atlas", 23, (693, 40, 136, 36), "休息到早晨"),
    (SA0, "atlas", 23, (230, 260, 136, 36), "休息到夜晚"),
    (SA0, "atlas", 23, (0, 358, 136, 36), "休息至痊愈"),
    # 露营月相按钮（独立 136×36 贴图：NEXT MOON ZENITH / NEXT MOON NADIR）
    (SA0, "tex", 67, None, "下次月临天顶"),
    (SA0, "tex", 69, None, "下次月临天底"),
    (SA0, "atlas", 23, (90, 300, 136, 20), "守夜"),
    (SA0, "atlas", 23, (90, 324, 136, 20), "照料伤员"),
    (SA0, "tex", 195, None, "结束露营"),
    (SA0, "tex", 132, None, "住宿天数"),
    # —— 商店 / 服务 / 物品 ——
    (SA0, "tex", 403, None, "买 / 卖"),
    (SA0, "tex", 355, None, "全部出售"),
    (SA0, "tex", 77, None, "服务"),
    (SA0, "tex", 222, None, "锻造"),
    (SA0, "tex", 199, None, "附魔"),
    (SA0, "tex", 178, None, "鉴定"),
    (SA0, "tex", 228, None, "磨砺"),
    (SA0, "tex", 281, None, "刻纹"),
    (SA0, "tex", 367, None, "邀请"),
    (SA0, "tex", 382, None, "遣散"),
    (SA0, "tex", 375, None, "增幅"),
    (SA0, "tex", 191, None, "报告问题"),
    (SA0, "tex", 342, None, "药水"),
    (SA0, "tex", 253, None, "升级"),
    (SA0, "tex", 232, None, "购买能力"),
    (SA0, "tex", 284, None, "购买特质"),
    (SA0, "tex", 298, None, "跳过"),
    # —— 任务书页「接受任务」签（金色问号 + ACCEPT 烘焙字）——
    # 专用重绘路径 redraw_accept()：保留羊皮纸纹理、按原文字宽度重绘「接受」。
    (SA0, "tex", 364, None, "接受"),
    # —— 任务筛选 / 知识菜单（图集 68x32 + 独立）——
    (SA0, "tex", 202, None, "全部"),
    (SA0, "tex", 348, None, "已完成"),
    (SA0, "tex", 256, None, "收集"),
    (SA0, "tex", 198, None, "讨伐"),
    (SA0, "tex", 210, None, "线索"),
    (SA0, "atlas", 23, (140, 388, 68, 32), "技能"),
    (SA0, "atlas", 23, (905, 0, 68, 32), "法术"),
    (SA0, "atlas", 23, (302, 300, 68, 32), "抗性"),
    (SA0, "atlas", 23, (374, 300, 68, 32), "属性"),
    (SA0, "atlas", 23, (284, 380, 68, 32), "兽典"),
    (SA0, "atlas", 23, (765, 120, 68, 32), "任务"),
    (SA0, "atlas", 23, (552, 181, 68, 32), "战斗"),
    (SA0, "atlas", 23, (552, 217, 68, 32), "被动"),
]

# 单条目的渲染覆盖（默认 NATIVE_SIZE=12）。键 = (fn, tid, rect)；rect=None 表示独立贴图。
# (SA0,181) 更新日志：17px 渲染墨迹 ~13.3 → ~43px@1080p，与「操作」（84 号≈43px）齐平。
# 游戏内暂停菜单三格（图集缩放 4.27 px/texel，12px 渲染约 47px）→ 10px 与同屏
# 文本/独立贴图按钮（~40px）统一（用户第七轮反馈「游戏内菜单字体大小不统一」）。
SIZE_OVERRIDE = {
    # 保存游戏/读取游戏/退出 三格 2026-10-16 由 10 回退为原生 12：
    # 10 非原生倍率在图集里发虚（第八轮「读取游戏等按钮模糊」），12px=4 字 48px 仍小于 68px 格宽。
    # 「更新日志」(#181) 2026-10-16 由 17px+AA 回退为原生 12px 二值：
    # 该贴图原版即像素字体 1:1 字稿（"CHANGELOG" 大写高 8 texels），显示放大 ≈3.2×；
    # 17px 渲染放大 1.7 倍 → 与文本「操作」(fs52≈27px) 永远对不齐。12px 原生 CN 墨迹
    # ≈9 texels ≈ 原版 8 texels，显示 ≈28px，与原版 27px 的配对一致。
    #
    # 「物品栏」页签格 (0,390,100,44)——第十三轮终版口径（2026-10-16 实机+截图双侧标定）：
    # 第十二轮 21px 仍"不一致"且顶部被裁。定位到两个叠因：
    #   ① 格坐标 y 偏差 12 行（(0,402)→(0,390)）：文字被贴到按钮可视区下缘、上缘裁切，
    #      且重绘区与上方邻格重叠（已随重建自 origin 恢复）；
    #   ② 尺寸：21px 渲染 → 屏上墨迹 ≈38px，而兄弟页签（68×32 格，12px 渲染）≈28px。
    #      按 44 格/32 格的显示缩放差（本按钮贴图缩放 ≈2.11 vs 兄弟 ≈2.88）反推：
    #      屏上 28px ↔ 格内墨迹 ≈13.3px ↔ 字号 ≈16px。
    # 第十四轮定稿：**原生 12px**（与兄弟页签同口径）。17px 属非原生网格重光栅化——
    # 像素字体在非原生字号下生成 2px 粗笔画 + 底行抗锯齿被阈值削薄（实机反馈
    # 「字变粗 / 下部被截断」）。实机同屏实测：本按钮屏上缩放（2.46）≈ 兄弟页签（2.55），
    # 原生 12px 即可同高（屏上 27 ↔ 28px），无需任何放大补偿。
    (SA0, 23, (0, 390, 100, 44)): 12,
}

# 超采样源字号（渲染源 → LANCZOS 降到 SIZE_OVERRIDE 目标字号后二值化）。
# 当前无条目：16px 超采样实测笔画仍断续（CJK 在非网格字号二值化必损）。
SS_OVERRIDE = {}

# 反向超采样：12px 原生掩码 → LANCZOS 放大到目标字号 → 阈值 60 二值化（均匀增粗）。
# 当前无条目。「增加技能」18px 版（第十九轮尝试）被第二十轮反馈否决——
# 「字体太大，而且有下划线（字形底部横笔画对齐的观感）、还不如上一版」→
# 回退 v1.18 的 12px 原生 + 整框锚点。
UP_OVERRIDE = {}
# 关闭二值化、灰度掩码贴图（软边 ≈ 字体渲染观感）——当前无条目（181 已回二值）。
AA_ENTRIES = set()
# 文字颜色覆盖（原文字色非"深色/浅色"常规时用）。任务书 ACCEPT 签走专用路径
# redraw_accept()（保纹理 + 放大重绘），不在此表。
COLOR_OVERRIDE = {}

# 文字区域限制（相对矩形；避开装饰图标）。默认按"内缩边框 + 全宽"自动检测。
ROI = {
    (SA0, 355): (22, 4, 124, 28),      # UI_SellAll：左侧金币图标
    (SA0, 403): (4, 4, 124, 28),       # BUY / SELL 正常
    (SA0, 232): (6, 2, 62, 30),        # BUY ABILITY 两行 -> 单行
    (SA0, 284): (6, 2, 62, 30),
    (SA0, 76): (6, 2, 62, 34),         # NEW SAVE 两行
    (SA0, 253): (6, 2, 62, 34),        # ADD LEVEL 两行
    (SA0, 402): (6, 2, 62, 30),
    (SA0, 280): (4, 2, 64, 18),        # SPECIES 小条
    (SA0, 285): (4, 2, 60, 18),
    (SA0, 147): (4, 2, 60, 18),
    (SA0, 23, (0, 390, 100, 44)): (6, 12, 94, 30),
    (SA0, 23, (688, 80, 100, 40)): (8, 8, 92, 34),
    # ↑ 「增加技能」按钮逐格 ROI：排除外框（同物品栏教训——清除区会把边框当墨迹擦平）；
    #   12px 原生 + 本 ROI 即 v1.18 版（第十九轮曾改 (15,13,90,33)+18px，第二十轮
    #   反馈「太大且有下划线观感」→ 回退至此）。
    # ↑ 物品栏页签逐格 ROI：排除板上边框线（top≈6/底≈42）——
    #   否则 text_bbox 会把边框当墨迹 → 清除区连带擦掉边框（第十二轮实机格子被擦平）。
    (RES, 134): (0, 0, 34, 36),        # 新游戏+（窄）
}


def bg_color(img):
    cols = img.getcolors(maxcolors=1 << 20) or []
    return max(cols)[1]


def text_bbox(img, roi=None, margin=3):
    """返回文字墨迹 bbox（排除边框与 roi 外区域）。"""
    w, h = img.size
    x0, y0, x1, y1 = roi if roi else (margin, margin, w - margin, h - margin)
    bg = bg_color(img)
    px = img.load()
    minx, miny, maxx, maxy = 1 << 30, 1 << 30, -1, -1
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = px[x, y][:3]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > 90:
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)
    if maxx < 0:
        return None, bg
    return (minx, miny, maxx, maxy), bg


def dominant_text_color(img, bbox, bg):
    box = img.crop((bbox[0], bbox[1], bbox[2] + 1, bbox[3] + 1))
    cols = box.getcolors(maxcolors=1 << 20) or []
    best, bestn = None, -1
    for n, c in cols:
        if abs(c[0] - bg[0]) + abs(c[1] - bg[1]) + abs(c[2] - bg[2]) > 90:
            if n > bestn:
                best, bestn = c, n
    return best or (255, 255, 255)


# 原生像素网格尺寸：直接用「融合像素字体12px」的**原始 TTF 以原生字号 12 渲染**
# （每个设计像素 1:1 落在图像像素上）→ 与按钮美术同风格的清晰像素字。
# （对照实验：经合并/缩放后的字体在任何字号都带上重采样模糊，故用原始字体。）
NATIVE_SIZE = 12
THRESHOLD = 100


def render_text_mask(text, size=NATIVE_SIZE, wrap=None, threshold=True, ss=None, up=None):
    # ss：超采样源字号（在原生网格的整数倍上渲染，再 LANCZOS 降采样到 size 后二值化）。
    # 非原生字号直渲时描边会 1px/2px 参差（「增加技能」16px 实测发毛）；2× 渲染
    # 再降采样可得到最接近像素网格的均匀笔画。
    # ★ 12px 原生路径逐字保留（历史 75 格全部按它标定，改动会整体漂移）；
    #   非原生字号/超采样走「按实际文本 bbox 排版」的修正路径——旧公式按
    #   bbox("国") 定行高 + 固定 y=2 起排，在 16px 下字形顶/底被画布裁掉
    #   （实机格出现「笔画断续+底行虚线」）。
    src = ss or size
    f = ImageFont.truetype(FONT_PATH, src)
    lines = text.split("\n") if wrap is None else wrap
    if src == NATIVE_SIZE and size == NATIVE_SIZE:
        # —— 原生 12px：历史公式（勿改）——
        tb = f.getbbox("国")
        line_h = tb[3] - tb[1] + 1
        wmax = 0
        for ln in lines:
            bb = f.getbbox(ln)
            wmax = max(wmax, bb[2] - bb[0])
        m = Image.new("L", (wmax + 4, line_h * len(lines) + 4), 0)
        dr = ImageDraw.Draw(m)
        for i, ln in enumerate(lines):
            bb = f.getbbox(ln)
            x = (wmax - (bb[2] - bb[0])) // 2 - bb[0]
            dr.text((x + 2, 2 + i * line_h), ln, font=f, fill=255)
    else:
        # —— 非原生字号：按实际文本 bbox 定画布与基线 ——
        bbs = [f.getbbox(ln) for ln in lines]
        top = min(b[1] for b in bbs)
        bot = max(b[3] for b in bbs)
        line_h = bot - top + 2
        wmax = max(b[2] - b[0] for b in bbs)
        m = Image.new("L", (wmax + 6, line_h * len(lines) + 6), 0)
        dr = ImageDraw.Draw(m)
        for i, (ln, bb) in enumerate(zip(lines, bbs)):
            x = 3 + (wmax - (bb[2] - bb[0])) // 2 - bb[0]
            dr.text((x, 3 + i * line_h - top), ln, font=f, fill=255)
    if ss:
        m = m.resize((max(1, round(m.width * size / ss)), max(1, round(m.height * size / ss))),
                     Image.LANCZOS)
    if up:
        # 反向超采样：12px 原生二值掩码 LANCZOS 放大到 up 字号，再以低阈值（60）二值化
        # → 笔画整体增粗 1px 且均匀（直渲 16px 因字形落点亚像素 → 笔画断续，实测弃用）。
        m = m.resize((max(1, round(m.width * up / size)), max(1, round(m.height * up / size))),
                     Image.LANCZOS)
        m = m.point(lambda v: 255 if v >= 60 else 0)
        bb0 = m.getbbox()
        return (m.crop(bb0), bb0[2] - bb0[0], bb0[3] - bb0[1], f) if bb0 else (None, 0, 0, f)
    if threshold:
        thr = max(THRESHOLD, 110) if ss else THRESHOLD
        m = m.point(lambda v: 255 if v >= thr else 0)
    bb = m.getbbox()
    if bb is None:
        return None, 0, 0, f
    return m.crop(bb), bb[2] - bb[0], bb[3] - bb[1], f


def render_into(img, roi, text, interior=None, size=NATIVE_SIZE, aa=False, ss=None, up=None,
                color=None):
    bbox, bg = text_bbox(img, roi)
    W, H = img.size
    ix0, iy0, ix1, iy1 = interior or (2, 2, W - 2, H - 2)
    if bbox is None:
        cx0, cy0, cx1, cy1 = ix0, iy0, ix1, iy1
        color = (255, 255, 255)
    else:
        cx0, cy0, cx1, cy1 = bbox
        if color is None:
            color = dominant_text_color(img, bbox, bg)
    # RGBA 图必须保住透明通道（曾因 convert('RGB') 把整张图集的 alpha 变实心，
    # 图集内所有透明图标/圆角变白块——2026-10-16 实机定位）
    if img.mode == "RGBA":
        color = tuple(color[:3]) + (255,)
        bg = tuple(bg[:3]) + (255,)
    # 先单行，再两行（窄按钮，如 34px 的 新游戏+）
    mask, mw, mh, f = render_text_mask(text, size=size, threshold=not aa, ss=ss, up=up)
    if mw > (ix1 - ix0) and len(text) > 2:
        half = (len(text) + 1) // 2
        wrap = [text[:half], text[half:]]
        mask, mw, mh, f = render_text_mask(text, size=size, wrap=wrap, threshold=not aa, ss=ss, up=up)
    if mask is None or mw > (ix1 - ix0) or mh > (iy1 - iy0):
        return False
    # 目标框：以原英文文字块的几何中心为锚（图标区已被 roi 排除）
    tx = cx0 + ((cx1 - cx0 + 1) - mw) // 2
    ty = cy0 + ((cy1 - cy0 + 1) - mh) // 2
    tx = max(ix0, min(tx, ix1 - mw))
    ty = max(iy0, min(ty, iy1 - mh))
    # 清除区 = 原文字块 ∪ 新文字框（+1 膨胀），防残留碎片
    ux0 = max(ix0, min(cx0, tx) - 1)
    uy0 = max(iy0, min(cy0, ty) - 1)
    ux1 = min(ix1, max(cx1, tx + mw - 1) + 1)
    uy1 = min(iy1, max(cy1, ty + mh - 1) + 1)
    dr = ImageDraw.Draw(img)
    dr.rectangle((ux0, uy0, ux1, uy1), fill=bg)
    img.paste(color, (tx, ty), mask)
    return True


# ---------------- 任务书「接受」签专用重绘 ----------------
# 原版：128×128 羊皮纸 + 金色问号 + 「ACCEPT」紫色像素字（左对齐、宽约 69px、高 11px）。
# 通用 render_into 会把整块文字区擦成纯色矩形 → 羊皮纸纹理被抹平，中文小字看起来
# 像「另贴的一层」（2026-10-18 实机反馈）。专用路径：
#   1) 只把原文字紫色像素按邻域中值补成羊皮纸（保留纹理）；
#   2) 「接  受」用 12px 像素字渲染后 ×2 NEAREST（两个空格 ≈ 原 ACCEPT 宽度 69px），
#      左对齐位置与原文字一致（x=16），保留下方整块羊皮纸的「一体」观感。
ACCEPT_PID = 364
ACCEPT_ROI = (8, 78, 120, 114)
ACCEPT_COLOR = (102, 45, 99)
ACCEPT_TEXT_XY = (16, 80)


def _color_near(c, t, tol=12):
    return abs(c[0] - t[0]) <= tol and abs(c[1] - t[1]) <= tol and abs(c[2] - t[2]) <= tol


def redraw_accept(img):
    x0, y0, x1, y1 = ACCEPT_ROI
    px = img.load()
    mask = set()
    for y in range(y0, y1):
        for x in range(x0, x1):
            if _color_near(px[x, y][:3], ACCEPT_COLOR):
                mask.add((x, y))
    if not mask:
        return False
    # 邻域中值补背景：用原图中未遮像素，逐通道取中值（保留纸张纹理，不做矩形平涂）
    src = img.copy()
    sp = src.load()
    for (x, y) in sorted(mask):
        found = []
        for rad in range(1, 10):
            for yy in range(max(y0, y - rad), min(y1, y + rad + 1)):
                for xx in range(max(x0, x - rad), min(x1, x + rad + 1)):
                    if (xx, yy) not in mask:
                        found.append(sp[xx, yy][:3])
            if len(found) >= 12:
                break
        if found:
            med = tuple(sorted(v[i] for v in found)[len(found) // 2] for i in range(3))
            px[x, y] = med + (px[x, y][3],)
    # 2x 像素字：12px 原生掩码 ×2 NEAREST，宽度接近原 ACCEPT（69px）
    m, mw, mh, _ = render_text_mask("接  受", size=NATIVE_SIZE)
    if m is None:
        return False
    m = m.resize((mw * 2, mh * 2), Image.NEAREST)
    tx, ty = ACCEPT_TEXT_XY
    if tx + m.width > img.width or ty + m.height > img.height:
        return False
    for yy in range(m.height):
        for xx in range(m.width):
            if m.getpixel((xx, yy)) > 0:
                px[tx + xx, ty + yy] = ACCEPT_COLOR + (255,)
    return True


def main():
    # UnityPy 解析纹理像素（.resS 流式数据）按 CWD 相对路径查找 —— 切到原版数据目录。
    os.chdir(os.path.join(C.ORIGIN_DIR, C.DATA_SUB))
    loc = os.path.join(ROOT, "output", "game", "loc_files", C.DATA_SUB)
    by_file = {}
    for (fn, kind, tid, rect, cn) in ENTRIES:
        by_file.setdefault(fn, []).append((kind, tid, rect, cn))

    total = fail = 0
    for fn, items in by_file.items():
        path = os.path.join(loc, fn)
        env = UnityPy.load(path)
        objs = {o.path_id: o for o in env.objects}
        # UnityPy 1.25.3 保存路径坑：data=None 的对象在 save 时经共享 reader 重读，
        # 本会话下会读出空数据（实测字体对象被写成 0 字节）。预缓存全部 raw 规避。
        for o in env.objects:
            if getattr(o, "data", None) is None:
                o.data = o.get_raw_data()
        # 先做独立贴图
        for kind, tid, rect, cn in items:
            if kind != "tex":
                continue
            o = objs.get(tid)
            if o is None or o.type.name != "Texture2D":
                print("！缺纹理 %s#%d (%s)" % (fn, tid, cn)); fail += 1; continue
            d = o.read()
            img = d.image.convert("RGBA")
            if (fn, tid) == (SA0, ACCEPT_PID):
                ok = redraw_accept(img)
            else:
                ok = render_into(img, ROI.get((fn, tid)), cn,
                                 size=SIZE_OVERRIDE.get((fn, tid, None), NATIVE_SIZE),
                                 aa=(fn, tid, None) in AA_ENTRIES,
                                 ss=SS_OVERRIDE.get((fn, tid, None)),
                                 up=UP_OVERRIDE.get((fn, tid, None)),
                                 color=COLOR_OVERRIDE.get((fn, tid, None)))
            total += 1
            if not ok:
                print("！重绘失败 %s#%d (%s)" % (fn, tid, cn)); fail += 1; continue
            d.image = img
            sd = getattr(d, "m_StreamData", None)
            if sd is not None:
                sd.path = ""
                sd.offset = 0
                sd.size = 0
            d.save()
        # 图集
        atlas_items = [it for it in items if it[0] == "atlas"]
        if atlas_items:
            cache = {}
            for kind, tid, rect, cn in atlas_items:
                o = objs.get(tid)
                if o is None or o.type.name != "Texture2D":
                    print("！缺图集 %s#%d" % (fn, tid)); fail += 1; continue
                if tid not in cache:
                    d = o.read()
                    cache[tid] = [d, d.image.convert("RGBA")]
                d, img = cache[tid]
                x, y, w, h = rect
                # Unity 纹理 Y 轴翻转
                x0, y0 = x, img.height - y - h
                cell = img.crop((x0, y0, x0 + w, y0 + h))
                ok = render_into(cell, ROI.get((fn, tid, rect)) or ROI.get((fn, tid)), cn,
                                 size=SIZE_OVERRIDE.get((fn, tid, rect), NATIVE_SIZE),
                                 aa=(fn, tid, rect) in AA_ENTRIES,
                                 ss=SS_OVERRIDE.get((fn, tid, rect)),
                                 up=UP_OVERRIDE.get((fn, tid, rect)),
                                 color=COLOR_OVERRIDE.get((fn, tid, rect)))
                total += 1
                if not ok:
                    print("！重绘失败 %s#%d rect=%r (%s)" % (fn, tid, rect, cn)); fail += 1; continue
                img.paste(cell, (x0, y0))
            for tid, (d, img) in cache.items():
                d.image = img
                sd = getattr(d, "m_StreamData", None)
                if sd is not None:
                    sd.path = ""
                    sd.offset = 0
                    sd.size = 0
                d.save()
        with io.open(path, "wb") as fo:
            fo.write(env.file.save())
        print("写出 %s（%d 项）" % (fn, len(items)))
        del env
    print("重绘 %d 项；失败 %d" % (total, fail))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
