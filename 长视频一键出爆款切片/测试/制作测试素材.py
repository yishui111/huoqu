# -*- coding: utf-8 -*-
"""
制作 FunClip 测试用的「长视频」素材：edge-tts 配音 + 渐变画面。
运行：用装了 edge_tts 的 Python 运行本文件（如 MoneyPrinterTurbo 的 venv）。
"""
import asyncio
import os
import subprocess
import sys
import tempfile

import edge_tts

VIDEOS = {
    "测试长视频1-生活冷知识": [
        "你知道吗，香蕉其实是浆果，而草莓根本不是浆果。",
        "蜂蜜是世界上唯一永远不会变质的食物，考古学家发现过三千年前的蜂蜜还能吃。",
        "章鱼有三颗心脏，血液还是蓝色的。",
        "闪电的温度大约是太阳表面温度的五倍。",
        "最后一条，每天必须喝满八杯水，其实并没有科学依据。",
    ],
    "测试长视频2-健身干货": [
        "深蹲被称为动作之王，一次能练到全身七成的肌肉群。",
        "增肌期间，蛋白质吃到每公斤体重两克就足够了，吃再多也不会多长肌肉。",
        "睡眠不足会直接让你的训练效果打对折。",
        "最后提醒，练前静态拉伸其实并不能减少受伤风险，动态热身才更有效。",
    ],
}

VOICE = "zh-CN-YunxiNeural"
# 素材统一放项目根目录的 test_videos/（批量切片.py 从那里取视频）
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "test_videos")


def tts(text, path):
    import time
    async def run():
        com = edge_tts.Communicate(text, VOICE)
        await com.save(path)
    for attempt in range(5):
        try:
            asyncio.run(run())
            if os.path.getsize(path) > 1000:
                return
        except Exception as e:
            print(f"  tts 第{attempt+1}次失败: {e}")
            time.sleep(10)
    raise RuntimeError("TTS 连续失败，请检查网络")


def build(video_name, segments):
    tmp = tempfile.mkdtemp()
    inputs = []
    for i, seg in enumerate(segments):
        p = os.path.join(tmp, f"seg{i}.mp3")
        tts(seg, p)
        inputs.append(p)
    # 拼接：每段之间加 0.9 秒静音
    silence = os.path.join(tmp, "sil.mp3")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=24000:cl=mono:d=0.9", silence], check=True)
    concat_in = []
    filter_parts = []
    streams = ""
    n = len(inputs) * 2 - 1
    for i, p in enumerate(inputs):
        concat_in += ["-i", p, "-i", silence]
    concat_in = concat_in[:-2]  # 去掉最后一个静音
    idx = 0
    for i in range(len(inputs)):
        streams += f"[{idx}:a]"
        idx += 1
        if i < len(inputs) - 1:
            streams += f"[{idx}:a]"
            idx += 1
    filter_parts.append(f"{streams}concat=n={len(inputs) * 2 - 1}:v=0:a=1[out]")
    audio_out = os.path.join(tmp, "audio.mp3")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + concat_in +
                   ["-filter_complex", ";".join(filter_parts), "-map", "[out]", audio_out],
                   check=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", audio_out], capture_output=True, text=True, check=True)
    dur = float(probe.stdout.strip()) + 1
    out = os.path.join(OUT_DIR, video_name + ".mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i",
                    f"gradients=s=1280x720:d={dur:.1f}:speed=0.03:c0=0x243b55:c1=0x141e30",
                    "-i", audio_out,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                    out], check=True)
    print("生成:", out, f"{dur:.0f}秒")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, segs in VIDEOS.items():
        build(name, segs)
    print("全部完成")
