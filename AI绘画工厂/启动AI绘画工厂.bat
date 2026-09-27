@echo off
title AI绘画工厂 - 一句话批量出图
cd /d %~dp0Fooocus
rem HuggingFace 国内镜像（模型自动下载走这里）
set HF_MIRROR=https://hf-mirror.com
set HF_ENDPOINT=https://hf-mirror.com
rem 本机地址绕过系统代理（否则浏览器/自检会被 Clash 拦截）
set NO_PROXY=127.0.0.1,localhost
set no_proxy=127.0.0.1,localhost
echo ================================================
echo   AI绘画工厂 - 一句话批量出图（壁纸/头像/插画/封面）
echo   正在启动，浏览器将自动打开 http://127.0.0.1:8188
echo   首次启动需下载绘画模型（约7GB，走国内镜像，请耐心）
echo   使用完毕后：关闭本窗口即可停止程序
echo ================================================
.venv\Scripts\python.exe launch.py --port 8188
echo.
echo 程序已退出，如上方有报错信息请截图反馈
pause >nul
