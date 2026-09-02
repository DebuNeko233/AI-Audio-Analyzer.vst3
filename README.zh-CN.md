# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** 是一个面向 AI / LLM 音乐制作工作流的 JUCE VST3 机器可读音频测量层。

插件在 DAW 内部直接完成测量，通过 OSC 把紧凑数据发送给 Analyzer MCP Bridge，再由 Cherry Studio 或其他 MCP 客户端结构化读取电平、响度、频谱、立体声、时间关系、工程概览、A/B 和遮蔽相关证据。

当前产品版本：**0.8.0**。

## 项目组成

```text
AI Audio Analyzer
├─ VST3    DAW 内的实时安全测量探针
├─ MCP     结构化测量 / 比较 / 证据工具
└─ Skill   英文 LLM 使用说明：正确调用 MCP、理解参数和有效性
```

Skill **不是风格化混音教程**，不会内置固定 LUFS、EQ、压缩、Sidechain、Stereo 或母带处理配方。

## 配套 FL Studio MCP

当前工作流配套：

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

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
├─ Mixer Track A ─ AI Audio Analyzer.vst3
├─ Mixer Track B ─ AI Audio Analyzer.vst3
└─ Master        ─ AI Audio Analyzer.vst3
                         │
                         │ OSC UDP，默认 127.0.0.1:9855
                         ▼
                 Analyzer MCP Bridge
                 ├─ Live Instance Registry
                 ├─ FL Track/Slot 确定性映射
                 ├─ Project Overview / Snapshot A-B
                 ├─ V0.6 Temporal Evidence
                 ├─ V0.7 Masking Evidence
                 └─ V0.8 Mid/Side + Stereo Evidence
                         │
                         ▼
                  Cherry Studio / LLM
