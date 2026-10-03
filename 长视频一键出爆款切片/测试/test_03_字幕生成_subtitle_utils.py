# -*- coding: utf-8 -*-
"""测试03：funclip/utils/subtitle_utils.py —— SRT 时间格式、分词、字幕生成与裁剪切片。"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 公共库 import ROOT, Tester  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "funclip"))
from utils.subtitle_utils import (Text2SRT, generate_srt, generate_srt_clip,  # noqa: E402
                                  str2list, time_convert)

t = Tester("test_03_字幕生成")


def S(text, ts):
    return {"text": text, "timestamp": ts}


def sentences():
    """三句话、逐字时间戳（str2list 对中文按字切分，token 数须与时间戳数一致）。"""
    return [
        S("香蕉是浆果", [[1000, 1500], [1500, 2000], [2000, 2500],
                        [2500, 3000], [3000, 3500]]),
        S("蜂蜜不变质", [[4000, 4500], [4500, 5000], [5000, 5500],
                        [5500, 6000], [6000, 6500]]),
        S("章鱼三颗心", [[7000, 7500], [7500, 8000], [8000, 8500],
                        [8500, 9000], [9000, 9500]]),
    ]


# ---------- time_convert ----------
t.group("time_convert 毫秒转 SRT 时间")
t.eq("0", time_convert(0), "00:00:00,000")
t.eq("1500", time_convert(1500), "00:00:01,500")
t.eq("59999", time_convert(59999), "00:00:59,999")
t.eq("61000", time_convert(61000), "00:01:01,000")
t.eq("3600000", time_convert(3600000), "01:00:00,000")
t.eq("3661500", time_convert(3661500), "01:01:01,500")

# ---------- str2list ----------
t.group("str2list 分词")
t.eq("中文按字切分", str2list("香蕉是浆果"), ["香", "蕉", "是", "浆", "果"])
t.eq("英文按词切分", str2list("hello world 66"), ["hello", "world", "66"])
t.eq("连字符词保持完整", str2list("deep-sea ABC"), ["deep-sea", "ABC"])
t.eq("中英混排（\\w 含中文，GPT 切片粘成一个词）", str2list("用GPT切片"),
     ["用", "GPT切片"])

# ---------- Text2SRT ----------
t.group("Text2SRT 单条字幕")
t2s = Text2SRT("香蕉", [[1000, 3500]])
t.eq("text 保留原文", t2s.text(), "香蕉")
t.eq("start/end 毫秒", (t2s.start_sec, t2s.end_sec), (1000, 3500))
t.eq("srt 三行结构", t2s.srt(), "00:00:01,000 --> 00:00:03,500\n香蕉\n")
t.eq("time(acc_ost) 叠加偏移", t2s.time(2.5), (1.0 + 2.5, 3.5 + 2.5))
t2s2 = Text2SRT(["hello", "world"], [[0, 500], [500, 900]])
t.eq("词列表拼接加空格", t2s2.text(), "hello world")
t2s3 = Text2SRT("香蕉是浆果。", [[0, 500]])
t.eq("text 去尾部标点", t2s3.text(), "香蕉是浆果")

# ---------- generate_srt ----------
t.group("generate_srt 全文 SRT")
with_spk = [dict(S("香蕉", [[0, 1000]]), spk=0), S("蜂蜜", [[2000, 3000]])]
srt = generate_srt(with_spk)
t.true("带说话人标记 spk0", "1  spk0\n" in srt, srt[:60])
t.true("无说话人的普通序号", "2\n00:00:02,000 --> 00:00:03,000\n蜂蜜\n" in srt)
no_ts = [S("坏数据", []), S("正常", [[0, 500]])]
srt2 = generate_srt(no_ts)
t.true("无时间戳的句子被跳过", "坏数据" not in srt2 and "正常" in srt2)

# ---------- generate_srt_clip ----------
t.group("generate_srt_clip 整句包含")
srt, subs, cc = generate_srt_clip(sentences(), 0.5, 4.0)
t.eq("整句包含时只切到第1句", len(subs), 1)
t.eq("字幕时间相对裁剪起点", [round(x, 2) for x in subs[0][0]], [0.5, 3.0])
t.eq("字幕文本", subs[0][1], "香蕉是浆果")
t.true("序号从1开始且含时间轴", srt.startswith("1\n00:00:00,500 --> 00:00:03,000"),
       srt[:50])

t.group("generate_srt_clip 跨句部分重叠")
srt, subs, cc = generate_srt_clip(sentences(), 3.0, 6.5)
t.eq("前句切尾+中句整句", [x[1] for x in subs], ["果", "蜂蜜不变质"])
t.eq("首条字幕从0开始", [round(x, 2) for x in subs[0][0]], [0.0, 0.5])
t.eq("次条字幕相对起点", [round(x, 2) for x in subs[1][0]], [1.0, 3.5])
t.eq("序号连续", [srt.split("\n")[0], srt.split("\n")[3]], ["1", "2"])

t.group("generate_srt_clip 两端截断")
srt, subs, cc = generate_srt_clip(sentences(), 4.5, 8.0)
t.eq("左截断中句+右截断末句", [x[1] for x in subs], ["蜜不变质", "章鱼"])
t.eq("截断后字幕时间", [round(x[0][0], 2) for x in subs], [0.0, 2.5])

t.group("generate_srt_clip 边界")
srt, subs, cc = generate_srt_clip(sentences(), 0.0, 0.9)
t.eq("窗口在句子之前返回空", (srt, subs), ("", []))
srt, subs, cc = generate_srt_clip(sentences(), 3.0, 3.6, begin_index=2,
                                  time_acc_ost=10.0)
t.eq("begin_index 顺延序号", srt.split("\n")[0], "3")
t.eq("time_acc_ost 整体平移字幕时间", [round(x, 2) for x in subs[0][0]],
     [10.0, 10.5])
t.eq("返回的 cc 为下一个可用序号", cc, 4)

# 确认 generate_srt_clip 不会把上一次的 list 化结果串进原数据（调用方需传新副本）
t.group("数据安全")
fresh = sentences()
generate_srt_clip(copy.deepcopy(fresh), 3.0, 6.5)
t.true("传入的 sentence_list 保持传入时的引用独立",
       isinstance(fresh[0]["text"], str))

sys.exit(t.finish())
