# -*- coding: utf-8 -*-
"""测试01：运行环境与依赖 —— venv、核心包、ffmpeg、项目关键文件、全部脚本可编译。"""
import os
import py_compile
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 公共库 import ROOT, Tester, run  # noqa: E402

t = Tester("test_01_环境与依赖")

# ---------- Python 环境 ----------
t.group("Python环境")
t.true("使用项目内 venv 的 Python", ".venv" in sys.executable.lower(),
       f"sys.executable={sys.executable}")
t.true("Python 版本 >= 3.8", sys.version_info >= (3, 8),
       f"{sys.version.split()[0]}")
t.eq("Python 主版本为 3.10（与部署时一致）", sys.version_info[:2], (3, 10))

# ---------- 核心依赖可导入 ----------
t.group("核心依赖")
for mod in ["funasr", "gradio", "moviepy.editor", "librosa", "soundfile",
            "PIL", "fastapi", "uvicorn", "litellm", "httpx", "numpy"]:
    try:
        __import__(mod)
        t.true(f"可导入 {mod}", True)
    except Exception as exc:  # noqa: BLE001
        t.true(f"可导入 {mod}", False, f"{type(exc).__name__}: {exc}")

import gradio  # noqa: E402
t.true("gradio 为部署时验证过的 4.44.x", gradio.__version__.startswith("4.44"),
       gradio.__version__)

# ---------- 外部工具 ----------
t.group("外部工具")
t.true("ffmpeg 在 PATH", shutil.which("ffmpeg") is not None)
res = run(["ffmpeg", "-version"])
t.true("ffmpeg 可执行", res.returncode == 0 and "ffmpeg version" in res.stdout,
       res.stderr[:120])

# ---------- 项目关键文件 ----------
t.group("项目关键文件")
for rel in ["font/STHeitiMedium.ttc", "funclip/utils/theme.json",
            "funclip/videoclipper.py", "funclip/launch.py",
            "funclip/subtitle_renderer.py", "funclip/utils/trans_utils.py",
            "funclip/utils/subtitle_utils.py", "api_server.py",
            "批量切片.py", "启动FunClip.bat", "关闭FunClip.bat",
            "启动接口服务.bat", "接口文档.md", "使用说明.md",
            os.path.join("测试", "制作测试素材.py"),
            os.path.join("测试", "上游遗留", "说明.md")]:
    t.true(f"存在 {rel}", os.path.isfile(os.path.join(ROOT, rel)))

# gradio 4.44 + pydantic v2 的布尔 schema 兼容补丁（部署时打入 venv）
t.group("venv补丁")
try:
    from gradio_client import utils as gutils
    ok = True
    try:
        gutils.json_schema_to_python_type({"type": "boolean"})
    except Exception as exc:  # noqa: BLE001
        ok = False
        patch_hint = f"{type(exc).__name__}: {exc}"
    t.true("gradio_client 布尔 schema 解析不崩（启动页面的关键补丁）", ok,
           "" if ok else patch_hint)
except Exception as exc:  # noqa: BLE001
    t.true("gradio_client 布尔 schema 解析不崩（启动页面的关键补丁）", False,
           f"{type(exc).__name__}: {exc}")

# ---------- 全部项目脚本可编译 ----------
t.group("脚本语法")
targets = []
for sub in ["", "funclip", os.path.join("funclip", "llm"),
            os.path.join("funclip", "utils"), "测试"]:
    d = os.path.join(ROOT, sub) if sub else ROOT
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".py") and not fn.startswith("__pycache__"):
            targets.append(os.path.join(d, fn))
for path in targets:
    rel = os.path.relpath(path, ROOT)
    try:
        py_compile.compile(path, doraise=True)
        t.true(f"语法编译通过 {rel}", True)
    except py_compile.PyCompileError as exc:
        t.true(f"语法编译通过 {rel}", False, str(exc)[:200])

sys.exit(t.finish())
