@echo off
setlocal
cd /d "%~dp0"
title Caves of Lore 汉化文件生成
rem ============================================================
rem  Caves of Lore 汉化 · 工程包一键构建
rem  前置：把原版游戏放 ..\origin\（Caves of Lore.exe 与 Caves of Lore_Data\ 同级）
rem  本文件编码 GBK，勿另存为 UTF-8；勿加 chcp 65001。
rem ============================================================

where python >nul 2>nul
if errorlevel 1 goto NOPY

python -c "import UnityPy" >nul 2>nul
if errorlevel 1 (
  echo [提示] 缺少运行库，正在自动安装，需要联网，约 1 分钟...
  python -m pip install -r "..\requirements.txt"
  if errorlevel 1 goto PIPFAIL
)

if not exist "..\origin\Caves of Lore_Data\resources.assets" goto NOORIG

echo ============================================
echo   Caves of Lore 汉化文件生成
echo ============================================
echo.
echo   [1/4] 构建（refer 译文 -> 游戏文件 + 字体合并 + DLL 登记）
python "build_game.py"
if errorlevel 1 goto FAIL

echo   [2/4] 按钮贴图汉化（Sprite/Texture2D 重绘）
python "b7_fix.py"
if errorlevel 1 goto FAIL

echo   [3/4] 按钮文字排版统一（字号 / 文本框宽度）
python "b8_fontsize.py"
if errorlevel 1 goto FAIL

echo.
echo   [4/4] 产物校验（白名单 diff / 读回 / 存档类文件扫描）
python "verify_build.py"
if errorlevel 1 goto FAIL

echo.
echo  完成！产出在 output\game\loc_files\（搬运式整文件覆盖用）。
echo  打包两类发布包（产在 output 顶层）：python tools\pack.py
pause
goto :eof

:NOPY
echo [错误] 未找到 python，请先安装 Python 3.10+ 并勾选 Add to PATH。
pause
goto :eof

:PIPFAIL
echo [错误] 依赖安装失败，请检查网络后重试。
pause
goto :eof

:NOORIG
echo [错误] 在 ..\origin\ 里没有找到原版游戏（Caves of Lore_Data\resources.assets）。
echo        请把自己的原版游戏文件放入 origin\ 后再运行。
pause
goto :eof

:FAIL
echo.
echo ！！构建或校验失败，请看上方输出定位问题。
pause
goto :eof
