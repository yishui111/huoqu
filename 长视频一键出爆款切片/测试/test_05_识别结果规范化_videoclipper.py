# -*- coding: utf-8 -*-
"""测试05：videoclipper 纯函数 —— 识别结果清洗、长句切分、MOSS/标规范化。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 公共库 import ROOT, Tester  # noqa: E402

sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "funclip"))  # videoclipper 顶层导入 utils 包
from funclip.videoclipper import (_clean_recognition_text, _is_valid_timestamp,  # noqa: E402
                                  _normalize_recognition_result,
                                  _split_long_sentence)

t = Tester("test_05_识别结果规范化")

# ---------- _is_valid_timestamp ----------
t.group("_is_valid_timestamp")
t.true("空列表无效", not _is_valid_timestamp([]))
t.true("None 无效", not _is_valid_timestamp(None))
t.true("非列表无效", not _is_valid_timestamp("[[0,1]]"))
t.true("首元素 None 无效", not _is_valid_timestamp([None, [1, 2]]))
t.true("尾元素 None 无效", not _is_valid_timestamp([[0, 1], None]))
t.true("正常时间戳有效", _is_valid_timestamp([[0, 100], [100, 200]]))

# ---------- _clean_recognition_text ----------
t.group("_clean_recognition_text 清洗")
t.eq("None 转空串", _clean_recognition_text(None), "")
t.eq("压缩连续空白", _clean_recognition_text("  你   好  "), "你 好")
t.eq("剔除 SenseVoice 标记",
     _clean_recognition_text("<|zh|>你好<|NEUTRAL|>世界"), "你好世界")
t.eq("剥掉首尾弯引号", _clean_recognition_text("“香蕉”"), "香蕉")
t.eq("普通文本原样", _clean_recognition_text("abc123"), "abc123")

# ---------- _split_long_sentence ----------
t.group("_split_long_sentence 长句切分")
short = {"text": "香蕉", "timestamp": [[0, 500]]}
chunks = _split_long_sentence(short)
t.eq("短句保持一条", len(chunks), 1)
t.eq("短句文本被清洗", chunks[0]["text"], "香蕉")

t.eq("无效时间戳返回空", _split_long_sentence({"text": "香蕉", "timestamp": []}), [])

mismatch = {"text": "香蕉是浆果", "timestamp": [[0, 500], [500, 900], [900, 1200]]}
chunks = _split_long_sentence(mismatch)
t.eq("token 数与时间戳数不一致时保持一条", len(chunks), 1)
t.eq("不一致时仍输出清洗文本", chunks[0]["text"], "香蕉是浆果")

# 8 个字、每字 2000ms：累计时长到 8000ms 处切开
long_ts = [[i * 2000, (i + 1) * 2000] for i in range(8)]
chunks = _split_long_sentence({"text": "一二三四五六七八", "timestamp": long_ts})
t.eq("超时长句切成两条", len(chunks), 2)
t.eq("第一条覆盖前四字（0~8000ms）", (chunks[0]["text"], chunks[0]["timestamp"][0][0],
                                      chunks[0]["timestamp"][-1][1]),
     (["一", "二", "三", "四"], 0, 8000))
t.eq("第二条覆盖后四字", (chunks[1]["text"], chunks[1]["timestamp"][-1][1]),
     (["五", "六", "七", "八"], 16000))

# 35 个单字、每字 100ms：token 数超 30 处切开
many_ts = [[i * 100, (i + 1) * 100] for i in range(35)]
chunks = _split_long_sentence({"text": "字" * 35, "timestamp": many_ts})
t.eq("超长 token 数切成两条", len(chunks), 2)
t.eq("第一条 30 个 token", len(chunks[0]["text"]), 30)
t.eq("第二条 5 个 token", len(chunks[1]["text"]), 5)

# ---------- _normalize_recognition_result ----------
t.group("_normalize_recognition_result")
res = {"text": "香蕉是浆果",
       "timestamp": [[0, 500], [500, 900], [900, 1300], [1300, 1700], [1700, 2000]],
       "sentence_info": [{"text": "香蕉是浆果",
                          "timestamp": [[0, 500], [500, 900], [900, 1300],
                                        [1300, 1700], [1700, 2000]]}]}
text, raw_text, ts, sent_info = _normalize_recognition_result(res)
t.eq("text 原样", text, "香蕉是浆果")
t.eq("raw_text 缺省时回退 text", raw_text, "香蕉是浆果")
t.eq("sentence_info 直接采用", len(sent_info), 1)

res2 = {"text": "香蕉是浆果",
        "timestamp": [[0, 500], [500, 900], [900, 1300], [1300, 1700], [1700, 2000]]}
_, _, _, sent_info2 = _normalize_recognition_result(res2)
t.eq("无 sentence_info 时从全文+时间戳兜底", len(sent_info2), 1)
t.true("兜底结果带时间戳", _is_valid_timestamp(sent_info2[0]["timestamp"]))

moss_ok = {"text": "你好 世界", "raw_text": "[10.5][S1]你 好 [12.0]",
           "timestamp": [[0, 300], [300, 600]]}
text, raw_text, _, _ = _normalize_recognition_result(moss_ok)
t.eq("完整 MOSS 输出 raw_text 归一为 text", raw_text, "你好 世界")

import funclip.videoclipper as vc  # noqa: E402

t.raises("截断的 MOSS 输出报 RuntimeError", RuntimeError,
         _normalize_recognition_result,
         {"text": "你好", "raw_text": "[10.5][S1]你 好",
          "timestamp": [[0, 300], [300, 600]]})
t.true("MOSS 截断标记正则可命中",
       bool(vc.MOSS_SEGMENT_MARKER_RE.search("[10.5][S1]")))
t.true("MOSS 结尾时间戳正则可命中",
       bool(vc.MOSS_FINAL_TIMESTAMP_RE.search("内容 [12.0]")))

sys.exit(t.finish())
