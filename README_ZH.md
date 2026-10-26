# ComfyUI MOSS Base+SFT Merge Presets

[English](README.md) | **简体中文**

[![ComfyUI](https://img.shields.io/badge/ComfyUI-custom_node-blue)](https://github.com/comfyanonymous/ComfyUI)
[![MOSS-Image](https://img.shields.io/badge/Model-MOSS--Image-orange)](https://github.com/OpenMOSS/MOSS-Image)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
一个用于 **MOSS-Image Base + SFT** 的 ComfyUI 自定义节点，提供可复现的预设融合和完整的逐层手调模式。

目标是：**保留 Base 的构图与自然写实感，同时吸收 SFT 的文字、材质和微细节能力。**

> 非官方社区项目，与 OpenMOSS、MOSI 或 ComfyUI 官方无隶属关系。

## 效果预览

材质与文字预览从左到右依次为：**Base、SFT、Base-preserve、Balanced、SFT-detail**。人物预览还包含 **Balanced** 在强度 **0.1** 和 **0.3** 下的结果。

### 人物肖像

![人物预设对比](assets/portrait-presets.jpg)

### 材质与写实感

![茶壶预设对比](assets/teapot-presets.jpg)

### 文字与图形细节

![海报预设对比](assets/poster-presets.jpg)

## 功能

- 一键选择 `Base-preserve`、`Balanced`、`SFT-detail` 三档预设。
- `Custom` 模式显示全部 51 个融合组件。
- 支持 MOSS-Image 全部 42 个 DiT block 逐层调节。
- `merge_info` 实时显示经过 `strength` 缩放后的有效层权重。
- 除 ComfyUI 本身外不需要额外 Python 依赖。
- 原生支持 **int8c / convrot Base + SFT** 融合。
- 兼容 ComfyUI 原生 MOSS-Image 加载和采样链。
- 可与 ComfyUI 内置 **ModelSave** 和仅模型 LoRA 加载节点串联使用。

## 环境要求

- 推荐 ComfyUI `0.42.0` 或更新版本。
- 官方 MOSS-Image Base / SFT 权重：
  - [MOSS-Image-Base](https://huggingface.co/OpenMOSS-Team/MOSS-Image-Base)
  - [MOSS-Image-SFT](https://huggingface.co/OpenMOSS-Team/MOSS-Image-SFT)
- 支持 int8c / convrot 量化格式的 Base 和 SFT 扩散模型。
- ComfyUI 兼容的 MOSS-Image 文本编码器和 Flux.2 VAE。
- 已在 Windows、RTX 5090、ComfyUI 0.42.0 上测试。

### int8c / convrot 兼容性

节点支持 **int8c Base + int8c SFT** 双量化模型融合：

- `base_model` 与 `sft_model` 可以同时是 int8c / convrot 模型。
- 融合时由 ComfyUI 原生量化补丁链完成：反量化 SFT 权重、与 Base 做组件级插值、再按 Base 模型的量化布局重新量化。
- 输出模型保持 `base_model` 的 int8c 量化布局，不会退化为 BF16。
- `weight_scale`、`comfy_quant` 等量化元数据不会被当作普通权重融合；缩放参数会随反量化/重量化过程重新生成。
- 第一次加载或首次应用补丁时会比 BF16 融合慢一些，这属于量化权重按需反量化的正常开销。

## 安装

把仓库克隆到 ComfyUI 的 `custom_nodes` 目录：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/slmonker/ComfyUI-MOSS-Merge-Presets.git
```

重启 ComfyUI。

## 使用

1. 添加两个扩散模型加载器：
   - 一个加载 MOSS-Image Base；
   - 一个加载 MOSS-Image SFT。
2. 在分类 `model/merging/moss` 中添加 **MOSS Base+SFT Merge Preset**。
   - 当前 ComfyUI 前端中，请在节点库里**双击**节点名称添加；单击通常只是预览。
3. 连接：
   - Base 加载器 → `base_model`
   - SFT 加载器 → `sft_model`
4. 把融合后的 `MODEL` 接到采样链：

```text
Base MODEL ─┐
            ├─ MOSS Base+SFT Merge Preset ─ ModelSamplingSD3 ─ SkipLayerGuidanceDiTSimple ─ KSampler
SFT MODEL ──┘
```

5. 先用 `Balanced`、`strength = 1.0`。

## 保存融合模型

本项目不需要额外的保存节点。在融合节点后面添加 ComfyUI 内置的 **ModelSave** 节点（部分中文界面显示为“保存模型”，分类为 `model/merging`），把融合后的 `MODEL` 接到它的 `model` 输入：

```text
Base MODEL ─┐
            ├─ MOSS Base+SFT Merge Preset ─┬─ ModelSave
SFT MODEL ──┘                              └─ ModelSamplingSD3 → SkipLayerGuidanceDiTSimple → KSampler
```

`filename_prefix` 不需要填写扩展名，例如 `diffusion_models/moss_balanced_s100`。ComfyUI 会按自身的计数命名规则把文件保存到 `ComfyUI/output/diffusion_models/`。之后如果要用 **Load Diffusion Model** 加载，请把完成的 `.safetensors` 文件移到 `ComfyUI/models/diffusion_models/`（或你实际配置的模型目录）。

**ModelSave** 是输出节点，没有 `MODEL` 输出。请从融合节点的输出分出一条线接给它，同时让采样链继续向后连接。它保存的是融合节点产生的扩散模型，不包含文本编码器和 VAE。

## 在融合后使用 LoRA

在 **MOSS Base+SFT Merge Preset** 后面添加 ComfyUI 的 **Load LoRA** 节点（`LoraLoaderModelOnly`，分类为 `model/loaders`）：

```text
Base MODEL ─┐
            ├─ MOSS Base+SFT Merge Preset ─ Load LoRA ─ ModelSamplingSD3 → SkipLayerGuidanceDiTSimple → KSampler
SFT MODEL ──┘
```

把融合后的 `MODEL` 接到 LoRA 节点的 `model` 输入，选择 LoRA 文件并设置 `strength_model`。LoRA 会在推理时作用于融合后的模型，也可以连续串联多个 Load LoRA 节点。如果同时需要保存 Base+SFT 融合结果，请按上面的方式从融合节点直接分线到 **ModelSave**，这样以后调整 LoRA 时不会影响已保存的融合模型。

![MOSS Base+SFT Merge Preset 后接仅模型 LoRA 加载节点](assets/moss-merge-lora-workflow.png)

## 预设

融合权重含义：`0 = Base`，`1 = SFT`。

| 组件 | Base-preserve | Balanced | SFT-detail |
|---|---:|---:|---:|
| `video_embedder` | 0.12 | 0.20 | 0.30 |
| `text_embedder.proj` | 0.12 | 0.20 | 0.30 |
| `text_embedder.blocks.0` | 0.10 | 0.16 | 0.24 |
| `text_embedder.blocks.1` | 0.10 | 0.16 | 0.24 |
| `time_embedding` | 0.14 | 0.24 | 0.36 |
| `shared_block_modulation` | 0.12 | 0.20 | 0.30 |
| `layers.0-7` | 0.08 | 0.15 | 0.25 |
| `layers.8-13` | 0.12 | 0.20 | 0.32 |
| `layers.14-21` | 0.18 | 0.30 | 0.50 |
| `layers.22-29` | 0.28 | 0.45 | 0.65 |
| `layers.30-35` | 0.42 | 0.60 | 0.80 |
| `layers.36-41` | 0.52 | 0.72 | 0.90 |
| `final_norm_video` | 0.12 | 0.20 | 0.30 |
| `final_linear_video` | 0.25 | 0.35 | 0.50 |
| `video_head_modulation` | 0.12 | 0.20 | 0.30 |

### `strength`

`strength` 会统一缩放所有组件的融合值：

- `0.0` = 纯 Base
- `1.0` = 当前预设
- 大于 `1.0` = 加强当前预设，单项最高限制为 `1.0`n
注意：由于每项都会在 `1.0` 截断，`1.25` 不是统一的 25% 增强。`SFT-detail` 在 `1.25` 仍然是混合模型，不等于纯 SFT。

## Custom 模式

选择 `Custom` 后显示全部 51 个可调组件：

- `m_video_embedder`
- `m_text_proj`
- `m_text_block0`
- `m_text_block1`
- `m_time`
- `m_shared`
- `m_L00` ～ `m_L41`
- `m_final_norm`
- `m_linear`
- `m_head`

Custom 模式默认从 `Balanced` 数值开始，`merge_info` 会随调整实时更新。

### 层段作用

以下结论来自受控融合实验，不是 MOSS 官方训练声明：

| 范围 | 主要影响 |
|---|---|
| `text_embedder.*` | Prompt 语义与文本条件投影 |
| `time_embedding` | 全局对比、光照、时间步响应 |
| `layers.0-13` | 主体位置、整体构图、大布局 |
| `layers.14-27` | 文字层级、结构化布局、中频细节 |
| `layers.28-41` | 材质纹理、微细节和完成度 |
| `final_*` / `video_head_modulation` | 输出映射、颜色、锐度和最终观感 |

想保留 Base 构图时，优先压低前段层；想增加 SFT 细节时，优先提高后段层，再调整中段。

## 推荐采样参数

预设主要按 ComfyUI 原生 MOSS-Image 管线测试：

- `ModelSamplingSD3 shift`：`5.0`
- `CFG`：`3.5`
- 采样器：`er_sde`
- 调度器：`simple`
- 步数：草稿 `24`，最终图 `40-50`
- `SkipLayerGuidanceDiTSimple`
  - `single_layers`：`22`
  - `start_percent`：`0.0`
  - `end_percent`：`0.5`

如果使用官方 Python/Diffusers 管线，则使用其默认参数：50 步、Euler、CFG 3.0、shift 5、负分支跳过 layer 22。

## 测试提示词

人物、产品、排版、室内、动漫和材质测试提示词见 [TEST_PROMPTS.md](TEST_PROMPTS.md)。

推荐对比方式：

1. 保持相同 seed、提示词、尺寸和采样参数。
2. 分别生成 `Base-preserve`、`Balanced`、`SFT-detail`。
3. 对比构图、皮肤/材质、文字准确度和微细节。
4. 至少测试 2～3 个 seed，因为融合模型的构图可能随 seed 变化。

公共负面提示词：

```text
nsfw, worst quality, bad anatomy, watermark, jpeg artifact
```

## 常见问题

### 节点只显示预览，没有真正添加

在当前 ComfyUI 节点库中双击节点名称；单击通常只是预览。

### 切换预设后手调滑杆消失

这是正常行为。预设模式会隐藏 51 个手调项，并在 `merge_info` 显示完整有效权重。选择 `Custom` 可重新展开。

### 画面过于偏向 SFT

- 降低 `strength`
- 改用 `Base-preserve`
- 优先降低 `layers.0-13` 和 `time_embedding`
- 换一个 seed 测试

### 文字或细节仍然不足

- 优先提高 `layers.14-29`
- 再提高 `layers.30-41`
- 可从 `SFT-detail` 开始调

## 限制

- 线性权重融合不等于正交的激活或层控制。
- 构图仍可能对 seed 敏感。
- SFT 训练细节未完全公开，因此层段作用是经验结论。
- 仓库不包含模型权重。

## 许可证

MIT，详见 [LICENSE](LICENSE)。

## 致谢

- [OpenMOSS / MOSS-Image](https://github.com/OpenMOSS/MOSS-Image)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- ComfyUI 模型融合 API 与 MOSS-Image 社区集成

## 更新记录

详见 [CHANGELOG.md](CHANGELOG.md)。
