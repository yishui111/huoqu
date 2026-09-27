@echo off
title 关闭 FunClip
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8315" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
echo 已关闭 FunClip (端口 8315)
ping -n 3 127.0.0.1 >nul
