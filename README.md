# 获取项目 · 容器仓库

四个「拿现成开源项目 + 我自己的启动/接口/批量层」的子项目。**上游本体不入库**，
本仓库只收我写的脚本、文档与测试产物；换机器部署时按下表把上游放回对应目录即可。

| 子项目 | 上游 | 我加的东西 | 默认端口 |
|---|---|---|---|
| `AI绘画工厂/` | [Fooocus](https://github.com/lllyasviel/Fooocus)（下载后放 `AI绘画工厂/Fooocus/`） | REST 接口服务 + 批量出图驱动 | 8189 |
| `短视频从零生成/` | [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo)（下载后放本目录） | 批量出片测试、启动/关闭脚本、使用/接口文档 | 8080 |
| `长视频一键出爆款切片/` | [FunClip](https://github.com/modelscope/FunClip)（上游源码放 `funclip/` 子目录） | REST 接口服务（异步识别/裁剪/烧字幕） | 8335 |
| `测试/` | — | FunClip 实测产物归档 | — |

## 换机部署要点

1. **上游拉取**：按上表把上游项目克隆/下载到指定位置（目录名保持一致）。
2. **依赖**：各子项目在自己的 `.venv` / `venv` 里装依赖（见各自使用说明；Fooocus 自带 `requirements.txt`，MPT 用本仓库留存的 `requirements.txt`）。
3. **敏感配置**：`短视频从零生成/config.toml` 不入库——复制 `config.example.toml` 后填入自己的 API key。
4. **模型权重**：Fooocus checkpoints、FunClip 的 `model_cache/`（asafaya/whisper 等）首次运行自动下载或按文档手动放置，均不入库。
