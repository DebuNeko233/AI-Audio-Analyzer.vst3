# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** 是一个面向 AI / LLM 音乐制作工作流的 JUCE VST3 机器可读音频测量层。

插件在 DAW 内直接测量音频，通过 OSC 把紧凑数据发送给 Analyzer MCP Bridge，再由 Cherry Studio 或其他 MCP 客户端结构化读取电平、响度、频谱、立体声、时间关系、工程概览、A/B、遮蔽相关证据、音频域调性证据，以及 V1.0 的闭环修改验证信息。

当前产品版本：**1.0.0**。

## 项目组成

```text
AI Audio Analyzer
├─ VST3    DAW 内的实时安全测量探针
├─ MCP     结构化测量 / 比较 / 验证工具
└─ Skill   英文 LLM 使用说明：正确调用 MCP、理解参数和证据语义
```

Skill **不是风格化混音/和声教程**，不会内置固定 LUFS、EQ、压缩、Sidechain、Stereo、转调、和声修改或母带处理配方。

## 配套 FL Studio MCP

当前工作流配套：

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

```text
AI Audio Analyzer MCP   → 观察 / 测量 / 比较 / 验证
FL Studio MCP           → 读取 / 控制 / 修改 / 回读 FL Studio
```

V1.0 把闭环明确为：

```text
工程发现
→ Analyzer 确定性映射
→ Before 测量
→ 根据用户目标进行外部推理
→ 通过真实 DAW-control MCP 修改
→ 回读宿主实际状态
→ After 测量
→ 检查 Before/After 是否可比
→ 需要时再下钻 Temporal / Masking / Stereo / Tonal 证据
```

Analyzer MCP 本身**不负责写入 DAW 参数**。

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
                 ├─ V0.8 Mid/Side + Stereo Evidence
                 ├─ V0.9 Tonal / Music-Semantic Evidence
                 └─ V1.0 Closed-loop Verification Sessions
                         │
                         ▼
                  Cherry Studio / LLM
                         │
                         └─ 外部 FL Studio MCP 负责实际修改和宿主回读
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
- V0.8 Mid RMS、Side RMS、Side/Mid dB、Side Spectrum、分频段 Side/Mid、低频 Stereo Relation 和 Negative Cross-Spectrum Evidence；
- V0.9 12-bin Mid-spectrum Chroma、Chroma 分析覆盖率、Tonal-center Profile Ranking 和 Single-F0 Harmonic-alignment Evidence。

### V0.3 Signal Validity

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

每次 Identify 状态翻转都会发送 `/aianalyzer/identify`，Transport 停止时同样有效。Bridge 可把 Runtime UUID 绑定到真实 FL Mixer Track / Slot，之后优先用：

```text
mixer:7/slot:9
```

### V0.5 Project Intelligence / Snapshot A-B

提供工程准备度、最近窗口概览，以及当前 Bridge Session 内的 Before / After Snapshot。

### V0.6 Temporal Evidence

```text
audio_temporal_profile()
audio_temporal_compare()
```

Temporal overlap / correlation 是时间共现和共变证据，不是遮蔽概率，也不是处理指令。

### V0.7 Masking Evidence

```text
32 个 Mid Spectrum 特征
→ 16 个 equal ERB-rate 区间
→ 相对频谱占用
→ 相对电平方向权重
→ V0.6 时间重叠
→ Region-level Masking Evidence
```

```text
audio_masking_evidence()
audio_project_masking_scan()
```

这里是 **equal-ERB-rate feature re-binning**，不是 gammatone / cochlear filterbank，也不是经过听阈校准的心理声学模型。分数是 heuristic evidence，不是可听遮蔽概率。

### V0.8 Mid/Side 与 Stereo Evidence

V0.8 将 Signed L/R Correlation、Side/Mid Energy、Decorrelation Proxy、Negative Cross-Spectrum、低频 Stereo Relation、Mid/Side Spectrum 和分频段 Stereo 关系拆开测量。

