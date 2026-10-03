# -*- coding: utf-8 -*-
"""测试09：REST 接口服务（api_server.py，8335 同款应用跑在随机空闲端口）。

覆盖：健康检查、404、上传识别、轮询、转写读取、裁剪出片、成片下载、
异常路径（错误 recog_id / 空文本 / 无音轨视频）。
慢测试（首次识别要加载模型，约 1 分钟）。
"""
import json
import os
import re
import socket
import sys
import threading
import time

import httpx
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 公共库 import (API_DIR, ROOT, Tester, VIDEO1, ensure_dir,  # noqa: E402
                    ffmpeg_run, ffprobe_duration)

os.environ.setdefault("MODELSCOPE_CACHE", os.path.join(ROOT, "model_cache"))
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ["no_proxy"] = "127.0.0.1,localhost"
sys.path.insert(0, ROOT)

t = Tester("test_09_REST接口服务")

t.group("服务启动")
import api_server  # noqa: E402

t.true("FastAPI 应用可导入", api_server.app is not None)
routes = {r.path for r in api_server.app.routes}
for p in ["/api/health", "/api/recog", "/api/transcript/{tid}",
          "/api/clip", "/api/job/{jid}", "/api/result/{jid}"]:
    t.true(f"路由存在 {p}", p in routes, str(sorted(routes)))

with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
config = uvicorn.Config(api_server.app, host="127.0.0.1", port=port,
                        log_level="warning")
server = uvicorn.Server(config)
thread = threading.Thread(target=server.run, daemon=True)
thread.start()
BASE = f"http://127.0.0.1:{port}"
for _ in range(60):
    try:
        r = httpx.get(BASE + "/api/health", timeout=2)
        if r.status_code == 200:
            break
    except Exception:  # noqa: BLE001
        time.sleep(0.5)
else:
    t.true("服务在10秒内可访问", False, "health 探测超时")
    sys.exit(t.finish())
t.true("服务可访问", True, BASE)


def poll(jid, timeout, tag):
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        r = httpx.get(BASE + "/api/job/" + jid, timeout=10)
        last = r.json().get("data", {})
        if last.get("status") in ("done", "error"):
            return last
        time.sleep(1.5)
    last["status"] = "timeout"
    return last


t.group("健康检查与404")
r = httpx.get(BASE + "/api/health", timeout=5)
body = r.json()
t.eq("health ok", (r.status_code, body.get("ok")), (200, True))
t.true("初始未加载模型", body["data"]["model_loaded"] is False)
for path in ["/api/transcript/no-such-id", "/api/job/no-such-id"]:
    r = httpx.get(BASE + path, timeout=5)
    t.eq(f"404 {path}", r.status_code, 404)
r = httpx.get(BASE + "/api/result/no-such-id", timeout=5)
t.eq("404 result", r.status_code, 404)

t.group("上传识别")
ensure_dir(API_DIR)
with open(VIDEO1, "rb") as f:
    data = f.read()
r = httpx.post(BASE + "/api/recog",
               files={"file": ("测试长视频1-生活冷知识.mp4", data, "video/mp4")},
               timeout=120)
t.eq("上传受理 200/ok", (r.status_code, r.json().get("ok")), (200, True))
tid = r.json()["data"]["task_id"]
t.true("返回 task_id", bool(tid), tid)

# 识别含首次模型加载（约 30~60 秒），给足 300 秒单次长轮询
job = poll(tid, 300, "recog")
t.true("识别任务完成", job.get("status") == "done", str(job)[:200])
t.true("识别全文含「香蕉」", "香蕉" in (job.get("text") or ""), (job.get("text") or "")[:60])
t.true("job 携带 SRT", "-->" in (job.get("srt") or ""))

r = httpx.get(BASE + "/api/transcript/" + tid, timeout=10)
tr = r.json()
t.eq("transcript 200/ok", (r.status_code, tr.get("ok")), (200, True))
t.true("transcript 全文非空", len(tr["data"].get("text") or "") > 20)
t.true("transcript SRT 含时间轴", "-->" in (tr["data"].get("srt") or ""))

