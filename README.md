# Caves of Lore 简体中文汉化

《Caves of Lore》（Red Plume LLC / Steam / Unity 2022.3.62f3 **Mono**）的**玩家侧文本汉化**。
译文直接写回游戏资源文件，不需要任何 Mod 加载器。

> **当前状态（2026-10-17，v1.24b 第二十四轮术语修正版）**：全文 CN 完成；构建 / 校验 /
> 打包 / 冷缓存全绿；24 轮实机反馈问题已逐条修复闭环。**复测确认**：配方「任意食物」、
> 以太环属性说明（DAMAGE / EFFECTS / 元素伤害行）、NPC 对话「差事」按钮均正常 ✓。
> v1.24b：`+1 个效果与记忆` 统一为 `+1 效果与记忆`、召唤系「怪物生命加成」去掉硬换行；
> 新增玩家向 `术语说明.txt`（解释效果/记忆/法术持续时间等实际机制）。
> 修复历史与逐轮记录见开发工作区（本仓库之外的 `workspace/recon/翻译进度.md`）。

---

## 一、这个仓库是什么

**本目录（`output/`）就是 GitHub 仓库根**——本文件即仓库首页。仓库内容：

* **全部译文**（`refer/`，可人工编辑）、**生成/校验/打包链**（`tools/`）、所用字体（`fonts/`）、
  使用文档与依赖清单；
* **不包含**：游戏本体（`origin/` 是空占位，收件人自备），也不包含生成出来的汉化文件
  （`game/` 是空占位，由脚本在本机生成）；
* 顶层所有 **`*.zip` 都是发布件**（两类包，见下），随仓库提交。

`tools/pack.py` 产出两类包（直接产在本目录顶层，**不建交付目录、不保留解压副本**）：

* **玩家包**（`Caves of Lore 简中汉化包 v1.0（玩家版）.zip`）——给玩家**一键替换**：
  43 个搬运式游戏文件 + `安装.bat` / `卸载.bat` / `说明.txt`，不需要 Python；
* **工程包**（`Caves of Lore 简中汉化工程 v1.0（工程版）.zip`）——本仓库内容的压缩快照
  （`origin/` 与 `game/` 为空占位），解压后把原版游戏放进 `origin/`、双击
  `tools/生成汉化文件.bat` 即可逐字节复现全部产物。

> 开发工作区（逆向脚本 / 侦察报告 / 测试截图 / 反编译产物）不在本仓库内。

---

## 二、目录结构

```text
├─ README.md              本文件（仓库首页）
├─ refer/                 ★ 全部人工可编辑译文（翻译只改这里；格式见 refer/说明.txt）
│   ├─ 界面文本.json      UI Text（菜单/按钮/场景内固定文字）
│   ├─ 对话/              对话与阅读文本，按对白图分组：NN_组名.json
│   ├─ 数据文本/          技能/物品/任务/特质/实体/教程/成就/告示牌/闲聊
│   ├─ 参数文本待审.json  引用型/参数型文本
│   ├─ 对话节点参数.json  对话图节点参数集
│   ├─ DLL字面量.json     程序内字面量（含显示层补丁的映射口径）
│   ├─ 对象归属索引.tsv   每个界面文本对象的父节点链/字号/位置（排查归属用）
│   └─ 说明书文件
├─ tools/                 生成/校验/打包链
│   ├─ 生成汉化文件.bat   ★ 双击入口（4 步：build → b7 → b8 → verify）
│   ├─ build_game.py      按 refer/ 生成 game/loc_files（43 文件）+ 字体合并 + DLL 登记
│   ├─ b7_fix.py          按钮贴图重绘（像素字体原生 12px；图集格逐格 ROI）
│   ├─ b8_fontsize.py     按钮文字排版统一（固定字号 / 文本框展宽加高）
│   ├─ verify_build.py    产物校验（白名单 diff / CN 读回 / 存档类文件扫描）
│   ├─ collect_md5.py     全量 md5 清单（双轮可复现性对比）
│   ├─ pack.py            打包两类发布包（顶层 zip）+ 打包后清空 game/
│   ├─ cold_test.py       冷缓存验收（沙盒装/卸全流程）
│   ├─ col_lib.py / col_schemas.py  裸解析/重写字典（对象级字节保真）
│   ├─ font_tool.py       中文字体子集化与按 '0' 基准合并
│   ├─ game_config.py     路径 / 指纹配置
│   └─ prebuilt/          预编译补丁件（补丁版 DLL / CavesL10N / 词表；工程包复现所需）
├─ fonts/                 使用的中文字体与授权（融合像素字体，OFL）
├─ origin/                （空占位）原版游戏放这里；本仓库不含游戏本体
├─ game/                  （空占位）生成物目录；打包后清空，只进玩家包
├─ 汉化安装说明.txt        面向玩家的安装步骤
├─ 术语说明.txt            游戏内术语机制说明（效果/记忆/法术持续时间/词缀等）
├─ 汉化提示词.md           同类游戏汉化方法论（可复用）
├─ requirements.txt       Python 依赖（UnityPy 等）
└─ *.zip                  发布件（玩家包 / 工程包）
```

---

## 三、怎么用

### 玩家 / 只想拿到汉化

用顶层 **`Caves of Lore 简中汉化包 v1.0（玩家版）.zip`**：解压到游戏根目录
（或与其同级），双击 `安装.bat`（自动探测游戏目录、校验版本、逐文件备份为
`*.l10nbak`）；卸载双击 `卸载.bat`。详见包内 `说明.txt`。

### 接手维护 / 继续翻译

