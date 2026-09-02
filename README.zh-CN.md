# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** 是一个面向 AI / LLM 音乐制作工作流的 JUCE VST3 音频测量层。

它不是让模型去“看”分析器界面，而是在 DAW 内部完成测量，通过 OSC 把紧凑数据发送给 MCP Bridge，再由 Cherry Studio 或其他 MCP 客户端结构化读取电平、响度、频谱、立体声、时间关系、工程概览、A/B 以及遮蔽相关证据。

当前产品版本：**0.7.0**。

## 项目组成

```text
AI Audio Analyzer
├─ VST3    DAW 内的实时安全测量探针
├─ MCP     将测量结果结构化提供给 LLM
└─ Skill   英文 LLM 使用说明：工具调用、参数语义、有效性
```

Skill **不是风格化混音教程**，不会内置固定 LUFS、EQ、压缩、Sidechain 或母带链规则。

## 配套 FL Studio MCP

当前工作流配套：

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

职责分开：

```text
AI Audio Analyzer MCP   → 观察 / 测量 / 比较 / 验证
FL Studio MCP           → 读取 / 控制 / 修改 FL Studio
```

典型闭环：

```text
OBSERVE → REASON → CHANGE → READBACK → COMPARE
观察       推理       修改       回读         对比
```

## 架构

```text
FL Studio / DAW
│
├─ Mixer Track A
│   └─ AI Audio Analyzer.vst3
├─ Mixer Track B
│   └─ AI Audio Analyzer.vst3
└─ Master
    └─ AI Audio Analyzer.vst3
             │
             │ OSC UDP，默认 127.0.0.1:9855
             ▼
        Analyzer MCP Bridge
        ├─ Live Instance Registry
        ├─ Recent History
        ├─ Signal Validity
        ├─ FL Track/Slot 确定性映射
        ├─ Project Overview / Snapshot A-B
        ├─ V0.6 Temporal Evidence
        └─ V0.7 Masking Evidence
             │
             ▼
      Cherry Studio / LLM
```

多个 Analyzer 可以共用一个 UDP 端口；只有一个 MCP Bridge 进程应绑定 UDP `9855`。

## 当前测量能力

### 基础频谱 / 动态 / 响度

- 4096 点 FFT，Hann Window
- 1024 Sample Analysis Hop
- 20 Hz–20 kHz 的 32 个对数频谱特征
- Sample Peak dBFS
- RMS dBFS
- Crest Factor
- LUFS-S
- 带 EBU R128 Gating 的 LUFS-I
- Current True Peak dBTP
- Session Max True Peak
- Spectral Centroid
- 约 85% Spectral Rolloff
- Spectral Flatness
- Full-band Stereo Correlation
- Mid/Side Width Ratio
- 8 个分频段 Stereo Correlation

响度和 True Peak 使用 `libebur128`。

### V0.3 Signal State

大致逻辑：

```text
关闭   低于 -50 dBFS 持续约 0.4 s
重开   高于 -48 dBFS
```

`signal_present=false` 时，依赖真实音频内容的频谱/立体声字段会变为 unavailable，而不是返回误导性的 0。

`null` 表示**当前无有效测量**，不是数值 0。

### V0.4 Analyzer ↔ FL Mixer 确定性映射

每个 Live Analyzer 都有 Session Runtime UUID，并向宿主公开：

```text
Parameter ID: identify
Display name: Identify
```

每次 Identify 状态翻转都会发送 `/aianalyzer/identify`，即使 Transport 停止也可工作。

控制端可将 Runtime UUID 与真实 FL Mixer Track/Slot 绑定，之后用：

```text
mixer:7/slot:9
```

稳定选中实例，不再依赖可能重复的显示名或音频内容猜测。

### V0.5 Project Intelligence / Snapshot A-B

提供工程准备度、最近窗口概览，以及当前 Bridge Session 内的 Before/After Snapshot。

### V0.6 Temporal Analysis

VST3 在内部分析 Hop 上计算时间特征，并聚合到约 10 Hz OSC：

```text
temporal_window_seconds
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_energy_db   # FFT-derived 40–160 Hz
```

MCP 提供：

```text
audio_temporal_profile()
audio_temporal_compare()
```

Temporal overlap/correlation 是“时间共现/共变证据”，不是遮蔽概率，也不是处理指令。

### V0.7 更强的 Masking Evidence

0.7 主要在 Bridge/MCP 层增强，复用 V0.6 VST3 测量，**不增加新的 OSC 字段**。

当前证据链：

```text
现有 32-band Spectrum
→ 16 个 equal ERB-rate 区间
→ 相对频谱占用
→ 相对电平方向权重
→ V0.6 时间重叠
→ Region-level Masking Evidence
```

关键限制：这里是 **ERB-rate 重分箱（re-binning）**，不是 gammatone / cochlear filterbank，也不是经过听阈校准的心理声学模型。

V0.7 新增：

```text
audio_masking_evidence()
audio_project_masking_scan()
```

返回值用于候选排序、下钻和验证；**不是可听遮蔽概率**，也不会自动给出 EQ、Sidechain、压缩等处理方案。

## MCP 工具

