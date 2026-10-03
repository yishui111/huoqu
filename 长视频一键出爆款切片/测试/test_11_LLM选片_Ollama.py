# -*- coding: utf-8 -*-
"""测试11：本地大模型选片（Ollama + litellm）—— 连通性、模型在位、真实选片输出可解析。

前置：本机 Ollama 已运行（启动FunClip.bat 会自动拉起）；使用已拉取的 qwen2.5:7b-16k。
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 公共库 import ROOT, TEST_DIR, TRAN_DIR, Tester, ensure_dir  # noqa: E402

os.environ["LITELLM_API_BASE"] = "http://127.0.0.1:11434"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "funclip"))

t = Tester("test_11_LLM选片")

EXPECTED_MODEL = "qwen2.5:7b-16k"

t.group("Ollama 服务连通")
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
names = []
online = False
err = ""
for attempt in range(3):  # Ollama 可能在重启/唤醒中，短暂重试
    try:
        with opener.open("http://127.0.0.1:11434/api/tags", timeout=5) as r:
            tags = json.loads(r.read().decode("utf-8"))
        names = [m["name"] for m in tags.get("models", [])]
        online = True
        break
    except Exception as exc:  # noqa: BLE001
        online = False
        err = f"{type(exc).__name__}: {exc}"
        time.sleep(5)
t.true("Ollama 已运行 (11434)", online,
       "" if online else err + "；启动FunClip.bat 会自动拉起 Ollama")
t.true("Ollama 已运行 (11434)", online,
       "" if online else err + "；启动FunClip.bat 会自动拉起 Ollama")

t.group("选片模型在位")
qwen = [n for n in names if n.startswith("qwen2.5")]
t.true("存在 qwen2.5 系列模型", bool(qwen), str(names))
t.true(f"已拉取 {EXPECTED_MODEL}（项目默认选片模型，回归：qwen2.5:3b 未安装）",
       EXPECTED_MODEL in names, str(names))
with open(os.path.join(ROOT, "批量切片.py"), encoding="utf-8") as f:
    batch_src = f.read()
t.true("批量切片.py 使用的模型与 Ollama 在位模型一致",
       f'LLM_MODEL = "ollama/{EXPECTED_MODEL}"' in batch_src)
with open(os.path.join(ROOT, "funclip", "launch.py"), encoding="utf-8") as f:
    launch_src = f.read()
t.true("WebUI 默认模型与 Ollama 在位模型一致",
       f'value="litellm/ollama/{EXPECTED_MODEL}"' in launch_src)

t.group("真实选片推理")
if not online:
    t.true("跳过推理（Ollama 未运行）", False, "无 Ollama 无法验证选片")
    sys.exit(t.finish())

from llm.litellm_api import litellm_call  # noqa: E402
from utils.trans_utils import extract_timestamps  # noqa: E402

SYSTEM_PROMPT = ("你是一个视频srt字幕分析剪辑器，输入视频的srt字幕，"
                 "分析其中的精彩且尽可能连续的片段并裁剪出来，输出四条以内的片段，"
                 "将片段中在时间上连续的多个句子及它们的时间戳合并为一条，"
                 "注意确保文字与时间戳的正确匹配。输出需严格按照如下格式："
                 "1. [开始时间-结束时间] 文本，注意其中的连接符是“-”。"
                 "时间戳必须保留方括号、使用单条短横线“-”连接，"
                 "例如 [00:00:02,290-00:00:07,400]，不要使用 --> 或其他符号")
SRT = """1
00:00:00,500 --> 00:00:03,000
你知道吗 香蕉其实是浆果

2
00:00:03,200 --> 00:00:06,500
蜂蜜是世界上唯一不会变质的食物

3
00:00:06,700 --> 00:00:09,900
章鱼有三颗心脏 血液是蓝色的

4
00:00:10,100 --> 00:00:13,400
闪电的温度是太阳表面的五倍

5
00:00:13,600 --> 00:00:17,000
每天八杯水并没有科学依据
"""
t0 = time.time()
try:
    llm_res = litellm_call("", "ollama/" + EXPECTED_MODEL,
                           "这是待裁剪的视频srt字幕：\n" + SRT, SYSTEM_PROMPT)
    llm_err = ""
except Exception as exc:  # noqa: BLE001
    llm_res = ""
    llm_err = f"{type(exc).__name__}: {exc}"
t.true(f"litellm→Ollama 推理返回（{time.time()-t0:.0f}s）", bool(llm_res), llm_err)
ensure_dir(TRAN_DIR)
with open(os.path.join(TRAN_DIR, "LLM选片输出.txt"), "w", encoding="utf-8") as f:
    f.write(llm_res)

ts = extract_timestamps(llm_res)
t.true("选片输出解析出时间戳", len(ts) >= 1, f"输出片段: {llm_res[:200]}")
t.true("片段数 ≤ 4（符合提示词要求）", 1 <= len(ts) <= 4, f"{len(ts)} 段")
t.true("时间戳落在素材范围内且方向正确",
       all(0 <= a < b <= 17000 for a, b in ts), str(ts))

sys.exit(t.finish())