```text
audio_stereo_profile(track, seconds=5)
audio_stereo_compare(track_a, track_b, seconds=5)
```

Skill 不定义统一的 Width、Correlation、Side/Mid 或低频 Stereo 目标。

### V0.9 音频域调性 / Music-semantic Evidence

V0.9 提供：

```text
12-bin normalized chroma: C..B
chroma_energy_ratio
single_f0_harmonic_energy_ratio
harmonic_f0_candidate_hz
```

Chroma 来自大约 `80 Hz–5 kHz` 的 Mid Spectrum Power，并映射到最近的 12-TET Pitch Class、折叠 Octave。Single-F0 Harmonic Ratio 的最终能量分子和分母也使用约 `80 Hz–5 kHz` 的语义频段，而候选 F0 搜索范围约为 `55–1000 Hz`。

```text
audio_tonal_profile(track, seconds=8)
audio_tonal_compare(track_a, track_b, seconds=8)
```

Tonal-center 使用 24 个 Major/Minor Krumhansl-Kessler Profile Correlation。它们是音频域证据，不是精确 Key / Note 概率。涉及精确 Note、Key、Chord、Tuning 时，如果 DAW/MIDI MCP 有真实符号数据，应优先用该数据。

### V1.0 可靠闭环验证

V1.0 新增的是 **Bridge 侧 Verification Orchestration**，没有新增 DSP 或 OSC 字段：

```text
audio_begin_verification(label, seconds=5, target_selectors=None)
audio_complete_verification(verification_id, seconds=0, change_summary="", host_readback="")
audio_verification_status(verification_id="")
```

标准流程：

```text
Before Baseline
→ 外部 FL Studio MCP 实际修改
→ 回读宿主实际状态
→ After Capture
→ 检查技术可比性
→ 返回 After - Before 测量差值
```

Verification 会显式检查：Before/After 测量窗口是否一致、Analyzer 拓扑是否一致、目标是否缺失或无效、Active Coverage 是否接近。当前 `active_ratio` 的绝对差容差为 `0.15`。

`controlled_comparison=true` 只代表**这次 A/B 的技术测量条件满足当前透明 Guardrails**，不代表 After 更好、设置正确、更加专业，也不代表应该保留修改。

`host_readback` 是调用方从外部 Control MCP 获得的实际宿主回读文本；Analyzer 会把它保存进审计结果，但不会独立验证 FL Studio 控制状态。

Verification Session 只保存在当前 Bridge 内存中，重启 MCP 后不会保留。

## MCP 工具

MCP 1.0 共 **27 个工具**。在之前 24 个测量/证据工具基础上新增：

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

