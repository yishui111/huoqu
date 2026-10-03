# -*- coding: utf-8 -*-
"""
补跑循环：反复检查 11 个测试的报告，缺 PASS 报告的就补跑，直到全绿或达到轮次上限。
本机夜间有其他 AI 任务抢占内存/磁盘，进程偶发被系统掐死，靠多轮补跑磨过坏窗口。

用法：.venv\\Scripts\\python.exe 测试\\补跑循环.py [最大轮数，默认 6]
"""
import glob
import json
import os
import sys
import time

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TEST_DIR)
import run_all_tests as R  # noqa: E402

PROGRESS = os.path.join(R.LOG_DIR, "补跑进度.txt")


def passed(rep_path, started_after):
    if not os.path.exists(rep_path):
        return False
    try:
        with open(rep_path, encoding="utf-8") as f:
            rep = json.load(f)
        return rep.get("status") == "PASS" and os.path.getmtime(rep_path) > started_after
    except Exception:  # noqa: BLE001
        return False


def main():
    max_rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    R.kill_orphan_tests()
    files = sorted(glob.glob(os.path.join(TEST_DIR, "test_*.py")))
    started_after = time.time() - 60

    def log(msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with open(PROGRESS, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    deadline = time.time() + 3 * 3600  # 总时长保险丝：3 小时
    for round_no in range(1, max_rounds + 1):
        pending = [f for f in files
                   if not passed(os.path.join(R.REP_DIR,
                                              os.path.splitext(os.path.basename(f))[0] + ".json"),
                                 started_after)]
        if not pending:
            log(f"第{round_no}轮：11 个测试全部有 PASS 报告，结束。")
            break
        log(f"第{round_no}轮开始，待补跑 {len(pending)} 个："
            + ", ".join(os.path.basename(p) for p in pending))
        for path in pending:
            if time.time() > deadline:
                log("到达 3 小时保险丝，停止。")
                break
            name = os.path.splitext(os.path.basename(path))[0]
            log(f"  补跑 {name} …")
            rep = R.run_one(path)
            log(f"  {name} -> {rep['status']} ({rep['total'] - rep['failed']}"
                f"/{rep['total']}, {rep.get('seconds', 0)}s)")
        if time.time() > deadline:
            break
        still = [f for f in files
                 if not passed(os.path.join(R.REP_DIR,
                                            os.path.splitext(os.path.basename(f))[0] + ".json"),
                               started_after)]
        if still:
            log(f"第{round_no}轮结束，仍缺 {len(still)} 个，休眠 60 秒后继续。")
            time.sleep(60)

    # 最终汇总（只汇总 PASS 报告齐全的口径，报告中如实反映缺项）
    reps = []
    for p in sorted(glob.glob(os.path.join(R.REP_DIR, "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                reps.append(json.load(f))
        except Exception:  # noqa: BLE001
            pass
    out_md = R.write_summary(reps)
    done = sum(1 for f in files
               if passed(os.path.join(R.REP_DIR,
                                      os.path.splitext(os.path.basename(f))[0] + ".json"),
                         started_after))
    log(f"汇总报告: {out_md}")
    log(f"最终结果: {done}/{len(files)} 个测试有本轮 PASS 报告。")
    return 0 if done == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())