r = httpx.get(BASE + "/api/health", timeout=5)
t.true("识别后模型常驻 (model_loaded=True)",
       r.json()["data"]["model_loaded"] is True)

# 上传文件名安全化：落盘为 8位十六进制 + 扩展名，不再出现中文/乱码文件名
test_t0 = time.time()
bad = [fn for fn in os.listdir(api_server.OUT_DIR)
       if os.path.isfile(os.path.join(api_server.OUT_DIR, fn))
       and os.path.getmtime(os.path.join(api_server.OUT_DIR, fn)) > test_t0
       and not fn.isascii()]
t.true("新落盘文件名均为 ASCII 安全名（回归：曾出现乱码文件名）",
       len(bad) == 0, str(bad[:3]))

t.group("裁剪出片与下载")
r = httpx.post(BASE + "/api/clip", json={"recog_id": tid,
                                         "text": "香蕉其实是浆果",
                                         "add_sub": True, "font_size": 32},
               timeout=30)
t.eq("clip 受理 200/ok", (r.status_code, r.json().get("ok")), (200, True))
cid = r.json()["data"]["task_id"]
job = poll(cid, 180, "clip")
t.true("裁剪任务完成", job.get("status") == "done", str(job)[:200])
t.true("返回成片文件名 .mp4", (job.get("file") or "").endswith(".mp4"),
       job.get("file"))
t.true("job 携带切片字幕", "-->" in (job.get("srt") or ""))

r = httpx.get(BASE + "/api/result/" + cid, timeout=60)
t.eq("下载 200", r.status_code, 200)
if r.status_code == 200:
    out_mp4 = os.path.join(API_DIR, "接口切片.mp4")
    with open(out_mp4, "wb") as f:
        f.write(r.content)
    t.true("成片 > 30KB", os.path.getsize(out_mp4) > 30 * 1024,
           f"{os.path.getsize(out_mp4)/1024:.0f}KB")
    dur = ffprobe_duration(out_mp4)
    t.true("成片时长 3~9 秒", 3 <= dur <= 9, f"{dur:.2f}s")

t.group("异常路径")
r = httpx.post(BASE + "/api/clip", json={"recog_id": "deadbeef",
                                         "text": "香蕉"}, timeout=30)
jid = r.json()["data"]["task_id"]
job = poll(jid, 30, "bad-id")
t.true("错误 recog_id → 任务 error", job.get("status") == "error",
       str(job)[:150])
t.true("错误信息说明识别任务不存在", "识别任务不存在" in (job.get("message") or ""),
       job.get("message"))

r = httpx.post(BASE + "/api/clip", json={"recog_id": tid, "text": ""},
               timeout=30)
jid = r.json()["data"]["task_id"]
job = poll(jid, 60, "empty")
t.true("空文本 → 任务 error 而非崩溃或假成功（回归）",
       job.get("status") == "error", str(job)[:150])
t.true("错误信息说明未生成切片", "未生成切片" in (job.get("message") or ""),
       job.get("message"))

mute = os.path.join(API_DIR, "无音轨.mp4")
ffmpeg_run(["-f", "lavfi", "-i",
            "testsrc=size=320x240:rate=15:duration=3", mute])
with open(mute, "rb") as f:
    r = httpx.post(BASE + "/api/recog",
                   files={"file": ("无音轨.mp4", f.read(), "video/mp4")},
                   timeout=60)
mid = r.json()["data"]["task_id"]
job = poll(mid, 120, "mute")
t.true("无音轨视频 → 任务 error（回归：曾 sys.exit 杀死整个服务）",
       job.get("status") == "error", str(job)[:150])
t.true("错误信息提及没有音轨", "没有音轨" in (job.get("message") or ""),
       job.get("message"))
r = httpx.get(BASE + "/api/health", timeout=5)
t.true("出错后服务仍存活", r.status_code == 200 and r.json()["ok"] is True)

t.group("服务关闭")
server.should_exit = True
thread.join(timeout=15)
t.true("服务线程退出", not thread.is_alive())

sys.exit(t.finish())
