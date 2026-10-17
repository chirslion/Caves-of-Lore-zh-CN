# -*- coding: utf-8 -*-
"""Anode Heart 汉化工程 —— 字体合成。

游戏（Unity 2019.4）用旧版 UI 动态字体：Font 资源里内嵌 TTF 字节，运行时按需栅格化。
原字体全部是西文像素字体，没有汉字。

做法：把开源中文字体「融合像素字体 12px」（SIL OFL 1.1）里**用得到的字符**子集化、
按目标字体的数字高度等比缩放后，与目标字体合并成一个字体文件。
这样不依赖 Unity 的 fallback 机制，任何情况下都能正常显示中文；
西文字形仍来自原字体，观感不变。

缩放依据：
  * 融合像素字体汉字墨迹高 = 1100/1200 em、字宽 = 1.0 em（等宽方块字）；
  * 令汉字**墨迹高 = 目标字体 '0' 的墨迹高**、**墨迹底 = '0' 的墨迹底**——与
    阿拉伯数字严格等高同底（2026-10-11 用户定案「中文与英文/数字必须齐平」；
    2026-10-15 实机反馈「数字与中文高度不一致」后由 'A'/基线 0 改按 '0' 双对齐）。
    于是汉字字宽 = capHeight / (1100/1200) = 1.091 × capHeight。
    以对话字体 monogram-extended（capHeight 0.4375 em）为例，汉字字宽 ≈ 0.477 em，
    对话框宽 137 单位 / 字号 10 ⇒ 每行约 28.7 个汉字（排版断行取 28，仍有余量），
    配合 DialogueChunkifier 的 CharsPerLine=36 使用（见 README.md「对话换行机制」）。
"""

import io
import os
import tempfile

CJK_UPEM = 1200            # 融合像素字体的 unitsPerEm
CJK_HANZI_INK = 1100       # 汉字墨迹高（字体单位）
CJK_BASELINE_DROP = 100    # 字框相对基线的下沉量（字体单位）；动态测量失败时的回退值

# 只保留这些表参与合并：其余表（OS/2、name、post、GSUB…）一律用原字体的，
# 以免两套字体表结构不一致导致合并器报错。
MERGE_TABLES = ["glyf", "loca", "hmtx", "cmap", "head", "hhea", "maxp",
                "name", "OS/2", "post"]

# 这些表在像素字体里没有意义，且会干扰合并（Jackey 有竖排表）
DROP_FROM_DEST = ["vhea", "vmtx", "VORG", "GSUB", "GPOS", "GDEF", "mort", "kerx"]


def _require_fonttools():
    from fontTools.ttLib import TTFont  # noqa
    return TTFont


def load_cjk(path):
    TTFont = _require_fonttools()
    return TTFont(path, fontNumber=0)


def dest_cap_em(dest):
    """量出目标字体 '0' 的 (墨迹高, 墨迹底部)（相对 em），作为汉字大小/基线基准。

    2026-10-15（Caves of Lore 实机反馈「中文与数字混排高度不一致」）两处修正：
      ① 高度：此前以 'A' 为基准——不少字体数字高于大写（Born2bSportyV2 0.625 vs 0.562、
         Montserrat 0.724 vs 0.699）→ 汉字匹配 cap 后数字"冒头"。改为按 '0'
         （数字缺字回退数字组最大 → 大写组），中文与数字等高。
      ② 基线：个别字体（Adobe Dia）全部字形墨迹悬于基线上方（'0' 底 = +0.169 em）——
         汉字若压在 0 就会比数字低一大截。返回 '0' 的墨迹底部，供调用方把汉字
         底边对齐到数字底边。
    """
    from fontTools.pens.boundsPen import BoundsPen

    cmap = dest.getBestCmap()
    gs = dest.getGlyphSet()
    upem = dest["head"].unitsPerEm

    def ink(ch):
        g = cmap.get(ord(ch))
        if not g:
            return None
        bp = BoundsPen(gs)
        try:
            gs[g].draw(bp)
        except Exception:
            return None
        if not bp.bounds:
            return None
        return (bp.bounds[3] - bp.bounds[1]) / upem, bp.bounds[1] / upem

    r = ink("0")
    if r:
        return r
    best = None
    for group in ("0123456789", "AHB"):
        for ch in group:
            rr = ink(ch)
            if rr and (best is None or rr[0] > best[0]):
                best = rr
        if best:
            return best
    return 0.6, 0.0