```

多个 Analyzer 可以共用同一个 UDP 端口；只有一个 MCP Bridge 进程应该绑定 UDP `9855`。

## 当前测量能力

基础测量包括：

- 4096 点 FFT、Hann Window、1024 Sample Hop；
- 20 Hz–20 kHz 的 32 个对数 **Mid Spectrum** 特征；
- Sample Peak、RMS、Crest Factor；
- `libebur128` 提供 LUFS-S / LUFS-I 和 Current / Session Max True Peak；
- Spectral Centroid、约 85% Rolloff、Flatness；
- Full-band L/R Correlation 和历史 Mid/Side Width Ratio；
- 8 个分频段 L/R Correlation；
- V0.6 Spectral Flux、RMS Rise、40–160 Hz Temporal Energy；
- V0.8 Mid RMS、Side RMS、Side/Mid dB、Side Spectrum、分频段 Side/Mid、低频 Stereo Relation 和 Negative Cross-Spectrum Evidence。

### V0.3 Signal Validity

大致逻辑：

```text
关闭   低于 -50 dBFS 持续约 0.4 s
重开   高于 -48 dBFS
```

`signal_present=false` 时，依赖真实音频内容的字段会变成 unavailable，而不是返回误导性的 0。`null` 表示**当前没有有效测量**，不是数值 0。

### V0.4 Analyzer ↔ FL Mixer 确定性映射

每个 Live Analyzer 都有 Session Runtime UUID，并向宿主公开：

```text
Parameter ID: identify
Display name: Identify
```

每次 Identify 状态翻转都会发送 `/aianalyzer/identify`，Transport 停止时同样有效。Bridge 可把 Runtime UUID 绑定到真实 FL Mixer Track / Slot，之后用：

```text
mixer:7/slot:9
```

稳定选中目标实例。

### V0.5 Project Intelligence / Snapshot A-B

提供工程准备度、最近窗口概览，以及当前 Bridge Session 内的 Before / After Snapshot。

### V0.6 Temporal Evidence

```text
audio_temporal_profile()
audio_temporal_compare()
```

Temporal overlap / correlation 是时间共现和共变证据，不是遮蔽概率，也不是处理指令。

### V0.7 更强的 Masking Evidence

```text
32 个 Mid Spectrum 特征
→ 16 个 equal ERB-rate 区间
→ 相对频谱占用
→ 相对电平方向权重
→ V0.6 时间重叠
→ Region-level Masking Evidence
```

新增：

```text
audio_masking_evidence()
audio_project_masking_scan()
```

这里是 **equal-ERB-rate feature re-binning**，不是 gammatone / cochlear filterbank，也不是经过听阈校准的心理声学模型。分数是 heuristic evidence，不是可听遮蔽概率。

### V0.8 更深入的 Mid/Side 与 Stereo Evidence

0.8 把单一 `stereo_width` 无法区分的概念拆开：

```text
带正负号的 L/R Correlation
Side/Mid Energy Ratio
Decorrelation Proxy = 1 - abs(correlation)
Negative Cross-Spectrum Energy Ratio
20–120 Hz Correlation + Side/Mid Ratio
32-band Mid Spectrum + 32-band Side Spectrum
8-band Correlation + Side/Mid Ratio
```

新增：

```text
audio_stereo_profile(track, seconds=5)
audio_stereo_compare(track_a, track_b, seconds=5)
```

重要区别：

- 低相关性不等于反相关；
- Side Energy 大不等于一定存在相位对立；
- Negative Cross Evidence 不是 Mono Cancellation 百分比，也不是可听问题概率；
- Skill 不定义统一的 Width、Correlation、Side/Mid 或低频 Stereo 目标。

## MCP 工具

MCP 0.8 共 **22 个工具**：

```text
audio_bridge_status()
audio_list_tracks()
audio_last_identify()
audio_bind_last_identified(...)
audio_instance_map()
audio_snapshot(track)
audio_average(track, seconds)
audio_stereo_bands(track)
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
audio_master_status(track="Master")
audio_project_status()
audio_mix_overview(seconds=10, max_tracks=32)
audio_capture_snapshot(name, seconds=5)
audio_list_snapshots()
audio_compare_snapshots(before, after)
audio_temporal_profile(track, seconds=5)
audio_temporal_compare(...)
audio_masking_evidence(...)
audio_project_masking_scan(...)
audio_stereo_profile(track, seconds=5)
audio_stereo_compare(track_a, track_b, seconds=5)
```

不要为了“完整”而机械调用所有工具。先从工程级工具开始，确实需要时再下钻。

## 用户安装

GitHub **Release 懒人包按照“完全没接触过编程也能安装”设计**。

当前平台：

```text
Windows x64
macOS Apple Silicon arm64
```

不提供 Intel / x86_64 macOS 包。

每个平台只提供一个最终 ZIP。用户只需要解压一次，里面不会再套另一个 Release ZIP。

解压后的结构：

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

用户 Release **不会包含 MCP Python 源码**、`requirements.txt`、venv、PyInstaller `_internal` 或开发者配置示例。

### Windows

下载 Windows ZIP → **全部解压缩** → 双击：

```text
Install.cmd
```

### macOS Apple Silicon

下载 macOS ZIP → 解压 → 双击：

```text
Install.command
```

如果 Gatekeeper 阻止运行，右键 `Install.command` → **打开**。

当前 macOS 包是 ad-hoc 签名，**不是 Apple Developer ID Notarization**。

## 仓库 MCP 架构

源码和 PyInstaller 永远只有一个入口：

```text
bridge/server.py
```

版本号是元数据，不写进启动文件名：

```text
Product version       0.8.0
MCP version           0.8
OSC protocol version  0.8
```

内部按职责拆分：

```text
bridge/server.py          启动 / self-test / 共享 Tool Registry
bridge/analyzer_core.py   OSC 状态、身份映射、基础工具
bridge/project_tools.py   Project Overview / Snapshot A-B
bridge/temporal_tools.py  V0.6 Temporal Layer
bridge/masking_tools.py   V0.7 Masking Evidence Layer
bridge/stereo_tools.py    V0.8 Mid/Side + Stereo Layer
```

仓库开发可以使用 Python 3.12 和 `bridge/requirements.txt`；这套开发内容**不会进入用户 Release**。

## Skill

LLM-facing Skill 按项目规则统一使用英文：

```text
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/README-CHERRY-STUDIO.md
skills/ai-analyzer-flstudio/references/analyzer-mcp.md
skills/ai-analyzer-flstudio/references/parameters.md
skills/ai-analyzer-flstudio/references/masking-evidence.md
skills/ai-analyzer-flstudio/references/stereo-evidence.md
```

Skill 只负责工具调用、selector / mapping、有效性、参数与证据语义，不预设混音审美。

## OSC 协议

Analysis 地址：`/aianalyzer/frame`。

协议继续 append-only。现有 `0..64` 完全不变，V0.8 追加：

```text
0..58    V0.1–V0.4 兼容字段
59       temporal_window_seconds
60       spectral_flux_mean
61       spectral_flux_peak
62       rms_rise_peak_db
63       low_band_energy_db
64       V0.6 schema marker = "0.6"
65       mid_rms_db
66       side_rms_db
67       side_to_mid_db
68       negative_cross_energy_ratio
69       low_band_20_120_correlation
70       low_band_20_120_side_to_mid_db
71..102  32 个 Side Spectrum Bands
103..110 8 个 Side/Mid Band Ratios
111      V0.8 schema marker = "0.8"
```

历史的 `11..42` 继续保持为 32-band **Mid Spectrum**。

Identify 地址仍然是 `/aianalyzer/identify`。

## 实时线程原则

Audio Callback 不执行 FFT、响度、OSC、MCP、文件或网络 I/O，也不执行重量级分配。Audio Sample 只写入预分配 SPSC FIFO，其余分析在后台线程完成。

## 当前限制

- V0.7 ERB 仍然只是 feature re-binning，不是真正 auditory filterbank；
- Masking Evidence 仍然是 heuristic；
- V0.8 Negative Cross Evidence 不是 phase-angle histogram 或 mono-cancellation 百分比；
- V0.8 Side/Mid 与 Correlation 都是测量，不是 Stereo Quality Score；
- Temporal 对齐受独立 OSC Stream 和约 10 Hz 更新分辨率限制；
- LUFS-I / Session Max True Peak 是 Session 累积量；
- FL Mixer Binding 是 Session-scoped，重新打开工程后可能需要重新 Identify；
- macOS Release 仅支持 Apple Silicon，且当前未 Notarize。

## 仓库结构

```text
Source/                         JUCE VST3
bridge/server.py                唯一 MCP 入口
bridge/analyzer_core.py         稳定内部 MCP/OSC Core
bridge/*_tools.py               功能模块
skills/ai-analyzer-flstudio/    英文 LLM-facing Skill
release/                        面向普通用户的安装器 / 文档
.github/workflows/build.yml     开发 CI
.github/workflows/release.yml   手动 Release 打包
AGENT.md                        Agent / Maintainer 路线图与规则
```

修改仓库前先阅读 `AGENT.md`。
