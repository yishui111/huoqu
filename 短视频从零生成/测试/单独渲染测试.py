# -*- coding: utf-8 -*-
r"""
单独复现「最终成片渲染」环节（绕过文案/配音/拼接，直接用已有任务素材）
用途：端到端流水线在 generate_video 阶段静默退出时，用它快速定位是否为本环节问题。
运行：项目根目录下执行  .venv\Scripts\python.exe 测试\单独渲染测试.py
产物：测试\final-repro.mp4 与 控制台输出
"""
import faulthandler
import sys
from pathlib import Path

faulthandler.enable()  # C 层崩溃时把各线程 Python 栈打到 stderr，静默死亡可见

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loguru import logger

from app.models.schema import VideoParams
from app.services import video

TASK = ROOT / "storage" / "tasks" / "aed0ac53-3681-4216-831f-779abc99f9c6"
OUT = Path(__file__).resolve().parent / "final-repro.mp4"


def main() -> int:
    params = VideoParams(
        video_subject="渲染复现",
        video_aspect="9:16",
        subtitle_enabled=True,
        font_name="MicrosoftYaHeiBold.ttc",
        font_size=60,
        text_fore_color="#FFFFFF",
        stroke_color="#000000",
        stroke_width=1.5,
        subtitle_position="bottom",
        n_threads=2,
    )
    logger.info("开始单独渲染复现：{}", OUT.name)
    video.generate_video(
        video_path=str(TASK / "combined-1.mp4"),
        audio_path=str(TASK / "audio.mp3"),
        subtitle_path=str(TASK / "subtitle.srt"),
        output_file=str(OUT),
        params=params,
    )
    size = OUT.stat().st_size if OUT.exists() else 0
    print(f"渲染完成，输出大小: {size} 字节", flush=True)
    return 0 if size > 10000 else 1


if __name__ == "__main__":
    sys.exit(main())
