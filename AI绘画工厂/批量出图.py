# -*- coding: utf-8 -*-
"""
AI绘画工厂 · 批量出图脚本（无需打开网页，进程内直接驱动 Fooocus）
=================================================================
用法：
  1. 在 批量提示词.txt 里一行一个提示词（可中文，会自动加风格翻译由 Fooocus 处理）
     格式：提示词 | 张数 | 比例     （张数/比例可省略，默认各 1 张 / 1152*896）
     比例可选：1152*896(横) 896*1152(竖) 1216*832(宽) 832*1216(长图) 1024*1024(方)
  2. 双击运行本脚本（或命令行 .venv\\Scripts\\python.exe 批量出图.py）
  3. 图片保存在 Fooocus/outputs/当天日期/，脚本结束会打印全部文件路径

注意：首次运行会先下载/加载模型（数分钟），之后每次只需几十秒。
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
FOOOCUS = os.path.join(ROOT, "Fooocus")
os.chdir(FOOOCUS)
sys.path.insert(0, FOOOCUS)
os.environ.setdefault("HF_MIRROR", "https://hf-mirror.com")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

PROMPTS_FILE = os.path.join(ROOT, "批量提示词.txt")
DEFAULT_COUNT = 1
DEFAULT_RATIO = "1152*896"


def parse_prompts(path):
    tasks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            prompt = parts[0]
            count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else DEFAULT_COUNT
            ratio = parts[2] if len(parts) > 2 and parts[2] else DEFAULT_RATIO
            tasks.append((prompt, count, ratio))
    return tasks


def ensure_models_downloaded():
    """首次使用：把默认预设的模型文件补齐（已存在则跳过）。"""
    import json
    import modules.config as config
    from modules.model_loader import load_file_from_url

    preset_path = os.path.join("presets", "default.json")
    with open(preset_path, encoding="utf-8") as f:
        preset = json.load(f)
    for key, dirpath in [("checkpoint_downloads", config.paths_checkpoints[0]),
                         ("embeddings_downloads", config.path_embeddings),
                         ("lora_downloads", config.paths_loras[0]),  # 上游属性为列表 paths_loras（配置键才叫 path_loras）
                         ("vae_downloads", config.path_vae)]:
        for file_name, url in preset.get(key, {}).items():
            load_file_from_url(url=url, model_dir=dirpath, file_name=file_name)
    # Fooocus 自带的小文件（提示词扩写、预览VAE等）
    misc = [
        ("https://huggingface.co/lllyasviel/misc/resolve/main/fooocus_expansion.bin", config.path_fooocus_expansion, "fooocus_expansion.bin"),
        ("https://huggingface.co/lllyasviel/misc/resolve/main/xlvaeapp.pth", config.path_vae_approx, "xlvaeapp.pth"),
        ("https://huggingface.co/lllyasviel/misc/resolve/main/vaeapp_sd15.pt", config.path_vae_approx, "vaeapp_sd15.pt"),
        ("https://huggingface.co/mashb1t/misc/resolve/main/xl-to-v1_interposer-v4.0.safetensors", config.path_vae_approx, "xl-to-v1_interposer-v4.0.safetensors"),
    ]
    for url, dirpath, name in misc:
        load_file_from_url(url=url.replace("https://huggingface.co", os.environ["HF_MIRROR"]), model_dir=dirpath, file_name=name)


def build_args(prompt, count, ratio):
    import modules.config as config
    from modules.flags import MetadataScheme, ip_list

    args = []
    args.append(False)                                   # generate_image_grid
    args.append(prompt)                                  # prompt
    args.append(config.default_prompt_negative)          # negative_prompt
    args.append(list(config.default_styles))             # style_selections
    args.append(config.default_performance)              # performance_selection
    args.append(ratio)                                   # aspect_ratios_selection
    args.append(count)                                   # image_number
    args.append(config.default_output_format)            # output_format
    args.append(-1)                                      # seed (随机)
    args.append(False)                                   # read_wildcards_in_order
    args.append(config.default_sample_sharpness)         # sharpness
    args.append(config.default_cfg_scale)                # cfg_scale
    args.append(config.default_base_model_name)          # base_model_name
    args.append(config.default_refiner_model_name)       # refiner_model_name
    args.append(config.default_refiner_switch)           # refiner_switch
    loras = list(config.default_loras)[:config.default_max_lora_number]
    for item in loras:                                   # 每个槽位：enabled, name, weight
        if len(item) == 3:
            enabled, name, weight = item
        else:
            enabled, name, weight = True, item[0], item[1]
        args.extend([bool(enabled), str(name), float(weight)])
    n_slots = config.default_max_lora_number - len(loras)
    for _ in range(n_slots):
        args.extend([False, "None", 0.0])
    args.append(False)                                   # input_image_checkbox
    args.append("uov")                                   # current_tab
    args.append("Disabled")                              # uov_method
    args.append(None)                                    # uov_input_image
    args.append([])                                      # outpaint_selections
    args.append(None)                                    # inpaint_input_image
    args.append("")                                      # inpaint_additional_prompt
    args.append(None)                                    # inpaint_mask_image_upload
    args.append(True)                                    # disable_preview
    args.append(False)                                   # disable_intermediate_results
    args.append(False)                                   # disable_seed_increment
    args.append(False)                                   # black_out_nsfw
    args.append(1.5)                                     # adm_scaler_positive
    args.append(0.8)                                     # adm_scaler_negative
    args.append(0.3)                                     # adm_scaler_end
    args.append(7.0)                                     # adaptive_cfg
    args.append(-2)                                      # clip_skip
    args.append(config.default_sampler)                  # sampler_name
    args.append(config.default_scheduler)                # scheduler_name
    args.append(config.default_vae)                      # vae_name
    args.extend([-1] * 8)                                # overwrite_step/switch/width/height/vary/upscale + mixing×2
    args.append(False)                                   # debugging_cn_preprocessor
    args.append(False)                                   # skipping_cn_preprocessor
    args.append(64)                                      # canny_low_threshold
    args.append(128)                                     # canny_high_threshold
    args.append("Joint")                                 # refiner_swap_method
    args.append(0.25)                                    # controlnet_softness
    args.append(False)                                   # freeu_enabled
    args.extend([1.01, 1.02, 1.0, 1.0])                  # freeu b1 b2 s1 s2
    args.append(False)                                   # debugging_inpaint_preprocessor
    args.append(False)                                   # inpaint_disable_initial_latent
    args.append("None")                                  # inpaint_engine
    args.append(0.85)                                    # inpaint_strength
    args.append(0.618)                                   # inpaint_respective_field
    args.append(False)                                   # inpaint_advanced_masking_checkbox
    args.append(False)                                   # invert_mask_checkbox
    args.append(0)                                       # inpaint_erode_or_dilate
    args.append(False)                                   # save_final_enhanced_image_only
    args.append(False)                                   # save_metadata_to_images
    args.append(MetadataScheme.FOOOCUS.value)            # metadata_scheme
    for _ in range(config.default_controlnet_image_count):
        args.extend([None, 0.5, 0.6, ip_list[0]])        # cn_img, cn_stop, cn_weight, cn_type
    args.append(False)                                   # debugging_dino
    args.append(0)                                       # dino_erode_or_dilate
    args.append(False)                                   # debugging_enhance_masks_checkbox
    # ---- Enhance 区段（上游更新后新增；AsyncTask 从尾部 pop，顺序不可乱）----
    args.append(None)                                    # enhance_input_image
    args.append(getattr(config, "default_enhance_checkbox", False))   # enhance_checkbox
    args.append(getattr(config, "default_enhance_uov_method", "Disabled"))       # enhance_uov_method
    args.append(getattr(config, "default_enhance_uov_processing_order", 0))      # enhance_uov_processing_order
    args.append(getattr(config, "default_enhance_uov_prompt_type", "Original Prompts"))  # enhance_uov_prompt_type
    for _ in range(config.default_enhance_tabs):         # 每个增强 tab 16 个值（全部禁用，仅类型占位）
        args.extend([False, "", "", "",                   # enabled, mask_dino_prompt, prompt, negative
                     "sam", "upper", "vit_b",             # mask_model, cloth_category, sam_model
                     0.4, 0.3, 10,                        # text_threshold, box_threshold, max_detections
                     False, "None", 0.5, 0.618,           # inpaint_disable_initial_latent, engine, strength, respective_field
                     0, False])                           # erode_or_dilate, mask_invert
    return args


def main():
    if not os.path.exists(PROMPTS_FILE):
        with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
            f.write("示例：夕阳下的海滩，金色波浪，电影感 | 1 | 1152*896\n")
        print(f"已生成提示词模板 {PROMPTS_FILE}，编辑后再运行本脚本")
        return

    tasks = parse_prompts(PROMPTS_FILE)
    if not tasks:
        print("提示词文件是空的")
        return
    total = sum(c for _, c, _ in tasks)
    print(f"共 {len(tasks)} 个提示词，{total} 张图。首次运行需加载模型，请耐心…")

    ensure_models_downloaded()

    import modules.async_worker as worker
    import modules.config as config

    all_results = []
    for prompt, count, ratio in tasks:
        print(f"\n>>> 生成：{prompt} × {count} @ {ratio}")
        t0 = time.time()
        task = worker.AsyncTask(args=build_args(prompt, count, ratio))
        worker.async_tasks.append(task)
        expected = count
        while len(task.results) < expected:
            time.sleep(1)
            if task.last_stop:
                break
        cost = time.time() - t0
        ok = [p for p in task.results if isinstance(p, str) and os.path.exists(p)]
        print(f"    完成，耗时 {cost:.0f} 秒，出图 {len(ok)}/{expected} 张")
        for p in ok:
            print(f"    {p}")
        all_results.extend(ok)

    print(f"\n===== 批量完成：共 {len(all_results)} 张图 =====")
    out_copy = os.path.join(ROOT, "测试", "产物")
    if all_results:
        import shutil
        os.makedirs(out_copy, exist_ok=True)
        for p in all_results:
            shutil.copy(p, out_copy)
        print(f"已复制到 {out_copy}")


if __name__ == "__main__":
    main()
