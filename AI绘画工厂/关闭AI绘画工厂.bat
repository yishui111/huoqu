@echo off
title 关闭 AI绘画工厂
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8188" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
echo 已关闭 AI绘画工厂 (端口 8188)
ping -n 3 127.0.0.1 >nul
