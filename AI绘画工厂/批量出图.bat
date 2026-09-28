@echo off
title AI绘画工厂 - 批量出图
cd /d %~dp0Fooocus
set HF_MIRROR=https://hf-mirror.com
set HF_ENDPOINT=https://hf-mirror.com
set NO_PROXY=127.0.0.1,localhost
set no_proxy=127.0.0.1,localhost
echo ================================================
echo   AI绘画工厂 - 批量出图
echo   任务清单：批量提示词.txt（一行一条）
echo   正在运行，请勿关闭本窗口，完成后会提示
echo ================================================
.venv\Scripts\python.exe -u ..\批量出图.py
echo.
echo 批量结束，产物见 Fooocus\outputs\ 与 测试\产物\
pause
