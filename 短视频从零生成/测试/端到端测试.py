# -*- coding: utf-8 -*-
r"""
端到端批量出片测试（可反复运行，产物全部落在本 测试/ 文件夹内）
流程：输入主题 → 本地 Ollama 大模型写文案 → edge-tts 配音
      → 使用 storage/local_videos 里的本地素材 → 自动字幕 → 批量输出 2 条竖屏视频
运行：cmd 下执行  ..\.venv\Scripts\python.exe 测试\端到端测试.py
产物：成片在本文件夹，文案/字幕/配音在 文案与字幕/ 子文件夹，日志为 测试运行日志.txt
      storage/tasks/<任务ID>/ 里保留完整中间文件，本脚本不删除
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent          # 测试/
ROOT = HERE.parent                              # 项目根目录
LOG = HERE / "测试运行日志.txt"
ART_DIR = HERE / "文案与字幕"

CMD = [
    str(ROOT / ".venv" / "Scripts" / "python.exe"),
    str(ROOT / "cli.py"),
    "--video-subject", "打工人为什么一到下午三点就犯困？3个提神冷知识",
    "--video-language", "zh-CN",
    "--video-source", "local",
    "--video-materials", "storage/local_videos/素材A.mp4,storage/local_videos/素材B.mp4,storage/local_videos/素材C.mp4",
    "--video-aspect", "9:16",
    "--video-clip-duration", "3",
    "--video-count", "2",
    "--subtitle-enabled",
]

# cli.py 单任务模式最后一行输出 {"task_id": ..., "result": {"videos": [...], ...}}


def parse_result(stdout: str):
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if line.startswith("{") and '"result"' in line:
            try:
                data = json.loads(line)
            except ValueError:
                continue
            result = data.get("result") or {}
            if result.get("videos"):
                return data, result
    return None, None


def main() -> int:
    print("开始端到端批量测试（2条视频），请耐心等待约 3~8 分钟…", flush=True)
    t0 = time.time()
    try:
        proc = subprocess.run(
            CMD, cwd=str(ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=900,
        )
        stdout, stderr, code = proc.stdout or "", proc.stderr or "", proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        code = -1
        stderr += f"\n===== 超时（{exc.timeout} 秒）=====\n"

    cost = time.time() - t0
    with open(LOG, "w", encoding="utf-8") as f:
        f.write(stdout)
        if stderr:
            f.write("\n===== STDERR =====\n" + stderr)

    data, result = parse_result(stdout)
    copied = []
    if result:
        for v in result["videos"]:
            dst = HERE / Path(v).name
            shutil.copy2(v, dst)
            copied.append(dst.name)
        ART_DIR.mkdir(exist_ok=True)
        task_dir = Path(result["audio_file"]).parent
        for name in ("script.json", "subtitle.srt", "audio.mp3"):
            src = task_dir / name
            if src.exists():
                shutil.copy2(src, ART_DIR / name)

    print((stdout or "")[-2000:])
    if stderr:
        print("----- stderr 末尾 -----")
        print(stderr[-1500:])

    ok = code == 0 and result is not None and len(result["videos"]) >= 1
    print("\n================ 测试结果 ================")
    print(f"退出码: {code}，耗时 {cost:.0f} 秒")
    print(f"任务ID: {data.get('task_id') if data else '未知'}")
    print(f"复制到 测试/ 的成片: {copied or '无'}")
    print(f"文案: {(result or {}).get('script', '')[:80]}…")
    print("结果: 通过" if ok else "结果: 失败（详见 测试运行日志.txt）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
