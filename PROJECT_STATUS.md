# PROJECT_STATUS · 项目进度档案

> **给 AI 助手**:接手本项目前,先完整阅读本文件;每完成一个阶段性工作,**立即更新**本文件
> (当前阶段、已完成、进行中、下一步、更新时间),让下次会话可以无缝接续。

- 上次更新:2026-09-28(ZCode 逐项目启动测试 + 整理推送)
- 项目路径:`G:\xmgousi\获取项目`
- 项目性质:容器目录(外层 git 仓库已于 2026-09-28 初始化,白名单只跟踪我写的脚本/文档)

## 这个项目是什么

收集/部署四个 AI 内容工具:

| 子目录 | 是什么 | 状态(2026-09-28) |
|---|---|---|
| `FunClip/` | 长视频→AI 切片(ASR+裁剪+烧字幕),ModelScope 出品 | ✅ 已部署,核心链路实测通过 |
| `MoneyPrinterTurbo/` | AI 短视频从零生成(文案→素材→配音→成片) | ⚠ 已 clone+venv,缺 API Key 未出片 |
| `AI绘画工厂/` | Fooocus 一句话批量出图(含 批量出图.py 驱动) | ❌ 本机 torch 原生段错误,待换 torch |
| `ai播客工厂/` | 规划中的播客生成项目 | 空目录 |

测试细节与证据见 `测试/测试报告.md`。

## 当前阶段:FunClip 可用;AI绘画工厂待修环境;MPT 待补 Key

## 已完成(2026-09-28)

- **FunClip**:WebUI + ASR + 按句裁剪 + 烧字幕全链路实测通过(RTF 0.09);LLM 选片需 Ollama qwen2.5:3b(未拉取)
- **AI绘画工厂**:修复 批量出图.py 两个上游更新导致的 bug(`paths_loras` 改名、Enhance 参数段缺失);出图在模型加载阶段段错误(exit 139),四条路径复现,定位为 torch 2.1.0+cu121 原生层与本机不兼容(safetensors/ldm_patched 导入均正常),建议升级 venv torch 到 2.5.x+cu124
- 外层仓库 git 初始化;FunClip/MPT 的上游 .git 改名 `.git.上游备份`(可随时改回),外层白名单跟踪我的脚本
- 推送到 GitHub(yishui111/huoqu)+ Gitee(fengyanlin/huoqu)

## 进行中 / 未完成

- AI绘画工厂:换 torch 版本后重测 批量出图.py
- MoneyPrinterTurbo:补 pexels API key / 本地 LLM(TTS base_url 4123/8880 指向旧机器服务,需迁移)
- Ollama 本机没有模型:FunClip 的 LLM 选片、MPT 的文案生成都依赖,`ollama pull` 后解锁

## 下一步

1. Fooocus venv 升级 torch → 重测出图
2. ollama pull qwen2.5:3b → 补测 FunClip LLM 选片 + MPT 全链路
3. ai播客工厂 立项

## 注意事项

- G 盘为外接 USB 盘,大模型首次加载明显偏慢
- FunClip/MoneyPrinterTurbo 是上游 clone;恢复上游 git 管理只需把 `.git.上游备份` 改回 `.git`
