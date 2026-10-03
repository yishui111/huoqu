@echo off
title 关闭 AI短视频工厂
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8501" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
echo 已关闭 AI短视频工厂 (端口 8501)
ping -n 3 127.0.0.1 >nul
