# -*- coding: utf-8 -*-
"""测试02：funclip/utils/trans_utils.py —— 时间戳解析、文本预处理与匹配、PCM 转换、状态读写。"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 公共库 import ROOT, STATE_DIR, Tester, ensure_dir  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "funclip"))
from utils.trans_utils import (convert_pcm_to_float, convert_time_to_millis,  # noqa: E402
                               extract_timestamps, pre_proc, proc, proc_spk,
                               load_state, write_state)

t = Tester("test_02_时间戳解析与文本匹配")

# ---------- convert_time_to_millis ----------
t.group("convert_time_to_millis")
t.eq("完整格式 HH:MM:SS,mmm", convert_time_to_millis("00:00:02,290"), 2290)
t.eq("时分秒无毫秒", convert_time_to_millis("01:02:03"), 3723000)
t.eq("分秒格式 MM:SS", convert_time_to_millis("10:30"), 630000)
t.eq("点号毫秒（按上游口径毫秒位直接取数字）", convert_time_to_millis("00:00:02.5"), 2005)
t.eq("尾随分隔符按 MM:SS 口径、毫秒记 0（回归：曾 int('') 崩溃）",
     convert_time_to_millis("00:02,"), 2000)

# ---------- pre_proc ----------
t.group("pre_proc 文本预处理")
t.eq("中文逐字加空格", pre_proc("香蕉其实是浆果"), "香 蕉 其 实 是 浆 果")
t.eq("标点被剔除", pre_proc("香蕉，是浆果。"), "香 蕉 是 浆 果")
t.eq("空字符串不再 IndexError（回归：曾 res[-1] 崩溃）", pre_proc(""), "")
t.eq("纯标点输入安全返回空", pre_proc("，。！？"), "")
t.eq("ASCII 原样保留", pre_proc("abc123"), "abc123")
t.eq("中英混排", pre_proc("你好world"), "你 好 world")

# ---------- proc 文本→时间戳匹配（返回值单位：采样点，16 采样/毫秒） ----------
t.group("proc 文本→时间戳匹配")
raw = "你 知 道 吗 香 蕉 很 甜"
ts = [[i * 300, i * 300 + 250] for i in range(8)]
t.eq("连续输入命中（返回采样点）", proc(raw, ts, "香蕉很甜"), [[19200, 37600]])
t.eq("带空格输入同样命中（回归：识别结果复制粘贴曾匹配失败）",
     proc(raw, ts, "香 蕉 很 甜"), [[19200, 37600]])
t.eq("未命中返回空", proc(raw, ts, "不 存 在"), [])
t.eq("待查文本为空返回空", proc(raw, ts, ""), [])
t.eq("时间戳为空返回空", proc(raw, [], "香 蕉"), [])
t.eq("大小写不敏感", proc("ABC def gh", [[0, 300], [300, 550], [550, 800]],
                          "abc def"), [[0, 8800]])
t.eq("多次出现全部命中", proc("好 好 学 习", [[0, 100], [100, 200], [200, 300],
                                              [300, 400]], "好"),
     [[0, 1600], [1600, 3200]])
t.eq("目标文本不存在返回空", proc("香蕉", [[0, 100]], "香 蕉 很 甜"), [])
t.eq("命中但词数越界安全返回空", proc("香 蕉", [[0, 100], [100, 200]],
                                      "香 蕉 很 甜"), [])

# ---------- proc_spk 说话人匹配 ----------
t.group("proc_spk 说话人匹配")
sd = [{"text": "甲的话", "timestamp": [[0, 1000]], "spk": 0},
      {"text": "乙的话", "timestamp": [[2000, 3000]], "spk": 1},
      {"text": "乙的又一句", "timestamp": [[4000, 4500]], "spk": 1}]
t.eq("按说话人1取全部片段", proc_spk("说话人1", sd), [[2000 * 16, 3000 * 16],
                                                      [4000 * 16, 4500 * 16]])
t.eq("按说话人0取片段", proc_spk("说话人0", sd), [[0, 16000]])
t.eq("不存在的说话人返回空", proc_spk("说话人9", sd), [])

# ---------- extract_timestamps（LLM 输出解析，本地增强版） ----------
t.group("extract_timestamps 格式兼容")
strict = "1. [00:00:02,290-00:00:07,400] 香蕉其实是浆果\n2. [00:00:10,560-00:00:15,520] 章鱼有三颗心脏"
t.eq("严格方括号多行", extract_timestamps(strict),
     [[2290, 7400], [10560, 15520]])
t.eq("无方括号", extract_timestamps("00:00:02,290-00:00:07,400"),
     [[2290, 7400]])
t.eq("箭头连接符 -->", extract_timestamps("[00:00:01,000-->00:00:02,000]"),
     [[1000, 2000]])
t.eq("MM:SS 短格式", extract_timestamps("[02:10-03:00]"), [[130000, 180000]])
t.eq("波浪线/至/到 连接符", extract_timestamps("[00:01~00:02]\n[00:03至00:04]\n[00:05到00:06]"),
     [[1000, 2000], [3000, 4000], [5000, 6000]])
t.eq("点号毫秒", extract_timestamps("[00:00:02.290-00:00:07.400]"),
     [[2290, 7400]])
t.eq("结束早于开始的片段被过滤", extract_timestamps("[00:00:05,000-00:00:01,000]"), [])
t.eq("纯文本无时间戳返回空", extract_timestamps("今天天气不错，适合切片。"), [])
t.eq("空输入返回空", extract_timestamps(""), [])
t.eq("破折号连接符 —", extract_timestamps("1. [00:00:02,000—00:00:03,500] 片段"),
     [[2000, 3500]])
t.eq("尾随逗号时间戳不崩溃（回归）", extract_timestamps("[00:02,-00:05]"),
     [[2000, 5000]])

# ---------- convert_pcm_to_float ----------
t.group("convert_pcm_to_float")
f64 = np.array([0.0, 0.5, -0.5], dtype=np.float64)
t.true("float64 原样返回", convert_pcm_to_float(f64) is f64)
f32 = np.array([0.0, 0.5], dtype=np.float32)
out = convert_pcm_to_float(f32)
t.true("float32 升为 float64", out.dtype == np.float64 and abs(out[1] - 0.5) < 1e-9)
i16 = np.array([0, 16384, -16384], dtype=np.int16)
out = convert_pcm_to_float(i16)
t.eq("int16 按位深归一化", [round(v, 3) for v in out], [0.0, 0.5, -0.5])
i8 = np.array([127, 0], dtype=np.int8)  # 8bit WAV 无符号语义，减 128 偏置
out = convert_pcm_to_float(i8)
t.eq("int8 减去直流偏置", [round(v, 3) for v in out], [-0.008, -1.0])
t.raises("不支持的类型抛 ValueError", ValueError,
         convert_pcm_to_float, np.array([0, 1], dtype=np.float16))

# ---------- write_state / load_state 往返 ----------
t.group("write_state/load_state 往返")
ensure_dir(STATE_DIR)
state_dir = os.path.join(STATE_DIR, "tmp_state")
ensure_dir(state_dir)
state = {"recog_res_raw": "你 好 世 界", "timestamp": [[0, 300], [300, 600]],
         "sentences": [{"text": "你好", "timestamp": [[0, 300]]}]}
write_state(state_dir, state)
back = load_state(state_dir)
t.eq("recog_res_raw 往返一致", back["recog_res_raw"], "你 好 世 界")
t.eq("timestamp 往返一致", back["timestamp"], [[0, 300], [300, 600]])
t.eq("sentences 往返一致", back["sentences"],
     [{"text": "你好", "timestamp": [[0, 300]]}])

sys.exit(t.finish())
