@echo off
cd /d "%~dp0"
title FunClip REST 接口 (8335)
echo 接口: http://127.0.0.1:8335/docs   （文档见 ..\接口文档.md）
.venv\Scripts\python.exe api_server.py
pause
