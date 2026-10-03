# -*- coding: utf-8 -*-
"""
端到端批量出片测试（可反复运行）
流程：输入主题 → 本地 Ollama 大模型(qwen2.5:3b)写文案 → edge-tts 配音
      → 使用 storage/local_videos 里的本地素材 → 自动字幕 → 批量输出 2 条竖屏视频
运行：双击本文件关联的 python，或命令行 .venv\\Scripts\\python.exe 测试批量出片.py
结果：视频输出在 storage/tasks/<任务ID>/final-*.mp4，日志在 测试运行日志.txt
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
LOG = ROOT / "测试运行日志.txt"

CMD = [
    str(ROOT / ".venv" / "Scripts" / "python.exe"),
    str(ROOT / "cli.py"),
    "--video-subject", "为什么猫咪总在半夜突然跑酷？3个冷知识让你笑出声",
    "--video-language", "zh-CN",
    "--video-source", "local",
    "--video-materials", "storage/local_videos/素材A.mp4,storage/local_videos/素材B.mp4,storage/local_videos/素材C.mp4",
    "--video-aspect", "9:16",
    "--video-clip-duration", "3",
    "--video-count", "2",
    "--subtitle-enabled",
]

def main():
    print("开始端到端批量测试（2条视频），请耐心等待…")
    t0 = time.time()
    proc = subprocess.run(CMD, cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    cost = time.time() - t0
    with open(LOG, "w", encoding="utf-8") as f:
        f.write(proc.stdout)
        if proc.stderr:
            f.write("\n===== STDERR =====\n" + proc.stderr)

    out = proc.stdout or ""
    tail = out[-3000:]
    print(tail)
    ok = proc.returncode == 0 and '"succeeded": 2' in out.replace(" ", "")
    videos = list((ROOT / "storage" / "tasks").glob("*/final-*.mp4"))
    print(f"\n退出码: {proc.returncode}，耗时 {cost:.0f} 秒")
    print(f"生成的成片文件: {[v.name for v in videos]}")
    sys.exit(0 if (ok or videos) else 1)

if __name__ == "__main__":
    main()
