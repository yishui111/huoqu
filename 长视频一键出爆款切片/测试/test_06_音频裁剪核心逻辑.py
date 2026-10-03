# -*- coding: utf-8 -*-
"""测试06：VideoClipper.clip 音频裁剪核心逻辑（合成状态，不加载识别模型）。

覆盖：按文本裁剪、多段 '#' 裁剪、[秒,秒] 偏移、方括号告警、起止偏移、
说话人裁剪、空文本回归（曾 pre_proc IndexError 崩溃）。
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 公共库 import ROOT, Tester  # noqa: E402

sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "funclip"))
from funclip.videoclipper import VideoClipper  # noqa: E402

t = Tester("test_06_音频裁剪核心逻辑")

RAW = "你 知 道 吗 香 蕉 其 实 是 浆 果 蜂 蜜 不 会 变 质"
TS = [[i * 300, i * 300 + 250] for i in range(17)]  # 17 个词，每词 300ms
SR = 16000


def mk_state(sd=False):
    state = {
        "audio_input": (SR, np.zeros(SR * 8, dtype=np.float64)),
        "recog_res_raw": RAW,
        "timestamp": list(TS),
        "sentences": [{"text": RAW, "timestamp": list(TS)}],
    }
    if sd:
        state["sd_sentences"] = [
            {"text": "甲", "timestamp": [[0, 1000]], "spk": 0},
            {"text": "乙", "timestamp": [[2000, 3000]], "spk": 1},
        ]
    return state


clipper = VideoClipper(None)
clipper.lang = "zh"

t.group("按文本裁剪")
(sr, audio), message, clip_srt = clipper.clip("香蕉其实是浆果", 0, 0, mk_state())
t.eq("采样率保持 16000", sr, 16000)
t.eq("命中片段长度 = (3250-1200)ms × 16", len(audio), (3250 - 1200) * 16)
t.true("日志含 1 periods", "1 periods found" in message, message)
# 裁剪区 SRT 的时间是相对裁剪起点的
t.true("切片字幕非空且含时间轴",
       "00:00:00,000 --> 00:00:02,050" in clip_srt
       and "香蕉其实是浆果" in clip_srt, clip_srt[:80])

t.group("带空格文本回归（从识别结果复制粘贴的场景）")
(sr, audio), message, _ = clipper.clip("香 蕉 其 实 是 浆 果", 0, 0, mk_state())
t.eq("带空格输入命中同样长度（回归：pre_proc 双空格曾导致永远匹配失败）",
     len(audio), (3250 - 1200) * 16)

t.group("未命中回退")
(sr, audio), message, _ = clipper.clip("不 存 在 的 话", 0, 0, mk_state())
t.eq("未命中返回原始全长音频", len(audio), SR * 8)
t.true("日志提示 No period", "No period found" in message, message)

t.group("多段 # 裁剪")
(sr, audio), message, _ = clipper.clip("你知道吗#蜂蜜不会变质", 0, 0, mk_state())
t.eq("两段拼接长度", len(audio), 18400 + 28000)
t.true("日志含 2 periods", "2 periods found" in message, message)

t.group("偏移与告警")
# 偏移语法为「文本[秒,秒]」（方括号跟在文本后面）
(sr, audio), message, _ = clipper.clip("香蕉[10,20]", 0, 0, mk_state())
t.eq("秒级偏移按 16 采样/毫秒叠加", len(audio), 8960)
(sr, audio), message, _ = clipper.clip("香蕉 [oops]", 0, 0, mk_state())
t.true("方括号无法解析时给出告警",
       "Bracket detected in dest_text but offset time matching failed" in message,
       message)
t.eq("告警时仍按原样裁剪", len(audio), 8800)

t.group("起止偏移")
(sr, audio), message, _ = clipper.clip("香蕉", 500, 0, mk_state())
t.eq("start_ost=500ms 使片段缩短", len(audio), 8800 - 500 * 16)
(sr, audio), message, _ = clipper.clip("香蕉", 0, 1000, mk_state())
t.eq("end_ost=1000ms 使片段加长", len(audio), 8800 + 1000 * 16)

t.group("说话人裁剪")
(sr, audio), message, _ = clipper.clip("", 0, 0, mk_state(sd=True),
                                       dest_spk="说话人1")
t.eq("按说话人1取片段长度", len(audio), 1000 * 16)
t.true("说话人裁剪日志正常", "1 periods found" in message, message)

t.group("空文本回归（曾 IndexError 崩溃）")
(sr, audio), message, clip_srt = clipper.clip("", 0, 0, mk_state())
t.true("空文本不崩溃且按未命中处理", "No period found" in message, message)
t.eq("空文本返回全长音频", len(audio), SR * 8)
t.eq("空文本切片字幕为空", clip_srt, "")

t.group("输入清洗")
(sr, audio), message, _ = clipper.clip("香蕉，其实是浆果。", 0, 0, mk_state())
t.eq("带标点文本剔除标点后命中", len(audio), 32800)
t.true("命中日志正常", "1 periods found" in message, message)

sys.exit(t.finish())