不要为了“完整”机械调用所有工具。先从工程级工具开始，只选择当前问题真正需要的 Evidence Family；如果任务要求修改 DAW 并验证结果，就用 V1.0 Verification 包住外部写入和宿主回读。

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
└─ ai-audio-analyzer-mcp[.exe]   PyInstaller -F 单文件程序
skill/
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
对应平台的一键安装文件
```

用户 Release **不会包含 MCP Python 源码**、`requirements.txt`、venv、PyInstaller `_internal`、开发者配置示例或嵌套 ZIP。

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

版本关系：

```text
Product version       1.0.0
MCP version           1.0
OSC protocol version  0.9
```

V1.0 没有改 VST3 Frame，因此 OSC Protocol 故意保持 0.9。

内部模块：

```text
bridge/server.py             启动 / self-test / 共享 Tool Registry
bridge/analyzer_core.py      OSC 状态、身份映射、基础工具
bridge/project_tools.py      Project Overview / Snapshot A-B
bridge/temporal_tools.py     V0.6 Temporal Layer
bridge/masking_tools.py      V0.7 Masking Evidence Layer
bridge/stereo_tools.py       V0.8 Mid/Side + Stereo Layer
bridge/semantic_tools.py     V0.9 Chroma / Tonal-center / Harmonic Evidence
bridge/verification_tools.py V1.0 Closed-loop Verification
```

`bridge/ci_regression.py` 只用于仓库 CI，不进入普通用户 Release。

## Skill

LLM-facing Skill 统一使用英文：

```text
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/README-CHERRY-STUDIO.md
skills/ai-analyzer-flstudio/references/analyzer-mcp.md
skills/ai-analyzer-flstudio/references/parameters.md
skills/ai-analyzer-flstudio/references/masking-evidence.md
skills/ai-analyzer-flstudio/references/stereo-evidence.md
skills/ai-analyzer-flstudio/references/tonal-evidence.md
skills/ai-analyzer-flstudio/references/verification-evidence.md
```

Skill 只负责工具调用、selector / mapping、有效性、参数与证据语义，不预设混音审美、转调、和声修改或处理动作。

## OSC 协议

Analysis 地址：`/aianalyzer/frame`。

MCP 1.0 继续使用 append-only **OSC Protocol 0.9**：

```text
0..58      V0.1–V0.4 兼容字段
59..64     V0.6 Temporal
65..111    V0.8 Mid/Side + Stereo
112..123   12 Chroma Bins：C..B
124        chroma_energy_ratio
125        single_f0_harmonic_energy_ratio
126        harmonic_f0_candidate_hz
127        V0.9 schema marker = "0.9"
```

历史 `11..42` 仍是 32-band **Mid Spectrum**。V1.0 不会在 127 后面继续追加字段。

Identify 地址仍是 `/aianalyzer/identify`。

## 实时线程原则

Audio Callback 不执行 FFT、响度、Music-semantic Analysis、OSC、MCP、Verification Orchestration、文件或网络 I/O，也不执行重量级分配。Audio Sample 只写入预分配 SPSC FIFO，其余分析在后台线程完成。

## 当前限制

- V0.7 ERB 仍是 feature re-binning，不是真正 auditory filterbank；
- Masking Evidence 仍是 heuristic；
- V0.8 Negative Cross Evidence 不是 phase-angle histogram 或 mono-cancellation 百分比；
- V0.8 Side/Mid 与 Correlation 都是测量，不是 Stereo Quality Score；
- V0.9 Chroma 是 FFT-derived 12-TET Pitch-class Evidence，不是 Transcription；
- V0.9 Tonal-center Ranking 是 Profile Correlation，不是精确 Key Detection；
- V0.9 Single-F0 Harmonic Evidence 是 Heuristic，在 Polyphonic / Noisy / Inharmonic Material 上可能不稳定；
- V1.0 Topology Fingerprint 只代表当前 Live Analyzer 的一致性，不是完整、永久的 FL Studio Project Hash；
- V1.0 `host_readback` 由调用方/外部 Control MCP 提供，Analyzer 不独立验证；
- V1.0 Verification Session 是内存态，Bridge 退出后消失；
- Temporal 对齐受独立 OSC Stream 和更新分辨率限制；
- LUFS-I / Session Max True Peak 是 Session 累积量；
- FL Mixer Binding 是 Session-scoped，重新打开工程后可能需要重新 Identify；
- macOS Release 仅支持 Apple Silicon，且当前未 Notarize。

## 仓库结构

```text
Source/                         JUCE VST3
bridge/server.py                唯一 MCP 入口
bridge/analyzer_core.py         稳定内部 MCP/OSC Core
bridge/*_tools.py               功能模块
bridge/ci_regression.py         仓库内部 MCP 回归测试
skills/ai-analyzer-flstudio/    英文 LLM-facing Skill
release/                        面向普通用户的安装器 / 文档
.github/workflows/build.yml     开发 CI
.github/workflows/release.yml   手动 Release 打包
AGENT.md                        Agent / Maintainer 历史与规则
```

修改仓库前先阅读 `AGENT.md`。
