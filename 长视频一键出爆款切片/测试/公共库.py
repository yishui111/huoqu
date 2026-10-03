# -*- coding: utf-8 -*-
"""
FunClip 测试公共库：细粒度断言收集、产物路径、ffprobe/ffmpeg 小工具。

约定：
- 所有测试产物统一放在 测试/产物/ 下（日志、报告、转写、切片、抽帧、api、状态）。
- 每个测试文件末尾调用 Tester.finish()，结果 JSON 落盘到 测试/产物/报告/，
  由 run_all_tests.py 汇总成 测试报告.md / 测试报告.json。
"""
import json
import os
import subprocess
import sys
import time

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TEST_DIR)
ART = os.path.join(TEST_DIR, "产物")
VENV_PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")

LOG_DIR = os.path.join(ART, "日志")
REP_DIR = os.path.join(ART, "报告")
TRAN_DIR = os.path.join(ART, "转写")
CLIP_DIR = os.path.join(ART, "切片")
FRAME_DIR = os.path.join(ART, "抽帧")
API_DIR = os.path.join(ART, "api")
STATE_DIR = os.path.join(ART, "状态")
VIDEO1 = os.path.join(ROOT, "test_videos", "测试长视频1-生活冷知识.mp4")
VIDEO2 = os.path.join(ROOT, "test_videos", "测试长视频2-健身干货.mp4")


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


class Tester:
    """逐条断言收集器：单条失败不中断，最后统一落盘并返回退出码。"""

    def __init__(self, name):
        # 报告文件名必须与测试脚本文件名一致，run_all_tests.py 才能读到
        script = os.path.splitext(os.path.basename(sys.argv[0] or ""))[0]
        self.name = script if script.startswith("test_") else name
        self.rows = []  # [组, 用例, 是否通过, 说明]
        self.t0 = time.time()
        self._g = "默认"

    def group(self, g):
        self._g = g

    def _record(self, case, ok, detail=""):
        self.rows.append([self._g, case, bool(ok), str(detail)])
        mark = "PASS" if ok else "FAIL"
        line = f"  [{mark}] {self._g} / {case}"
        if detail and not ok:
            line += f"  -> {detail}"
        print(line, flush=True)

    def true(self, case, cond, detail=""):
        self._record(case, cond, detail)

    def eq(self, case, actual, expected):
        ok = actual == expected
        self._record(case, ok, "" if ok else f"期望 {expected!r}，实际 {actual!r}")

    def near(self, case, actual, expected, tol):
        ok = abs(actual - expected) <= tol
        self._record(case, ok, "" if ok else f"期望 {expected}±{tol}，实际 {actual}")

    def raises(self, case, exc_type, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except exc_type as exc:
            self._record(case, True, type(exc).__name__)
        except Exception as exc:  # noqa: BLE001
            self._record(case, False,
                         f"抛出了 {type(exc).__name__}: {exc}，期望 {exc_type.__name__}")
        else:
            self._record(case, False, f"未抛出 {exc_type.__name__}")

    def finish(self):
        total = len(self.rows)
        failed = [r for r in self.rows if not r[2]]
        dt = time.time() - self.t0
        ensure_dir(REP_DIR)
        report = {
            "name": self.name,
            "status": "PASS" if not failed else "FAIL",
            "total": total,
            "failed": len(failed),
            "seconds": round(dt, 1),
            "cases": self.rows,
        }
        path = os.path.join(REP_DIR, self.name + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        print(f"\n== {self.name}: {'全部通过' if not failed else '存在失败'} "
              f"{total - len(failed)}/{total}  用时 {dt:.0f}s ==", flush=True)
        return 0 if not failed else 1


def run(cmd, **kw):
    """跑外部命令，显式 UTF-8 解码，避免中文乱码。"""
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def ffprobe_info(path):
    res = run(["ffprobe", "-v", "error", "-print_format", "json",
               "-show_format", "-show_streams", path])
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {res.stderr[:300]}")
    return json.loads(res.stdout)


def ffprobe_duration(path):
    return float(ffprobe_info(path)["format"]["duration"])


def ffmpeg_run(args):
    res = run(["ffmpeg", "-y", "-loglevel", "error"] + args)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {res.stderr[:300]}")
    return res


def extract_frame(video_path, at_sec, out_png):
    ensure_dir(os.path.dirname(out_png))
    ffmpeg_run(["-ss", str(at_sec), "-i", video_path,
                "-frames:v", "1", out_png])
    return out_png


def port_busy(port):
    """True 表示端口已有进程在监听。"""
    res = run(["netstat", "-ano", "-p", "tcp"])
    for line in res.stdout.splitlines():
        if f":{port}" in line and "LISTENING" in line.upper():
            return True
    return False
