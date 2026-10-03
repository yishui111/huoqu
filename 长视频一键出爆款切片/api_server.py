# -*- coding: utf-8 -*-
"""
FunClip · REST 接口服务（跑在本目录 .venv 里，端口 8335）

把「长视频 → 语音识别 → 按文本裁剪 + 烧字幕」暴露成异步任务接口
（LLM 智能选片依赖 Ollama，本服务走无 LLM 的确定性裁剪：给文本就裁）。

  POST /api/recog          上传视频/音频 → 异步识别（返回 task_id）
  GET  /api/transcript/{id}  取识别全文与 SRT
  POST /api/clip           按文本片段裁剪（可烧字幕）→ 异步出片
  GET  /api/job/{id}       任务进度
  GET  /api/result/{id}    下载成片 mp4
  GET  /api/health         健康检查

启动：  .venv\\Scripts\\python.exe api_server.py   （或双击 启动接口服务.bat）
文档：  ..\\接口文档.md
"""
import os
import sys
import threading
import time
import uuid

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "funclip"))  # videoclipper 以顶层方式 import 同级 utils 包
os.chdir(BASE)
os.environ.setdefault("MODELSCOPE_CACHE", os.path.join(BASE, "model_cache"))
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")

OUT_DIR = os.path.join(BASE, "output_api")

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(title="FunClip REST", docs_url="/docs")

_jobs = {}          # id -> dict(status/progress/message/...)
_states = {}        # recog_id -> VideoClipper state（recog_res_raw/timestamp/...）
_clipper = None
_lock = threading.Lock()


def _get_clipper():
    global _clipper
    with _lock:
        if _clipper is None:
            from funasr import AutoModel
            from funclip.videoclipper import VideoClipper

            model = AutoModel(model="paraformer-zh", model_root=os.environ["MODELSCOPE_CACHE"])
            _clipper = VideoClipper(model)
            _clipper.lang = "zh"
    return _clipper


def _set(jid, **kw):
    _jobs[jid].update(kw, ts=time.time())


def _run_recog(jid, video_path):
    try:
        _set(jid, status="running", progress=20, message="加载识别模型…")
        clipper = _get_clipper()
        _set(jid, progress=50, message="识别中…")
        res_text, res_srt, state = clipper.video_recog(video_path, output_dir=OUT_DIR)
        _states[jid] = state
        _set(jid, status="done", progress=100, message="识别完成",
             text=res_text, srt=res_srt)
    except Exception as exc:  # noqa: BLE001
        _set(jid, status="error", message="%s: %s" % (type(exc).__name__, exc))


def _run_clip(jid, recog_id, dest_text, font_size, add_sub):
    try:
        _set(jid, status="running", progress=30, message="裁剪 + 烧字幕…")
        state = _states.get(recog_id)
        if not state:
            return _set(jid, status="error", message="识别任务不存在：%s" % recog_id)
        clipper = _get_clipper()
        clip_file, message, clip_srt = clipper.video_clip(
            dest_text, 0, 0, state, font_size=font_size,
            font_color="white", add_sub=add_sub, output_dir=OUT_DIR)
        if not clip_file:
            # 文本没匹配到语音片段等情况：明确报错，而不是拿目录里的旧文件充数
            return _set(jid, status="error", message="未生成切片：%s" % message)
        _set(jid, status="done", progress=100, message="出片完成",
             file=os.path.basename(clip_file), srt=clip_srt)
    except Exception as exc:  # noqa: BLE001
        _set(jid, status="error", message="%s: %s" % (type(exc).__name__, exc))


class ClipBody(BaseModel):
    recog_id: str
    text: str                 # 要裁剪的原文片段（来自识别全文）
    font_size: int = 32
    add_sub: bool = True      # 是否烧录字幕


@app.get("/api/health")
def health():
    return {"ok": True, "data": {"model_loaded": _clipper is not None,
                                 "recog_cached": len(_states), "jobs": len(_jobs)}}


@app.post("/api/recog")
async def recog(file: UploadFile = File(...)):
    os.makedirs(OUT_DIR, exist_ok=True)
    # 客户端传来的文件名可能带乱码/路径分隔符：只取扩展名，落盘统一用任务前缀命名
    orig_name = os.path.basename(file.filename or "in.mp4")
    ext = os.path.splitext(orig_name)[1].lower() or ".mp4"
    path = os.path.join(OUT_DIR, "%s%s" % (uuid.uuid4().hex[:8], ext))
    with open(path, "wb") as f:
        while chunk := await file.read(1 << 20):
            f.write(chunk)
    jid = uuid.uuid4().hex[:12]
    _jobs[jid] = {"status": "queued", "progress": 0, "message": "排队中",
                  "video": orig_name}
    threading.Thread(target=_run_recog, args=(jid, path), daemon=True).start()
    return {"ok": True, "data": {"task_id": jid}}


@app.get("/api/transcript/{tid}")
def transcript(tid: str):
    job = _jobs.get(tid)
    if not job:
        return JSONResponse({"ok": False, "message": "任务不存在"}, status_code=404)
    return {"ok": True, "data": {k: job.get(k) for k in ("status", "text", "srt", "message")}}


@app.post("/api/clip")
def clip(body: ClipBody):
    jid = uuid.uuid4().hex[:12]
    _jobs[jid] = {"status": "queued", "progress": 0, "message": "排队中"}
    threading.Thread(target=_run_clip,
                     args=(jid, body.recog_id, body.text, body.font_size, body.add_sub),
                     daemon=True).start()
    return {"ok": True, "data": {"task_id": jid}}


@app.get("/api/job/{jid}")
def job(jid: str):
    j = _jobs.get(jid)
    if not j:
        return JSONResponse({"ok": False, "message": "任务不存在"}, status_code=404)
    return {"ok": True, "data": {k: j.get(k) for k in
                                 ("status", "progress", "message", "text", "srt", "file")}}


@app.get("/api/result/{jid}")
def result(jid: str):
    j = _jobs.get(jid)
    if not j or j.get("status") != "done" or not j.get("file"):
        return JSONResponse({"ok": False, "message": "任务不存在或未完成"}, status_code=404)
    return FileResponse(os.path.join(OUT_DIR, j["file"]), filename=j["file"])


if __name__ == "__main__":
    import uvicorn

    os.makedirs(OUT_DIR, exist_ok=True)
    print("FunClip 接口服务  http://127.0.0.1:8335  (docs: /docs)")
    uvicorn.run(app, host="127.0.0.1", port=8335, log_level="warning")
