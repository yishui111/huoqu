# -*- coding: utf-8 -*-
"""
FunClip 测试总入口：依次运行本目录下所有 test_*.py，并汇总成测试报告。

用法（在项目根目录）：
  .venv\\Scripts\\python.exe 测试\\run_all_tests.py            # 全量
  .venv\\Scripts\\python.exe 测试\\run_all_tests.py --quick     # 跳过慢测试(端到端/REST/WebUI/LLM)
  .venv\\Scripts\\python.exe 测试\\run_all_tests.py --only REST # 只跑名字含关键词的
  .venv\\Scripts\\python.exe 测试\\run_all_tests.py --close     # 全部通过后运行 关闭FunClip.bat 收尾
"""
import glob
import json
import os
import re
import subprocess
import sys
import time

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, TEST_DIR)
from 公共库 import VENV_PY, LOG_DIR, REP_DIR, ensure_dir, port_busy, run  # noqa: E402

SLOW = ("test_08", "test_09", "test_10", "test_11")


def kill_orphan_tests():
    """清理遗留的 python 测试/runner 进程。

    .venv\\Scripts\\python.exe 只是个启动器，真 python 是它的子进程——
    上层被杀时常留下真 python 孤儿，继续占用模型与产物文件，毒化下一次运行。
    """
    res = run(["wmic", "process", "where", "name='python.exe'",
               "get", "ProcessId,ParentProcessId,CommandLine", "/format:list"])
    own = {os.getpid(), os.getppid()}
    for block in res.stdout.split("\n\n"):
        m = re.search(r"ProcessId=(\d+)", block)
        if not m:
            continue
        pid = int(m.group(1))
        if pid in own:
            continue
        if "run_all_tests" in block and not re.search(r"test_0\d|test_1\d", block):
            # 别的 runner 孤儿实例：也会清空报告目录，必须一并清掉
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True)
            print(f"    (清理遗留 runner 进程 PID {pid})", flush=True)
        elif re.search(r"test_0\d|test_1\d", block):
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           capture_output=True)
            print(f"    (清理遗留测试进程 PID {pid})", flush=True)


def run_one(path, tries=3):
    """跑单个测试；无报告产出（导入偶发崩溃/卡死）自动重跑，超时整树终止。"""
    name = os.path.splitext(os.path.basename(path))[0]
    ensure_dir(LOG_DIR)
    log_path = os.path.join(LOG_DIR, name + ".log")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONFAULTHANDLER"] = "1"
    # 关掉 gradio 遥测、本机地址绕代理：否则外网请求被系统代理卡住会拖慢/拖死导入
    env["GRADIO_ANALYTICS_ENABLED"] = "False"
    env.setdefault("NO_PROXY", "127.0.0.1,localhost")
    env.setdefault("no_proxy", "127.0.0.1,localhost")
    rep_path = os.path.join(REP_DIR, name + ".json")
    t0 = time.time()
    for attempt in range(tries):
        if attempt:
            time.sleep(10)  # 给系统喘口气再重试
        p = subprocess.Popen([VENV_PY, "-u", "-X", "faulthandler", path],
                             cwd=ROOT, env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        try:
            out, _ = p.communicate(timeout=1200)
            returncode = p.returncode
        except subprocess.TimeoutExpired:
            # venv 启动器+真 python 是两层进程，必须 /T 整树杀
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                           capture_output=True)
            try:
                out, _ = p.communicate(timeout=30)
            except Exception:  # noqa: BLE001
                out = ""
            returncode = -9
            print("    (超过 1200 秒，已整树终止)", flush=True)
        dt = time.time() - t0
        stdout = out if isinstance(out, str) else (out or b"").decode(
            "utf-8", "replace")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(stdout)
        if os.path.exists(rep_path) or attempt == tries - 1:
            break
        print(f"    (无报告产出，疑似导入崩溃，重试 {attempt + 1}/{tries - 1})",
              flush=True)
        kill_orphan_tests()
    dt = time.time() - t0
    if os.path.exists(rep_path):
        with open(rep_path, encoding="utf-8") as f:
            rep = json.load(f)
    else:  # 测试脚本本身崩了（重试后仍无报告）
        rep = {"name": name, "status": "CRASH", "total": 0, "failed": 0,
               "seconds": round(dt, 1), "cases": []}
    rep["log"] = log_path
    rep["exitcode"] = returncode
    tail = (stdout or "").strip().splitlines()[-5:]
    rep["crash_tail"] = "\n".join(tail)
    return rep


