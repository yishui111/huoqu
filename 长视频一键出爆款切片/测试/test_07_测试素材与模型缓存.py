# -*- coding: utf-8 -*-
"""测试07：测试素材与模型缓存 —— test_videos 完整性、识别模型缓存、输出目录。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 公共库 import (ROOT, TEST_DIR, Tester, VIDEO1, VIDEO2, ffprobe_info)  # noqa: E402

t = Tester("test_07_测试素材与模型缓存")

t.group("测试视频素材")
t.true("测试长视频1 存在", os.path.isfile(VIDEO1), VIDEO1)
t.true("测试长视频2 存在", os.path.isfile(VIDEO2), VIDEO2)

for tag, video in [("视频1", VIDEO1), ("视频2", VIDEO2)]:
    info = ffprobe_info(video)
    dur = float(info["format"]["duration"])
    t.true(f"{tag} 时长在 20~45 秒", 20 <= dur <= 45, f"{dur:.1f}s")
    vstreams = [s for s in info["streams"] if s["codec_type"] == "video"]
    astreams = [s for s in info["streams"] if s["codec_type"] == "audio"]
    t.eq(f"{tag} 有 1 路视频流", len(vstreams), 1)
    t.eq(f"{tag} 有 1 路音频流", len(astreams), 1)
    if vstreams:
        s = vstreams[0]
        t.true(f"{tag} 分辨率 1280x720", (s["width"], s["height"]) == (1280, 720),
               f"{s['width']}x{s['height']}")
        t.true(f"{tag} 视频编码 h264", s["codec_name"] == "h264", s["codec_name"])
    if astreams:
        t.true(f"{tag} 音频编码 aac", astreams[0]["codec_name"] == "aac",
               astreams[0]["codec_name"])

t.group("识别模型缓存")
cache = os.path.join(ROOT, "model_cache")
t.true("model_cache 目录存在", os.path.isdir(cache))
total = 0
file_count = 0
for dirpath, _, files in os.walk(cache):
    for fn in files:
        try:
            total += os.path.getsize(os.path.join(dirpath, fn))
            file_count += 1
        except OSError:
            pass
t.true("缓存体积 > 100MB（识别模型已就位，无需重新下载）", total > 100 * 1024 ** 2,
       f"{total / 1024 ** 2:.0f}MB / {file_count} 个文件")
hits = []
for dirpath, files, _ in os.walk(cache):
    if "paraformer" in dirpath.replace("\\", "/").lower() and files:
        hits.append(dirpath)
t.true("paraformer 识别模型目录存在", bool(hits), str(hits[:2]))

t.group("输出目录")
for d in ["output", "output_api"]:
    t.true(f"{d}/ 目录存在", os.path.isdir(os.path.join(ROOT, d)))

t.group("素材制作脚本")
maker = os.path.join(TEST_DIR, "制作测试素材.py")
t.true("制作测试素材.py 位于 测试/ 目录", os.path.isfile(maker))
with open(maker, encoding="utf-8") as f:
    src = f.read()
t.true("素材脚本指向项目根 test_videos（脚本已移入 测试/）",
       "test_videos" in src and '".."' in src)
t.true("素材脚本包含两个测试视频定义",
       "测试长视频1-生活冷知识" in src and "测试长视频2-健身干货" in src)

sys.exit(t.finish())