def merge_cjk(dest_bytes, cjk_path, charset, log=None):
    """把 charset 里的字符合并进 dest_bytes 描述的字体，返回新字体字节。"""
    TTFont = _require_fonttools()
    from fontTools.merge import Merger
    from fontTools.subset import Subsetter, Options
    from fontTools.ttLib.scaleUpem import scale_upem

    tmp = tempfile.mkdtemp(prefix="anodefont_")

    # 1) 目标字体：去掉会干扰合并的表
    dest = TTFont(io.BytesIO(dest_bytes), fontNumber=0, recalcBBoxes=False,
                  recalcTimestamp=False)
    upem = dest["head"].unitsPerEm
    cap, dest_bottom = dest_cap_em(dest)
    if log:
        log("  基准 '0'：高 %.3f em / 底 %.3f em → 汉字同高同底" % (cap, dest_bottom))

    keys = [str(k) for k in dest.keys()]
    if any(t in keys for t in DROP_FROM_DEST):
        nd = TTFont()
        nd.sfntVersion = dest.sfntVersion
        nd.recalcTimestamp = False       # 否则重建时会打上当前时间戳
        nd.recalcBBoxes = False
        for t in dest.keys():
            if str(t) == "GlyphOrder" or str(t) in DROP_FROM_DEST:
                continue
            nd.tables[t] = dest[t]
        nd.setGlyphOrder(dest.getGlyphOrder())
        dest = nd

    # 裁掉目标字体**自带的 CJK 字形**。
    # Merger 对「同一 Unicode 在两个字体里都有」的规则是保留**第一个字体**
    # 的字形——不裁的话，合并进去的汉字会被 dest 自带的版本完全遮蔽。
    # 实测：Jackey 自带 12,204 个 CJK 字形（约 0.75 em、风格与西文不搭），
    # 导致界面中文一直显示的是它而不是融合像素字体（2026-10-11 定位）。
    #
    # 同步「接管」中文语境常用的 6 个半角标点（.,:;!?）：让它们也用中文字形
    # 渲染（融合像素的标点与汉字同风格；advance 与各西文字体基本一致——
    # ":" "!" "." 完全相同、其余差 <0.1 em）。解决「中文与标点画风不一致」
    # （2026-10-11 用户反馈；这些标点多来自代码里的 `label + ": " + value`
    # 拼接，资源文件层面改不到，字体层是唯一不新增替换文件的解法）。
    PUNCT_TAKEOVER = ".,:;!?"
    cmap_dest = dest.getBestCmap()
    # 记录原字体这 6 个码位的墨迹盒（下方归一化用；dest 很快会被 subset 裁掉它们）
    # 2026-10-16 实机：「?」帮助图标出框/偏小——接管的像素标点没跟宿主字体
    # 的悬挂基线（Adobe Dia 全字形悬于基线上 0.169em）对齐，也没按原墨迹缩放。
    orig_punct = {}
    glyf_dest = dest["glyf"] if "glyf" in dest else None
    if glyf_dest is not None:
        for ch in PUNCT_TAKEOVER:
            gname = cmap_dest.get(ord(ch))
            if not gname:
                continue
            gl = glyf_dest[gname]
            gl.recalcBounds(glyf_dest)
            if gl.numberOfContours:
                orig_punct[ord(ch)] = (gl.xMin, gl.yMin, gl.xMax, gl.yMax)
    keep = [c for c in cmap_dest
            if not (0x3400 <= c <= 0x9FFF or 0xF900 <= c <= 0xFAFF)
            and chr(c) not in PUNCT_TAKEOVER]
    if len(keep) < len(cmap_dest):
        opt = Options()
        opt.layout_features = []
        opt.notdef_outline = True
        opt.name_IDs = ["*"]
        opt.recalc_bounds = True
        ss = Subsetter(options=opt)
        ss.populate(unicodes=keep)
        ss.subset(dest)
        if log:
            log("  dest 自带 CJK 已裁掉：%d → %d 字符"
                % (len(cmap_dest), len(keep)))

    p_dest = os.path.join(tmp, "dest.ttf")
    dest.save(p_dest)

    # 2) 中文子集：缩放 → 只留必要表
    cjk = load_cjk(cjk_path)
    text = "".join(sorted(c for c in set(charset) if c))
    opt = Options()
    opt.layout_features = []
    opt.notdef_outline = True
    opt.recalc_bounds = True
    ss = Subsetter(options=opt)
    ss.populate(text=text)
    ss.subset(cjk)

    # ---- 把 CJK 字形对齐到拉丁基线 ----
    # 融合像素字体的汉字与全角标点按"字框"设计、整体比基线低 100/1200 em，
    # 而拉丁字母/数字贴着基线（[0, cap]）。不平移的话，混排时高亮的
    # 英文/数字"底边比中文高 0.06em"，看上去仍不齐（用户 2026-10-11 第四轮
    # 反馈：「高低一致了，但高亮英文/数字的最底部还是高一些」）。
    # 把 CJK 槽位（汉字 + 全角标点/形式）的字形统一上移，使满框汉字的
    # 底边落在基线上；ASCII 区不动（"," 的合法下沉等保持原设计）。
    from fontTools.pens.boundsPen import BoundsPen
    best = cjk.getBestCmap()
    glyf = cjk["glyf"]
    cjk_glyphs = {g for cp, g in best.items()
                  if (0x3400 <= cp <= 0x9FFF or 0xF900 <= cp <= 0xFAFF
                      or 0x3000 <= cp <= 0x303F or 0xFF00 <= cp <= 0xFFEF)}
    gs = cjk.getGlyphSet()
    lows = []
    for ch in "国目品田":
        gname = best.get(ord(ch))
        if gname and gname in glyf and not glyf[gname].isComposite():
            bp = BoundsPen(gs)
            gs[gname].draw(bp)
            if bp.bounds:
                lows.append(bp.bounds[1])
    drop = min(lows) if lows else -CJK_BASELINE_DROP
    if drop < 0:
        moved = 0
        for gname in cjk_glyphs:
            gl = glyf.get(gname)
            if gl is None:
                continue
            if gl.isComposite():
                for comp in gl.components:
                    comp.y += int(round(-drop))
            else:
                gl.coordinates.translate((0, -drop))
            gl.recalcBounds(glyf)
            moved += 1
        if log:
            log("  CJK 字形上移 %.0f/1200 em 贴基线（%d 个字形）" % (-drop, moved))

    # 先假装 upem 变小，再缩放到目标 upem，得到"汉字墨迹高 = cap"的效果：
    # 设 head.unitsPerEm = U（只改标称），则墨迹高 = CJK_HANZI_INK/U em；
    # 令其 = cap ⇒ U = CJK_HANZI_INK/cap（scale_upem 保持物理比例后不变）。
    # （2026-10-11 第二轮定案：此前取 1200/cap 即墨迹高 = 0.917×cap，
    #   比数字/大写矮 9%，高亮的英文/数字因此"冒头"。）
    cjk["head"].unitsPerEm = int(round(CJK_HANZI_INK / cap))
    scale_upem(cjk, upem)

    # ---- 底边对齐到目标字体的数字底（Adobe Dia 等字体全字形悬于基线之上）----
    if abs(dest_bottom) > 1e-6:
        dy = int(round(dest_bottom * upem))
        best2 = cjk.getBestCmap()
        glyf2 = cjk["glyf"]
        moved = 0
        for cp, gname in best2.items():
            if not (0x3400 <= cp <= 0x9FFF or 0xF900 <= cp <= 0xFAFF
                    or 0x3000 <= cp <= 0x303F or 0xFF00 <= cp <= 0xFFEF):
                continue
            gl = glyf2.get(gname)
            if gl is None:
                continue
            if gl.isComposite():
                for comp in gl.components:
                    comp.y += dy
            else:
                gl.coordinates.translate((0, dy))
            gl.recalcBounds(glyf2)
            moved += 1
        if log:
            log("  CJK 底边对齐数字底 %.3f em（上移 %d 单位，%d 字形）"
                % (dest_bottom, dy, moved))

    # ---- 接管的半角标点（.,:;!?）：按原字体该码位的墨迹盒归一化（位置+大小）----
    # 像素标点自带设计（多贴基线、墨迹略小）；只换风格、不改几何——
    # 底边对齐原字形的 yMin、高度缩放到原墨迹高，避免「?」这类在宿主字体
    # （Adobe Dia 悬基线）里掉到框底、比原版小一圈。
    best3 = cjk.getBestCmap()
    glyf3 = cjk["glyf"]
    fixed = 0
    for cp, ob in sorted(orig_punct.items()):
        gname = best3.get(cp)
        gl = glyf3.get(gname) if gname else None
        if gl is None:
            continue
        gl.recalcBounds(glyf3)
        cur_h = gl.yMax - gl.yMin
        if cur_h <= 0:
            continue
        s = (ob[3] - ob[1]) / float(cur_h)
        dx = ob[0] - s * gl.xMin
        dy2 = ob[1] - s * gl.yMin
        if gl.isComposite():
            for comp in gl.components:
                comp.x = int(round(comp.x * s + dx))
                comp.y = int(round(comp.y * s + dy2))
        else:
            # 注意：GlyphCoordinates.transform 只吃 2x2 矩阵（忽略平移分量！），
            # 平移必须另调 translate——否则字形只缩放、不归位。
            gl.coordinates.transform(((s, 0), (0, s)))
            gl.coordinates.translate((dx, dy2))
        gl.recalcBounds(glyf3)
        fixed += 1
    if fixed and log:
        log("  接管标点按原墨迹盒归一化：%d 个（%s）"
            % (fixed, "".join(chr(cp) for cp in sorted(orig_punct))))

    mini = TTFont()
    mini.sfntVersion = cjk.sfntVersion
    for t in MERGE_TABLES:
        if t in cjk:
            mini.tables[t] = cjk[t]
    mini.setGlyphOrder(cjk.getGlyphOrder())
    p_cjk = os.path.join(tmp, "cjk.ttf")
    mini.save(p_cjk)

    # 3) 合并
    out = Merger().merge([p_dest, p_cjk])

    # 4) 固定 head 时间戳：合并器会给 head 打上当前时间，导致每次构建产物不一致。
    out.recalcTimestamp = False
    buf = io.BytesIO()
    out.save(buf)
    return _pin_timestamp(buf.getvalue(), dest["head"].modified,
                          dest["head"].created)


