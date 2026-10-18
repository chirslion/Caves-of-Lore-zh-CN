# -*- coding: utf-8 -*-
"""地图站点羊皮纸标签汉化（resources.assets 内烘焙文字重绘）。

背景：世界地图上的站点图标（UI_Parchment_*）是 384x128 的整张 Texture2D，
英文站名（TAILOR / ALCHEMIST / …）烘焙在像素画里，文本管线覆盖不到。
本脚本按与 b7 相同的「像素字体原生 12px 重绘」路线，先把原文字像素擦成
背景色（深色带 / 纸张），再用游戏同款融合像素字体写中文：
  · 上方小字：12px，浅灰（类别/营业内容）
  · 下方大字：12px ×2 NEAREST（约等于原像素字高度）

前置：build_game.py 之后运行（读 output/game/loc_files 的产物）。
输出：修改 resources.assets，并写白名单清单 output/game/_b9_tex_objs.json
      （verify_build.py 用）。
"""
import io
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont
import UnityPy

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "output", "tools"))
import game_config as C  # noqa: E402

FONT = os.path.join(ROOT, "output", "fonts", "融合像素字体12px_zh_hans.ttf")
FN = "resources.assets"

BAND = (83, 74, 65, 255)      # 深色带背景
PAPER = (255, 235, 189, 255)  # 纸张背景

# (path_id, 英文名, 小字中文（1~2 行）, 大字中文, 小字起始 y, 大字起始 y, 大字擦除下界)
LABELS = [
    (63,   "UI_Parchment_Tailor",    ["衣物"],              "裁缝",       18, 55, 96),
    (65,   "UI_Parchment_Butcher",   ["食物"],              "屠夫",       18, 55, 96),
    (200,  "UI_Parchment_Trainer",   ["武器训练"],          "武器训练师", 18, 50, 106),
    (441,  "UI_Parchment_Herbalist", ["草药/药水"],         "草药师",     18, 55, 96),
    (482,  "UI_Parchment_Enchanter", ["法球/法杖", "附魔"], "附魔师",     10, 55, 96),
    (524,  "UI_Parchment_Alchemist", ["药剂酿造"],          "炼金师",     18, 55, 96),
    (538,  "UI_Parchment_Library",   ["遗忘的藏书馆"],      "图书馆",     18, 55, 96),
    (544,  "UI_Parchment_Fletcher",  ["弓/斧"],             "制箭师",     18, 55, 96),
    (646,  "UI_Parchment_Inn",       ["睡眠"],              "旅店",       18, 55, 96),
    (651,  "UI_Parchment_Smith",     ["武器/护甲"],         "铁匠",       18, 55, 96),
    (667,  "UI_Parchment_TownHall",  ["食物/饮品"],         "镇公所",     18, 55, 96),
]


def text_img(text, px, color, scale=1):
    font = ImageFont.truetype(FONT, px)
    tmp = Image.new("RGBA", (512, 64), (0, 0, 0, 0))
    dr = ImageDraw.Draw(tmp)
    bb = dr.textbbox((0, 0), text, font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    out = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0))
    dr = ImageDraw.Draw(out)
    dr.text((1 - bb[0], 1 - bb[1]), text, font=font, fill=color)
    if scale != 1:
        out = out.resize((out.width * scale, out.height * scale), Image.NEAREST)
    return out


def redraw(img, small_lines, big_cn, small_y0, big_y0, big_y1):
    p = img.load()
    # 1) 擦小字：灰色像素（207 灰字；带底色不是灰、纸张不是灰）→带底。
    #    Enchanter 的第二行小字延伸到 y≈41（仍在深色带内）。
    for y in range(small_y0, 43):
        for x in range(40, 336):
            r, g, b, a = p[x, y]
            if (a > 0 and 120 <= r <= 235
                    and abs(r - g) <= 12 and abs(g - b) <= 12):
                p[x, y] = BAND
    # 2) 擦大字：纸张区（深色像素→纸底色）；Trainer 的两行大字延伸到 y≈104
    for y in range(big_y0, big_y1):
        for x in range(112, 372):
            r, g, b, a = p[x, y]
            if a > 0 and max(r, g, b) < 100:
                p[x, y] = PAPER

    # 3) 写小字（12px，浅灰；最多两行）
    # 单行时居中于深色带（原版英文小字偏下，中文单行会显得「掉在带子底部」；
    # 2026-10-18 反馈「单行不如双行、不在空白中央」→ 单行上移居中）。
    ys = [16] if len(small_lines) == 1 else [7, 23]
    for text, y in zip(small_lines, ys):
        s = text_img(text, 12, (200, 200, 200))
        img.alpha_composite(s, ((108 + 342) // 2 - s.width // 2, y))
    # 4) 写大字（12px ×2，垂直居中于纸张空白区 44..122——不再跟着原英文的
    #    big_y0/big_y1 走；原英文偏上，中文单行沿用会显得不在空白中央）。
    b = text_img(big_cn, 12, (0, 0, 0), scale=2)
    paper_y0, paper_y1 = 44, 122
    img.alpha_composite(b, ((112 + 372) // 2 - b.width // 2,
                            paper_y0 + (paper_y1 - paper_y0 - b.height) // 2))


def main():
    loc = os.path.join(C.LOC_FILES, C.DATA_SUB, FN)
    if not os.path.exists(loc):
        raise SystemExit("未找到构建产物：%s" % loc)
    # 纹理像素按 resS 相对路径读取 —— 与 b7 相同，切到原版数据目录
    os.chdir(os.path.join(C.ORIGIN_DIR, C.DATA_SUB))
    env = UnityPy.load(loc)
    objs = {o.path_id: o for o in env.objects}
    for o in env.objects:
        if getattr(o, "data", None) is None:
            o.data = o.get_raw_data()

    changed = []
    for pid, name, small_lines, big_cn, small_y0, big_y0, big_y1 in LABELS:
        o = objs.get(pid)
        if o is None or o.type.name != "Texture2D":
            raise SystemExit("缺少纹理 #%d（%s）" % (pid, name))
        d = o.read()
        if getattr(d, "m_Name", "") != name:
            raise SystemExit("#%d 名不符：%r != %r" % (pid, getattr(d, "m_Name", ""), name))
        img = d.image.convert("RGBA")
        if img.size != (384, 128):
            raise SystemExit("#%d 尺寸异常：%r" % (pid, img.size))
        redraw(img, small_lines, big_cn, small_y0, big_y0, big_y1)
        d.image = img
        sd = getattr(d, "m_StreamData", None)
        if sd is not None:
            sd.path = ""
            sd.offset = 0
            sd.size = 0
        d.save()
        changed.append(pid)
        print("  · %-28s %s / %s" % (name, "/".join(small_lines), big_cn))

    out = env.file.save()
    with io.open(loc, "wb") as f:
        f.write(out)
    man = os.path.join(ROOT, "output", "game", "_b9_tex_objs.json")
    with io.open(man, "w", encoding="utf-8", newline="\n") as f:
        json.dump({FN: changed}, f, ensure_ascii=False, indent=1)
    print("地图标签：%d 张；写出 %s（%d 字节）；白名单 → %s"
          % (len(changed), FN, len(out), man))


if __name__ == "__main__":
    main()
