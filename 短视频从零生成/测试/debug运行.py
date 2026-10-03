# -*- coding: utf-8 -*-
r"""
调试包装器：完整跑 cli.py，但兜住一切 BaseException（含 SystemExit）。
背景：端到端流水线在成片渲染阶段"无日志、无堆栈、退出码 1"地静默退出，
普通 except Exception 抓不住 SystemExit/KeyboardInterrupt，此脚本用于让
真凶现形。定位问题后可删除。
运行：项目根目录下执行
  .venv\Scripts\python.exe 测试\debug运行.py <cli.py 的原参数...>
"""
import faulthandler
import runpy
import sys
import threading
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

faulthandler.enable()
# 任何线程里的未捕获异常也打出来（默认只打主线程或直接吞掉）
threading.excepthook = lambda args: (
    print(f"!!! THREAD EXCEPTION {args.exc_type.__name__}: {args.exc_value!r}", file=sys.stderr, flush=True),
    traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback, file=sys.stderr),
)

sys.argv = ["cli.py"] + sys.argv[1:]
print(f"!!! debug wrapper argv = {sys.argv}", file=sys.stderr, flush=True)

try:
    runpy.run_path(str(ROOT / "cli.py"), run_name="__main__")
except SystemExit as e:
    print(f"!!! SystemExit code={e.code!r}", file=sys.stderr, flush=True)
    if e.code not in (0, None):
        print("!!! 上面的日志末尾就是退出前的最后输出；若未见任何错误日志，说明异常来自更底层", file=sys.stderr, flush=True)
    raise
except BaseException as e:
    print(f"!!! CAUGHT {type(e).__name__}: {e!r}", file=sys.stderr, flush=True)
    traceback.print_exc()
    raise
