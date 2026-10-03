@echo off
title 关闭 FunClip
rem 按端口精准杀进程：WebUI(8315) + REST 接口服务(8335)，不误伤其他 Python 程序
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8315" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8335" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
echo 已关闭 FunClip (WebUI 8315 + 接口服务 8335)
ping -n 3 127.0.0.1 >nul