def _checksum(data):
    """OpenType 表校验和（大端 32 位累加，末尾补零）。"""
    pad = (-len(data)) % 4
    data = data + b"\0" * pad
    total = 0
    for i in range(0, len(data), 4):
        total = (total + int.from_bytes(data[i:i + 4], "big")) & 0xFFFFFFFF
    return total


def _pin_timestamp(data, modified, created):
    """把 head 表的 created/modified 写死，并重算校验和，保证构建可复现。"""
    import struct

    data = bytearray(data)
    num = struct.unpack(">H", data[4:6])[0]
    head_off = None
    for i in range(num):
        o = 12 + 16 * i
        if data[o:o + 4] == b"head":
            head_off = struct.unpack(">I", data[o + 8:o + 12])[0]
            rec_off = o
            break
    if head_off is None:
        return bytes(data)

    data[head_off + 20:head_off + 28] = struct.pack(">Q", created)
    data[head_off + 28:head_off + 36] = struct.pack(">Q", modified)
    adj = head_off + 8
    data[adj:adj + 4] = b"\0\0\0\0"
    # head 表校验和（checkSumAdjustment 已置 0）
    head_len = struct.unpack(">I", data[rec_off + 12:rec_off + 16])[0]
    data[rec_off + 4:rec_off + 8] = struct.pack(
        ">I", _checksum(bytes(data[head_off:head_off + head_len])))
    # 全文件校验和
    data[adj:adj + 4] = struct.pack(
        ">I", (0xB1B0AFBA - _checksum(bytes(data))) & 0xFFFFFFFF)
    return bytes(data)


def charset_from_texts(texts):
    """收集所有译文里出现过的字符，外加常用标点与 ASCII。"""
    chars = set()
    for t in texts:
        chars.update(t or "")
    extra = (
        "　　，。、；：？！（）《》「」『』【】…—～·“”‘’％＋－＝／＼＃＠＆＊"
        "0123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        " !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
        "←↑→↓★☆♪♥●○◆◇■□▲△▼▽※→"
    )
    chars.update(extra)
    return chars