MCP 0.7 共 **20 个工具**，其中历史的 `audio_detect_masking()` 仍是频谱重叠 heuristic；更完整的两轨证据优先用 `audio_masking_evidence()`。

推荐调用路径：

```text
audio_project_status()
    ↓
audio_mix_overview()
    ↓
audio_project_masking_scan()
    ↓
audio_masking_evidence(a, b)
    ↓
audio_temporal_compare(a, b, ...)
```

不要为了“完整”而机械调用所有工具。

## 用户安装

GitHub **Release 懒人包明确按“完全没接触过编程也能用”来设计**。

当前 Release 平台：

```text
Windows x64
macOS Apple Silicon arm64
```

不提供 Intel/x86_64 macOS 包。

每个平台最终只提供一个用户 ZIP。用户只需要解压一次，ZIP 里面不会再套另一个 Release ZIP。

解压后的结构大致是：

```text
AI Audio Analyzer.vst3
mcp/
└─ ai-audio-analyzer-mcp[.exe]   已打包好的单文件程序
skill/
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
对应平台的一键安装文件
```

用户 Release **不会包含 MCP Python 源码**，也不会包含 `requirements.txt`、venv、PyInstaller `_internal` 或开发者配置示例。

### Windows

下载 Windows ZIP，右键选择 **全部解压缩**，然后双击：

```text
Install.cmd
```

### macOS Apple Silicon

下载 macOS ZIP，解压后双击：

```text
Install.command
```

如果 Gatekeeper 阻止运行，右键 `Install.command` → **打开**。

当前 macOS 包是 ad-hoc 签名，**不是 Apple Developer ID Notarization**。

Release 里自带 `START-HERE.md`、中文教程和英文教程，全部按点哪里、做什么来写，不要求用户理解开发环境。

## MCP 源码结构与唯一入口

仓库开发侧仍然只有一个 MCP 源码 / PyInstaller 入口：

```text
bridge/server.py
```

版本号作为元数据存在：

```text
MCP version          0.7
OSC protocol version 0.6
```

内部按职责拆分：

```text
bridge/server.py          唯一启动 / self-test / tool registry 入口
bridge/analyzer_core.py   稳定 OSC 状态、身份映射、基础测量和基础工具
bridge/project_tools.py   工程 Overview / Snapshot A-B
bridge/temporal_tools.py  V0.6 Temporal 解析与比较
bridge/masking_tools.py   V0.7 Masking Evidence
```

源码开发建议 Python 3.12：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r bridge/requirements.txt
AI_ANALYZER_SELF_TEST=1 python bridge/server.py
```

这套开发流程只存在于仓库中，**不会跟着用户 Release 一起发布**。

`bridge/cherry-studio.example.json` 也只是仓库里的开发者示例。用户安装器会直接生成指向已打包 MCP executable 的 Cherry Studio 配置。

## Skill

Skill 位于：

```text
skills/ai-analyzer-flstudio/
```

LLM-facing Skill 按项目规则统一使用英文：

```text
SKILL.md
README-CHERRY-STUDIO.md
references/analyzer-mcp.md
references/parameters.md
references/masking-evidence.md
```

Skill 只负责工具调用、selector/mapping、有效性、参数语义、Temporal/Masking Evidence 限制；不预设混音审美。

## OSC 协议

V0.7 不增加新字段，继续沿用 V0.6 append-only frame：

```text
0      analyzer_name
1      sample_rate
2      plugin_timestamp
3      peak_db
4      rms_db
5      crest_db
6      centroid_hz
7      rolloff_hz
8      flatness
9      stereo_correlation
10     stereo_width
11..42 32 spectrum bands
43     lufs_s
44     lufs_i
45     true_peak_dbtp
46     max_true_peak_dbtp
47..54 8 band stereo correlations
55     signal_present
56     detector_peak_db
57     silence_seconds
58     runtime_uuid
59     temporal_window_seconds
60     spectral_flux_mean
61     spectral_flux_peak
62     rms_rise_peak_db
63     low_band_energy_db
64     frame_schema_version = "0.6"
```

## 当前限制

- V0.7 ERB 只是基于已有 32-band feature 的 re-binning，不是真正 auditory filterbank；
- Masking evidence 是 heuristic，不应描述成心理声学 ground truth；
- Temporal 对齐受独立 OSC Stream 和约 10 Hz 更新分辨率限制；
- LUFS-I / Session Max True Peak 是 session 累积量；
- FL Mixer binding 是 session-scoped，重新打开工程后可能需要重新 Identify；
- macOS Release 仅支持 Apple Silicon，且当前未 Notarize。

## 仓库结构

```text
Source/                         JUCE VST3
bridge/server.py                唯一 MCP 入口
bridge/analyzer_core.py         稳定内部 Core
bridge/*_tools.py               功能模块
skills/ai-analyzer-flstudio/    英文 LLM-facing Skill
release/                        面向普通用户的懒人包安装器 / 文档
.github/workflows/build.yml     开发 CI
.github/workflows/release.yml   手动 Release 打包
AGENT.md                        Agent / Maintainer 路线图与规则
```

修改仓库前先阅读 `AGENT.md`。
