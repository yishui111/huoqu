# -*- coding: utf-8 -*-
"""测试10：WebUI 启动与关闭 —— launch.py 起服务(8315) → 页面可用 → 关闭FunClip.bat 收掉。

慢测试（启动时要加载识别模型，约 1~2 分钟）。
"""
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from 公共库 import LOG_DIR, ROOT, Tester, ensure_dir, port_busy, run  # noqa: E402

t = Tester("test_10_WebUI启动与关闭脚本")
PORT = 8315

t.group("启动脚本静态检查")
with open(os.path.join(ROOT, "启动FunClip.bat"), encoding="gbk") as f:
    bat_start = f.read()
t.true("启动脚本指向 funclip\\launch.py --port 8315",
       "funclip\\launch.py --port 8315" in bat_start)
t.true("启动脚本注入 NO_PROXY 绕过系统代理", "NO_PROXY=127.0.0.1,localhost" in bat_start)
t.true("启动脚本指向本机 Ollama", "LITELLM_API_BASE=http://127.0.0.1:11434" in bat_start)
t.true("启动脚本把模型缓存收进项目 model_cache", "MODELSCOPE_CACHE" in bat_start)
with open(os.path.join(ROOT, "关闭FunClip.bat"), encoding="gbk") as f:
    bat_stop = f.read()
t.true("关闭脚本会关 WebUI 8315", ":8315" in bat_stop)
t.true("关闭脚本会关接口服务 8335", ":8335" in bat_stop)
t.true("关闭脚本按端口精准 taskkill", "taskkill" in bat_stop)

t.group("WebUI 启动")
if port_busy(PORT):
    t.true(f"端口 {PORT} 启动前空闲", False, "端口已被占用，请先运行 关闭FunClip.bat")
    sys.exit(t.finish())
t.true("端口 8315 启动前空闲", True)

env = os.environ.copy()
env["NO_PROXY"] = "127.0.0.1,localhost"
env["no_proxy"] = "127.0.0.1,localhost"
env["LITELLM_API_BASE"] = "http://127.0.0.1:11434"
env.setdefault("MODELSCOPE_CACHE", os.path.join(ROOT, "model_cache"))
env["PYTHONUTF8"] = "1"
ensure_dir(LOG_DIR)
log = open(os.path.join(LOG_DIR, "WebUI启动.log"), "w", encoding="utf-8")
proc = subprocess.Popen(
    [os.path.join(ROOT, ".venv", "Scripts", "python.exe"),
     os.path.join(ROOT, "funclip", "launch.py"), "--port", str(PORT)],
    cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)

t.true("进程已拉起", proc.poll() is None)

ok = False
body = ""
# 绕过系统代理（Clash），直连本机
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
deadline = time.time() + 300
while time.time() < deadline:
    if proc.poll() is not None:
        break
    try:
        with opener.open(f"http://127.0.0.1:{PORT}/", timeout=3) as r:
            if r.status == 200:
                body = r.read().decode("utf-8", "replace")
                ok = True
                break
    except Exception:  # noqa: BLE001
        time.sleep(2)
t.true("首页 300 秒内返回 200（含模型加载时间）", ok,
       "启动超时或进程退出，详见 测试/产物/日志/WebUI启动.log")
t.true("页面为 Gradio 应用", ok and ("gradio" in body.lower() or "gradio_config" in body),
       body[:100])

config_ok = False
try:
    with opener.open(f"http://127.0.0.1:{PORT}/config", timeout=10) as r:
        cfg = r.read().decode("utf-8", "replace")
    config_ok = "视频输入" in cfg and "识别" in cfg
except Exception as exc:  # noqa: BLE001
    cfg = str(exc)
t.true("组件配置含「视频输入/识别」界面元素", config_ok, cfg[:120])

t.group("关闭脚本实测")
res = run(["cmd", "/c", os.path.join(ROOT, "关闭FunClip.bat")], cwd=ROOT)
t.true("关闭脚本执行成功", res.returncode == 0, res.stderr[:120])
# bat 输出是 GBK 中文，跨编码只校验 ASCII 端口号
t.true("关闭脚本输出包含两个端口号", "8315" in res.stdout and "8335" in res.stdout,
       res.stdout[:120])

freed = True
for _ in range(15):
    if not port_busy(PORT):
        break
    time.sleep(1)
else:
    freed = False
t.true("关闭后 8315 端口已释放", freed)
time.sleep(2)
t.true("WebUI 进程已退出", proc.poll() is not None,
       f"returncode={proc.poll()}")
log.close()

sys.exit(t.finish())
