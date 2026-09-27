# -*- coding: utf-8 -*-
"""
FunClip 端到端批量切片测试（可反复运行）
流程：识别(test_videos/*.mp4 全部视频) → 本地 Ollama 大模型(qwen2.5:3b)选高光片段
      → 按时间戳裁剪并烧录字幕
运行：.venv\\Scripts\\python.exe 批量切片.py
结果：切片输出在 output/ 目录，日志在 测试运行日志.txt
"""
import glob
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
os.environ["LITELLM_API_BASE"] = "http://127.0.0.1:11434"
os.environ.setdefault("MODELSCOPE_CACHE", os.path.join(ROOT, "model_cache"))

sys.path.insert(0, os.path.join(ROOT, "funclip"))
os.chdir(os.path.join(ROOT, "funclip"))

SYSTEM_PROMPT = ("你是一个视频srt字幕分析剪辑器，输入视频的srt字幕，"
                 "分析其中的精彩且尽可能连续的片段并裁剪出来，输出四条以内的片段，"
                 "将片段中在时间上连续的多个句子及它们的时间戳合并为一条，"
                 "注意确保文字与时间戳的正确匹配。输出需严格按照如下格式："
                 "1. [开始时间-结束时间] 文本，注意其中的连接符是“-”。"
                 "时间戳必须保留方括号、使用单条短横线“-”连接，"
                 "例如 [00:00:02,290-00:00:07,400]，不要使用 --> 或其他符号")
USER_HEAD = "这是待裁剪的视频srt字幕："
LLM_MODEL = "ollama/qwen2.5:3b"


def main():
    from funasr import AutoModel
    from videoclipper import VideoClipper
    from llm.litellm_api import litellm_call
    from utils.trans_utils import extract_timestamps

    videos = sorted(glob.glob(os.path.join(ROOT, "test_videos", "*.mp4")))
    if not videos:
        print("test_videos 下没有视频，请先运行 制作测试素材.py")
        sys.exit(1)

    print("正在加载本地识别模型（首次会自动下载，约1.5GB）…")
    t0 = time.time()
    asr = AutoModel(
        model="iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
        vad_model="damo/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        punc_model="damo/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        spk_model="damo/speech_campplus_sv_zh-cn_16k-common",
        disable_update=True,
    )
    clipper = VideoClipper(asr)
    clipper.lang = "zh"
    print(f"模型就绪，耗时 {time.time()-t0:.0f} 秒")

    results = []
    for video in videos:
        name = os.path.splitext(os.path.basename(video))[0]
        print(f"\n===== 处理: {name} =====")
        t1 = time.time()
        res_text, res_srt, state = clipper.video_recog(video, "no")
        print(f"识别完成({time.time()-t1:.0f}秒)，字幕 {len(res_srt.splitlines())} 行")
        print("识别文本:", res_text[:120].replace("\n", " "), "…")

        t2 = time.time()
        llm_res = litellm_call("", LLM_MODEL, USER_HEAD + "\n" + res_srt, SYSTEM_PROMPT)
        print(f"大模型选片({time.time()-t2:.0f}秒):\n{llm_res}")

        ts = extract_timestamps(llm_res)
        if not ts:
            print("!! 大模型没有解析出时间戳，跳过该视频")
            results.append((name, "NO_TIMESTAMP"))
            continue
        out_dir = os.path.join(ROOT, "output", name)
        clip_file, message, clip_srt = clipper.video_clip(
            "", 0, 100, state, font_size=32, font_color="white",
            add_sub=True, timestamp_list=ts, output_dir=out_dir)
        print(f"切片完成: {clip_file}")
        print(f"裁剪日志: {message}")
        results.append((name, clip_file))

    print("\n===== 批量结果汇总 =====")
    ok = 0
    for name, r in results:
        ok += 1 if r not in ("NO_TIMESTAMP",) and r else 0
        print(f"  {name}: {r}")
    print(f"成功 {ok}/{len(results)}")
    sys.exit(0 if ok == len(results) else 1)


if __name__ == "__main__":
    main()
