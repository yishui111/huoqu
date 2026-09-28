@echo off
cd /d "%~dp0"
title AI绘画工厂 REST 接口 (8189)
echo 接口: http://127.0.0.1:8189/api/health   （文档见 ..\接口文档.md）
echo 注意: 生成走 Fooocus venv 子进程；本机 torch 段错误期间任务会返回 error
python api_server.py
pause
