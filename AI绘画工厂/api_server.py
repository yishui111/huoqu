# -*- coding: utf-8 -*-
"""
AI绘画工厂 · REST 接口服务（端口 8189，纯标准库）

把「一句话批量出图」暴露成异步任务接口。生成在**子进程**里跑
（Fooocus venv 的 批量出图.py）：即便 Fooocus 崩溃（如本机已知的
torch 2.1.0 段错误）也只影响单个任务，服务本身不受影响。

  POST /api/generate   {"prompt":"...", "count":1, "ratio":"1152*896"} → 异步出图
  GET  /api/job/{id}   进度（queued/running/done/error，done 带 images 列表）
  GET  /api/result/{id} 下载第一张图（?all=1 打包 zip）
  GET  /api/health     健康检查

⚠ 当前已知：本机 Fooocus venv 的 torch 在模型加载段错误（exit 139），
  任务会如实返回 error；待按 测试报告.md 升级 torch 后即可出图，接口不变。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
FOOOCUS = os.path.join(BASE, "Fooocus")
PY = os.path.join(FOOOCUS, ".venv", "Scripts", "python.exe")
BATCH = os.path.join(BASE, "批量出图.py")
OUT_DIR = os.path.join(BASE, "output_api")
PORT = 8189
RATIOS = {"1152*896", "896*1152", "1216*832", "832*1216", "1024*1024"}

_jobs = {}


def _run(job_id, prompt, count, ratio):
    job = _jobs[job_id]
    job_dir = os.path.join(OUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    prompts_file = os.path.join(job_dir, "prompts.txt")
    with open(prompts_file, "w", encoding="utf-8") as f:
        f.write("%s | %d | %s\n" % (prompt, count, ratio))
    job.update(status="running", progress=20, message="启动 Fooocus 子进程（首次加载模型数分钟）…")
    try:
        env = dict(os.environ, PYTHONIOENCODING="utf-8",
                   HF_MIRROR="https://hf-mirror.com", HF_ENDPOINT="https://hf-mirror.com")
        proc = subprocess.run([PY, BATCH, prompts_file],
                              cwd=FOOOCUS, env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=3600)
        # 解析产物：优先取脚本打印的绝对路径；否则兜底收集 Fooocus/outputs 近 30 分钟新图
        produced = []
        if proc.stdout:
            produced = [p.strip() for p in proc.stdout.splitlines()
                        if re.match(r"\s*[A-Za-z]:\\.*\.(png|jpg)$", p.strip())
                        and os.path.exists(p.strip())]
        if not produced:
            for dirpath, _, files in os.walk(os.path.join(FOOOCUS, "outputs")):
                for fn in files:
                    p = os.path.join(dirpath, fn)
                    if fn.lower().endswith((".png", ".jpg")) and \
                       time.time() - os.path.getmtime(p) < 1800:
                        produced.append(p)
        if proc.returncode == 0 and produced:
            for p in produced:
                dst = os.path.join(job_dir, os.path.basename(p))
                if os.path.abspath(p) != os.path.abspath(dst):
                    shutil.copy(p, dst)
            job.update(status="done", progress=100, message="出图 %d 张" % len(produced),
                       images=[os.path.join(job_dir, os.path.basename(p)) for p in produced],
                       seconds=None)
        else:
            tail = (proc.stderr or proc.stdout or "")[-400:]
            job.update(status="error", progress=100,
                       message="子进程退出码 %s（139=段错误，见 测试报告.md 的 torch 问题）：%s"
                               % (proc.returncode, tail))
    except Exception as exc:  # noqa: BLE001
        job.update(status="error", message="%s: %s" % (type(exc).__name__, exc))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.address_string(), fmt % args))

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(
            body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _ok(self, data=None, message="ok"):
        self._send(200, {"ok": True, "message": message, "data": data})

    def _fail(self, message, code=400):
        self._send(code, {"ok": False, "message": message})

    def do_GET(self):
        parsed = urlparse(self.path)
        path, qs = parsed.path, parse_qs(parsed.query)
        if path == "/api/health":
            self._ok({"status": "ok", "fooocus_venv": os.path.exists(PY),
                      "note": "生成在子进程执行；本机 torch 段错误期间任务会返回 error"})
        elif path.startswith("/api/job/"):
            job = _jobs.get(path.rsplit("/", 1)[-1])
            if not job:
                return self._fail("任务不存在", 404)
            self._ok({k: v for k, v in job.items() if k != "images"} |
                     {"images": [os.path.basename(p) for p in job.get("images", [])]})
        elif path.startswith("/api/result/"):
            jid = path.rsplit("/", 1)[-1]
            job = _jobs.get(jid)
            if not job or job.get("status") != "done" or not job.get("images"):
                return self._fail("任务不存在或未完成", 404)
            if qs.get("all", ["0"])[0] == "1":
                buf = BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for p in job["images"]:
                        zf.write(p, os.path.basename(p))
                self._send(200, buf.getvalue(), "application/zip")
            else:
                data = open(job["images"][0], "rb").read()
                self._send(200, data, "image/png")
        else:
            self._fail("unknown endpoint: %s" % path, 404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/generate":
            return self._fail("unknown endpoint", 404)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return self._fail("请求体不是合法 JSON")
        prompt = (body.get("prompt") or "").strip()
        if not prompt:
            return self._fail("prompt 不能为空")
        count = int(body.get("count") or 1)
        ratio = body.get("ratio") or "1152*896"
        if ratio not in RATIOS:
            return self._fail("ratio 仅支持 %s" % sorted(RATIOS))
        jid = uuid.uuid4().hex[:12]
        _jobs[jid] = {"status": "queued", "progress": 0, "message": "排队中",
                      "prompt": prompt, "count": count, "ratio": ratio}
        threading.Thread(target=_run, args=(jid, prompt, count, ratio), daemon=True).start()
        self._ok({"job_id": jid}, "已排队")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    print("AI绘画工厂 接口服务  http://127.0.0.1:%d  （POST /api/generate）" % PORT)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
