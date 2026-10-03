# -*- coding: utf-8 -*-
"""测试04：funclip/subtitle_renderer.py —— Pillow 字幕渲染（替代 ImageMagick 的关键路径）。"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 公共库 import ROOT, Tester  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "funclip"))
from subtitle_renderer import DEFAULT_FONT_PATH, make_text_clip  # noqa: E402

t = Tester("test_04_字幕渲染")

t.group("字体资源")
t.true("内置中文字体存在", DEFAULT_FONT_PATH.is_file(), str(DEFAULT_FONT_PATH))

t.group("正常渲染")


def frame_rgba(clip):
    return clip.get_frame(0)


clip = make_text_clip("香蕉其实是浆果", font_size=32)
w, h = clip.size
t.true("中文渲染尺寸为正", w > 0 and h > 0, f"{w}x{h}")
arr = frame_rgba(clip)
t.eq("帧为 RGB 三通道（透明度走 mask）", arr.shape[2], 3)
t.true("透明 mask 存在", clip.mask is not None)
mask = clip.mask.get_frame(0)
t.true("mask 值域 0~1", float(mask.min()) >= 0.0 and float(mask.max()) <= 1.0)
opaque = mask > 0.5
t.true("文字有非透明像素", int(opaque.sum()) > 50, f"非透明像素 {int(opaque.sum())}")
t.true("文字颜色为白色", bool((arr[opaque] == 255).all()))

clip2 = make_text_clip("ABC xyz 123", font_size=24)
t.true("英文数字渲染正常", clip2.size[0] > 0 and clip2.size[1] > 0)

clip3 = make_text_clip("你好\n世界", font_size=32)
t.true("多行渲染更高", clip3.size[1] > clip.size[1] - 5, f"{clip3.size}")

t.true("颜色 black/green/red 可用",
       all(make_text_clip("测试", font_size=16, color=c).size[0] > 0
           for c in ("black", "green", "red")))

t.group("参数校验")
t.raises("font_size=0 拒绝", ValueError, make_text_clip, "x", font_size=0)
t.raises("font_size 为负拒绝", ValueError, make_text_clip, "x", font_size=-8)
t.raises("font_size 非整数拒绝", ValueError, make_text_clip, "x", font_size=2.5)
t.raises("font_size 为布尔拒绝", TypeError, make_text_clip, "x", font_size=True)
t.raises("未知颜色拒绝", ValueError, make_text_clip, "x", color="magenta2")
t.raises("字体文件缺失报 FileNotFoundError", FileNotFoundError,
         make_text_clip, "x", font_path=os.path.join(ROOT, "font", "不存在.ttf"))

t.group("尺寸合理性")
big = make_text_clip("字", font_size=64)
small = make_text_clip("字", font_size=16)
t.true("字号越大渲染越大", big.size[0] > small.size[0] and big.size[1] > small.size[1],
       f"64号={big.size} 16号={small.size}")

sys.exit(t.finish())
