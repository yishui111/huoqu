# PROJECT_STATUS · 项目进度档案

> **给 AI 助手**:接手本项目前,先完整阅读本文件;每完成一个阶段性工作,**立即更新**本文件
> (当前阶段、已完成、进行中、下一步、更新时间),让下次会话可以无缝接续。

- 上次更新:2026-09-28 深夜(第二次更新;与白天另一会话的记录合并,修正过时结论)
- 项目路径:`G:\xmgousi\获取项目`
- 项目性质:容器目录(外层 git 仓库已初始化,白名单只跟踪我写的脚本/文档)

## 这个项目是什么

收集/部署**三个** AI 内容工具(面向短视频创作/流量变现):

| 子目录 | 是什么 | 状态(2026-09-28 深夜) |
|---|---|---|
| `FunClip/` | 长视频→AI 切片(ASR+LLM选片+裁剪+烧字幕),ModelScope 出品 | ✅ **全链路实测通过**:批量切片 2/2 成功,LLM 选片已接本地 Ollama qwen2.5:3b |
| `MoneyPrinterTurbo/` | AI 短视频从零生成(文案→素材→配音→字幕→成片) | ✅ **全链路实测通过**:批量出片 2/2(本地素材模式,无需 API Key);LLM=本地 Ollama |
| `AI绘画工厂/` | Fooocus 一句话批量出图(壁纸/头像/推文配图,含 批量出图.py+中译英) | ✅ **全链路实测通过**:批量出图 3/3,每张约 9~12 秒(4080) |

每个项目内都有:双击启动/关闭 bat(中文项目名)、`使用说明.md`、`测试/` 文件夹(截图+产物+详细记录)。

测试细节与证据:`各项目/测试/测试记录.md`;白天会话的早期报告在 `测试/测试报告.md`(根级)。

## 当前阶段:三个项目全部可用,进入"逐个补强+找下一个项目"阶段

## 已完成(2026-09-28 白天会话,保留原记录)

- **FunClip**:WebUI + ASR + 按句裁剪 + 烧字幕链路验证(RTF 0.09)
- **AI绘画工厂**:修复 批量出图.py 两个上游更新导致的 bug(`paths_loras` 改名、Enhance 参数段缺失)
- 外层仓库 git 初始化;FunClip/MPT 的上游 .git 改名 `.git.上游备份`;推送到 GitHub(yishui111/huoqu)+ Gitee(fengyanlin/huoqu)

## 已完成(2026-09-28 深夜会话,即本次)

- **全局基建**:修复 Ollama(符号链接目标 `D:\aistore\.ollama` 缺失导致服务崩溃);拉取 qwen3.5:4b(3.4GB)+ qwen2.5:3b(2GB)——三个项目的本地大模型需求全部解锁
- **FunClip**:litellm 接 Ollama 选片;依赖安装;增强 extract_timestamps(兼容无方括号/`-->`/MM:SS 等);改默认 LLM 为 litellm/ollama/qwen2.5:3b;修 4 个启动链路问题(端口冲突 7860→8315、theme.json 相对路径、系统代理 NO_PROXY、gradio 4.44 布尔 schema 500);批量 2/2 实测
- **MoneyPrinterTurbo**:配置 config.toml(LLM=ollama qwen2.5:3b、nvenc);批量出片 2/2(1080×1920,含字幕抽帧验证);qwen3.5:4b 写文案无标点问题→默认改 qwen2.5:3b
- **AI绘画工厂**:torch 2.1.0+cu121 部署成功(**白天会话结论"需换 torch 2.5"已过时**——段错误真因是 model_sampling 的 numpy→torch 转换缺失+孤儿进程占显存/内存压力,已用 1 行 `torch.as_tensor` 补丁+清理解决);web 栈降级(fastapi 0.103.2/starlette 0.27/pydantic 2.5.3 修复 gradio 3.41 页面 500);批量出图 3/3;新增本地大模型中译英层(qwen2.5:3b,含中文检测重试)
- 全部项目补齐:中文 bat 启动/关闭、使用说明.md、测试/ 文件夹(截图+产物+记录)

## 进行中 / 未完成

- MoneyPrinterTurbo 在线素材(Pexels/Pixabay)需要免费 API Key,默认未填(本地素材模式已够用)
- AI绘画工厂:qwen2.5:3b 翻译偶发夹中文(已重试兜底);批量脚本与网页界面不可同时跑(内存),文档已注明
- FunClip:torch 为 CPU 版(RTF 0.03 已够快),想更快可换 CUDA 版

## 下一步

1. 按用户节奏找下一个项目(候选:AI 表情包工厂、MinerU 文档转Markdown、KlicStudio 视频翻译——注意与已有 pyVideoTrans 区分)
2. 各项目产物持续回填 测试/ 文件夹
3. 若并行会话仍活跃:改文件前先 `git status`/重读文件,避免互相覆盖(本次已发生 批量出图.py 被并行修改,已合并双方改动)

## 注意事项

- G 盘为外接 USB 盘,大模型首次加载明显偏慢
- FunClip/MoneyPrinterTurbo 是上游 clone;恢复上游 git 管理只需把 `.git.上游备份` 改回 `.git`
- 本机 7860 端口被 pyVideoTrans 长期占用:新项目选端口避开(当前使用:8315=FunClip, 8188=AI绘画工厂, 8501=MPT, 9610/9602/9885=解说模型工作台)
- 系统代理为 Clash(127.0.0.1:7897):所有本机 Web 服务启动脚本都要带 `NO_PROXY=127.0.0.1,localhost`
- E 盘还有用户自己的 GPT-SoVITS/3D 服务常驻,占用少量显存,属正常现象,勿杀