def write_summary(reps):
    out_json = os.path.join(TEST_DIR, "测试报告.json")
    out_md = os.path.join(TEST_DIR, "测试报告.md")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(reps, f, ensure_ascii=False, indent=1)

    total = sum(r["total"] for r in reps)
    failed = sum(r["failed"] for r in reps)
    secs = sum(r.get("seconds", 0) for r in reps)
    lines = ["# FunClip 测试报告", "",
             "- 运行时间：" + time.strftime('%Y-%m-%d %H:%M:%S'),
             f"- 汇总：{'✅ 全部通过' if failed == 0 else '❌ 存在失败'}，"
             f"用例 {total - failed}/{total}，总耗时 {secs:.0f} 秒", "",
             "| 测试 | 结果 | 用例 | 失败 | 耗时 |", "|---|---|---|---|---|"]
    for r in reps:
        mark = "✅ PASS" if r["status"] == "PASS" else f"❌ {r['status']}"
        lines.append(f"| {r['name']} | {mark} | {r['total']} | {r['failed']} "
                     f"| {r.get('seconds', 0)}s |")
    lines.append("")
    for r in reps:
        if r["status"] != "PASS":
            lines += [f"## {r['name']} 失败明细", ""]
            for g, c, ok, d in r["cases"]:
                if not ok:
                    lines.append(f"- {g} / {c}：{d}")
            if r["status"] == "CRASH":
                lines.append(f"- 测试脚本崩溃，日志末尾：\n```\n{r['crash_tail']}\n```")
            lines.append("")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_md


def main():
    args = sys.argv[1:]
    quick = "--quick" in args
    close = "--close" in args
    summarize_only = "--summarize-only" in args
    only = None
    if "--only" in args:
        only = args[args.index("--only") + 1]

    if summarize_only:
        reps = []
        for p in sorted(glob.glob(os.path.join(REP_DIR, "*.json"))):
            with open(p, encoding="utf-8") as f:
                reps.append(json.load(f))
        report_md = write_summary(reps)
        all_ok = all(r["status"] == "PASS" for r in reps)
        print(f"报告: {report_md}", flush=True)
        print(f"结论: {'✅ 全部通过' if all_ok else '❌ 存在失败'}", flush=True)
        return 0 if all_ok else 1

    kill_orphan_tests()
    files = sorted(glob.glob(os.path.join(TEST_DIR, "test_*.py")))
    if only:
        files = [f for f in files if only in os.path.basename(f)]
    if quick:
        files = [f for f in files
                 if not os.path.basename(f).startswith(SLOW)]

    print(f"FunClip 测试：共 {len(files)} 个测试文件"
          f"{'（quick 模式）' if quick else ''}\n", flush=True)
    ensure_dir(REP_DIR)
    for old in glob.glob(os.path.join(REP_DIR, "*.json")):
        os.remove(old)

    reps = []
    for path in files:
        name = os.path.basename(path)
        print(f"==== {name} ====", flush=True)
        rep = run_one(path)
        reps.append(rep)
        mark = "PASS" if rep["status"] == "PASS" else rep["status"]
        print(f"---- {name}: {mark} ({rep['total'] - rep['failed']}/"
              f"{rep['total']}, {rep['seconds']}s) ----\n", flush=True)

    report_md = write_summary(reps)
    all_ok = all(r["status"] == "PASS" for r in reps)

    if close:
        if all_ok:
            print("\n全部通过，运行 关闭FunClip.bat 收尾…", flush=True)
            res = run(["cmd", "/c", os.path.join(ROOT, "关闭FunClip.bat")],
                      cwd=ROOT)
            print(res.stdout.strip(), flush=True)
            state = "still-listening" if (port_busy(8315) or port_busy(8335)) \
                else "closed"
            print(f"收尾后端口状态: {state}", flush=True)
        else:
            print("\n存在失败用例，跳过关闭动作。", flush=True)

    print(f"\n报告: {report_md}", flush=True)
    print(f"结论: {'✅ 全部通过' if all_ok else '❌ 存在失败'}", flush=True)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
