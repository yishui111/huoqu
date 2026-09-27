@echo off
title FunClip - AI视频切片工厂
cd /d %~dp0
rem 确保本地大模型服务 Ollama 已启动（AI选高光片段依赖它）
netstat -ano | findstr ":11434" | findstr "LISTENING" >nul 2>&1 || (
    echo 正在启动本地大模型服务 Ollama ...
    start "" "C:\Users\dapanji\AppData\Local\Programs\Ollama\ollama app.exe"
    ping -n 6 127.0.0.1 >nul
)
rem 本地大模型接入：litellm 指向本机 Ollama（界面模型选 litellm/ollama/qwen2.5:3b）
set LITELLM_API_BASE=http://127.0.0.1:11434
rem 本机地址绕过系统代理（否则 gradio 自检会被代理拦下而启动失败）
set NO_PROXY=127.0.0.1,localhost
set no_proxy=127.0.0.1,localhost
rem ASR 模型缓存放在项目内，方便管理
set MODELSCOPE_CACHE=%CD%\model_cache
echo ================================================
echo   FunClip - AI 视频切片工厂（长视频一键出切片）
echo   正在启动，浏览器将自动打开 http://127.0.0.1:8315
echo   首次启动需下载识别模型（约1.5GB），请耐心等待
echo   使用完毕后：关闭本窗口即可停止程序
echo ================================================
rem 注意：必须从项目根目录启动（launch.py 用相对路径读主题文件）
.venv\Scripts\python.exe funclip\launch.py --port 8315
echo.
echo 程序已退出，如上方有报错信息请截图反馈
pause >nul