1. 安装依赖：`pip install -r requirements.txt`；
2. 把原版游戏（`Caves of Lore.exe` + `Caves of Lore_Data/` + `MonoBleedingEdge/`）放进 `origin/`；
3. 生成：双击 `tools/生成汉化文件.bat`
   （= `build_game.py` → `b7_fix.py` → `b8_fontsize.py` → `verify_build.py`）；
4. 改译文：只改 `refer/` 下的 **CN** 字段，**不要动 ID 与 EN**；改完回第 3 步重跑；
5. 打包：`python tools/pack.py`；冷缓存验收：`python tools/cold_test.py`。

游戏日后更新：把新版放进 `origin/` → 重新提取 EN 并掩护已有译文（按 ID / EN 救援）
→ 补译空 CN → 重跑构建。

---

## 四、汉化改动了游戏本体的哪些文件（43 个）

| 文件 | 改动 | 说明 |
|---|---|---|
| `Caves of Lore_Data/level*`（24 个） | 场景 UI 文本（m_Text）+ 排版修正 | 菜单/按钮/场景内固定文字；level0 另含字号与文本框调整 |
| `Caves of Lore_Data/resources.assets` | 数据/物品/技能/任务文本 + 贴图 + 字体 | 含对话图节点与 Database 文本；7 个字体并入 CJK 子集 |
| `Caves of Lore_Data/sharedassets*`（15 个） | 对话/数据/UI 文本 + 贴图 | sharedassets0 含标题/创建/服务按钮贴图重绘 |
| `Caves of Lore_Data/Managed/Assembly-CSharp.dll` | 568 处 ldstr 替换 + 多组 IL 显示层注入 | 运行时文本；枚举/后缀/敌种名/配方类型名等显示层翻译 |
| `Caves of Lore_Data/Managed/CavesL10N.dll`（新增） | 存档边界翻译 + 显示层包装 | 纯反射辅助程序集（netstandard2.0） |
| `Caves of Lore_Data/Managed/CavesL10N.table.txt`（新增） | 存档边界翻译表 | CN↔EN 双向（含只写别名与保留值标记） |

* 按钮贴图重绘：像素**内联回 .assets**（清 `m_StreamData`），**`.resS` 文件保持原版不动**；
* 字体：CJK 子集按 `'0'` 基准（高+底）合并进原字体本身，不新增字体文件；
* 存档兼容：中文只存在于"显示层"；游戏内存/存档始终英文原文，装与不装补丁的存档完全互通
  （实现：存档写出深克隆 中→英、读入 英→中回译）；
* 指纹（安装后核对）：见 `tools/game_config.py` 的 `CN_FINGERPRINTS`（与玩家包 `说明.txt` 同步）。

---

## 五、技术原理（简述）

* **文本载体**：全部在 MonoBehaviour/ScriptableObject 序列化数据里（无 TextAsset、无 i18n 框架）：
  对话图节点（XNode）、UI Text、各类 Holder 数据、程序内字面量。改写走自研裸解析/重写器
  （逐字段 4 字节对齐 + 对象尾补零；全类逐字节往返验证）。
* **运行时覆写**：UI 值标签由 DLL 在运行时写入（如 `screenStateText.text = "Fullscreen"`）——
  数据侧改了没用，须走 DLL 补丁（spec 驱动逐规则计数断言 + PCL 作用域扫描 + 全量 JIT 自检）。
* **显示层翻译**：枚举直出（材质/生物/伤害/武器类型）、品质词缀（`基名·词`）、敌种名等
  以注入包装方法实现；数据侧保持英文标识符（匹配机制所限）。
* **按钮美术字**：标题/创造/服务等按钮文字烘焙在贴图里 → 用游戏自身像素字体原生 12px 重绘。
* **字号一致性**：UI Text 的 BestFit 按宽+高双拟合 → 同型按钮统一固定字号 + 文本框展宽加高。
* **高亮**：对话高亮为运行时注入；译文保证高亮词三处同词且后跟全角标点。
* **已知限制**：少数机制性英文有意保留（按键名、输入谜题答案、部分人名等），详见译文说明。

---

## 六、已知问题 / 待办

开发工作区的 `test/测试项.md` 维护逐轮实测清单与已知接受项（不在本仓库内）。
遇到显示问题（方块字 / 错位 / 未翻译段落），请记录【场景 + 截图】反馈。

---

## 七、版权与许可

* **原游戏素材**：《Caves of Lore》及其全部素材（文本、图像、字体、音频等）版权归
  **Red Plume LLC**（开发 / 发行）所有。本工程仅提供文本本地化替换，与版权方无关联，
  不对游戏素材主张任何权利；汉化文件仅供个人学习交流使用，
  请在支持正版的前提下使用。
* **中文字体**：**融合像素字体（Fusion Pixel Font）12px 简体中文**
  （文件 `fonts/融合像素字体12px_zh_hans.ttf`），作者 **TakWolf**（https://takwolf.com），
  来源 https://github.com/TakWolf/fusion-pixel-font ，
  许可证 **SIL Open Font License 1.1**（授权原文见 `fonts/融合像素字体_OFL授权.txt`）。
  本工程只把所需字形子集合并进游戏自带字体（不新增字体文件）；字体原件随工程仓库提供。
* **其他第三方资源**：
  * **UnityPy**（https://github.com/K0lb3/UnityPy）— MIT License；
  * **Pillow**（https://python-pillow.org）— MIT-CMU License；
  * **fontTools**（https://github.com/fonttools/fonttools）— MIT License；
  * **Mono.Cecil**（https://github.com/jbevain/cecil）— MIT License
    （仅开发期用于生成补丁版 `Assembly-CSharp.dll`，不随玩家包分发）。

---

*本工程按 `BaseLine/` 汉化工程基线组织。*
