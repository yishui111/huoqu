@echo off
title MoneyPrinterTurbo - AI短视频工厂
cd /d %~dp0
set PYTHONPATH=%CD%
set HF_ENDPOINT=https://hf-mirror.com
echo ================================================
echo   MoneyPrinterTurbo - AI 一键批量生成短视频
echo ================================================
rem 确保本地大模型服务 Ollama 已启动（AI写文案依赖它）
netstat -ano | findstr ":11434" | findstr "LISTENING" >nul 2>&1 || (
    echo 正在启动本地大模型服务 Ollama ...
    start "" "C:\Users\dapanji\AppData\Local\Programs\Ollama\ollama app.exe"
    ping -n 6 127.0.0.1 >nul
)
echo   正在启动 WebUI，浏览器将自动打开 http://127.0.0.1:8501
echo   使用完毕后：关闭本窗口即可停止程序
echo ================================================
.venv\Scripts\python.exe -m streamlit run webui\Main.py --server.address=127.0.0.1 --server.port=8501 --browser.gatherUsageStats=False --client.toolbarMode=minimal --server.showEmailPrompt=False --logger.hideWelcomeMessage=True
echo.
echo 程序已退出，如上方有报错信息请截图反馈
pause >nul
