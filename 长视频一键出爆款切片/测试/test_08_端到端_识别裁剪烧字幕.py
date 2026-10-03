# -*- coding: utf-8 -*-
"""测试08：端到端 —— 真实识别模型加载 → 语音识别 → 文本裁剪烧字幕 / AI 时间戳裁剪。

慢测试（加载 1.5GB 识别模型，约 1~2 分钟）。
产物：转写文本/SRT 存 产物/转写/，成片存 产物/切片/，抽帧对比存 产物/抽帧/。
"""
import os
import re
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 公共库 import (CLIP_DIR, ROOT, TEST_DIR, TRAN_DIR, FRAME_DIR, Tester,  # noqa: E402
                    VIDEO1, ensure_dir, extract_frame, ffprobe_duration)

os.environ.setdefault("MODELSCOPE_CACHE", os.path.join(ROOT, "model_cache"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "funclip"))

t = Tester("test_08_端到端_识别裁剪烧字幕")

# ---------- 加载识别模型 ----------
t.group("识别模型加载")
t0 = time.time()
from funasr import AutoModel  # noqa: E402
from funclip.videoclipper import VideoClipper  # noqa: E402
from funclip.model_selection import create_asr_model  # noqa: E402
from utils.trans_utils import extract_timestamps  # noqa: E402

# 走项目自己的模型工厂（模型已缓存时本地离线加载，与 WebUI/批量脚本同一代码路径）
asr = create_asr_model("paraformer", "zh", AutoModel)
clipper = VideoClipper(asr)
clipper.lang = "zh"
t.true("模型加载成功", asr is not None, f"耗时 {time.time()-t0:.0f}s")

# ---------- 语音识别 ----------
t.group("语音识别 video_recog")
t1 = time.time()
res_text, res_srt, state = clipper.video_recog(
    VIDEO1, output_dir=os.path.join(TEST_DIR, "产物"))
t.true(f"识别完成（{time.time()-t1:.0f}s）", isinstance(res_text, str))
t.true("识别出关键句「香蕉是浆果」", "香蕉" in res_text and "浆果" in res_text,
       res_text[:80])
t.true("识别出「蜂蜜」知识条目", "蜂蜜" in res_text)
t.true("识别出「章鱼」知识条目", "章鱼" in res_text)
t.true("SRT 含时间轴箭头", "-->" in res_srt)
t.true("SRT 行数充足（>10 行）", len(res_srt.splitlines()) > 10,
       f"{len(res_srt.splitlines())} 行")
t.true("state 含 recog_res_raw/timestamp/sentences",
       all(k in state for k in ("recog_res_raw", "timestamp", "sentences")))
t.true("词级时间戳非空", len(state["timestamp"]) > 10,
       f"{len(state['timestamp'])} 个词")

ensure_dir(TRAN_DIR)
with open(os.path.join(TRAN_DIR, "识别全文.txt"), "w", encoding="utf-8") as f:
    f.write(res_text)
with open(os.path.join(TRAN_DIR, "识别全文.srt"), "w", encoding="utf-8") as f:
    f.write(res_srt)
t.true("识别全文与 SRT 已存 产物/转写/", True)

# ---------- 按文本裁剪 + 烧字幕 ----------
t.group("文本裁剪+烧字幕")
out1 = ensure_dir(os.path.join(CLIP_DIR, "文本裁剪"))
clip_file, message, clip_srt = clipper.video_clip(
    "香蕉其实是浆果", 0, 100, state, font_size=32, font_color="white",
    add_sub=True, output_dir=out1)
t.true("生成切片文件", bool(clip_file) and os.path.isfile(clip_file),
       str(clip_file))
m = re.search(r"from ([\d.]+) to ([\d.]+)", message)
t.true("裁剪日志含时间段", bool(m), message[:120])
if clip_file and m:
    x0, x1 = float(m.group(1)), float(m.group(2))
    dur = ffprobe_duration(clip_file)
    t.near("切片时长≈目标片段(含0.1s尾部偏移)", dur, x1 - x0 + 0.1, 1.0)
    t.true("切片体积 > 30KB", os.path.getsize(clip_file) > 30 * 1024,
           f"{os.path.getsize(clip_file)/1024:.0f}KB")
    # 字幕烧录验证：同源同帧对比，底部区域应有显著差异（白字）
    src_png = extract_frame(VIDEO1, x0 + 1.0,
                            os.path.join(FRAME_DIR, "源帧.png"))
    clip_png = extract_frame(clip_file, 1.0,
                             os.path.join(FRAME_DIR, "切片帧.png"))
    a = np.asarray(Image.open(src_png).convert("RGB"), dtype=np.float32)
    b = np.asarray(Image.open(clip_png).convert("RGB"), dtype=np.float32)
    h = a.shape[0]
    bottom = slice(int(h * 0.7), h)
    diff_bottom = float(np.abs(a[bottom] - b[bottom]).mean())
    diff_top = float(np.abs(a[:h // 3] - b[:h // 3]).mean())
    t.true("底部区域差异显著（字幕已烧录）", diff_bottom > 1.0,
           f"底部差 {diff_bottom:.2f} 顶部差 {diff_top:.2f}")
    t.true("顶部区域基本一致（同源帧）", diff_top < 8.0, f"{diff_top:.2f}")
t.true("裁剪区 SRT 非空", bool(clip_srt) and "-->" in clip_srt)
with open(os.path.join(TRAN_DIR, "裁剪段字幕.srt"), "w", encoding="utf-8") as f:
    f.write(clip_srt)

# ---------- 模拟 LLM 时间戳裁剪（extract_timestamps → video_clip） ----------
t.group("AI时间戳裁剪")
llm_out = ("1. [00:00:00,500-00:00:08,000] 开头冷知识\n"
           "2. [00:00:08,100-00:00:12,000] 中间冷知识")
ts = extract_timestamps(llm_out)
t.eq("LLM 输出解析出 2 段时间戳", ts, [[500, 8000], [8100, 12000]])
out2 = ensure_dir(os.path.join(CLIP_DIR, "AI模拟裁剪"))
clip_file2, message2, clip_srt2 = clipper.video_clip(
    "", 0, 0, state, font_size=32, font_color="white", add_sub=True,
    output_dir=out2, timestamp_list=ts)
t.true("AI 裁剪生成切片", bool(clip_file2) and os.path.isfile(clip_file2),
       str(clip_file2))
if clip_file2:
    dur2 = ffprobe_duration(clip_file2)
    t.near("AI 裁剪时长≈两段之和(11.4s)", dur2, 11.4, 1.5, f"{dur2:.2f}s")
    t.true("AI 裁剪 SRT 覆盖两段（序号到2）", "\n2\n" in clip_srt2,
           clip_srt2[:120])

# ---------- 不烧字幕的纯裁剪 ----------
t.group("纯裁剪不带字幕")
out3 = ensure_dir(os.path.join(CLIP_DIR, "无字幕裁剪"))
clip_file3, _, _ = clipper.video_clip(
    "章鱼有三颗心脏", 0, 0, state, add_sub=False, output_dir=out3)
t.true("无字幕裁剪也出片", bool(clip_file3) and os.path.isfile(clip_file3),
       str(clip_file3))

# ---------- 资源释放 ----------
t.group("资源释放")
try:
    state["video"].close()
    released = True
except Exception:  # noqa: BLE001
    released = False
t.true("视频句柄可正常关闭", released)

sys.exit(t.finish())
