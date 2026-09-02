# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** 是一个面向 AI / LLM 音乐制作工作流的 JUCE VST3 机器可读音频测量层。

插件直接在 DAW 内测量音频，通过 OSC 将紧凑数据发送给 Analyzer MCP Bridge，再由 Cherry Studio 或其他 MCP 客户端结构化读取电平、响度、频谱、立体声、时间关系、遮蔽、调性、工程概览、A/B、性能状态和闭环验证证据。

当前产品版本：**1.1.0**。

## 项目组成

```text
AI Audio Analyzer
├─ VST3    DAW 内的实时安全测量探针
├─ MCP     结构化测量 / 比较 / 验证 / 性能工具
└─ Skill   面向 LLM 的英文 MCP 调用和参数语义说明
```

Skill **不是风格化混音/和声教程**，不会内置固定 LUFS、EQ、压缩、Sidechain、Stereo、转调、和声修改或母带处理配方。

## 配套 FL Studio MCP

当前工作流配套：

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

```text
AI Audio Analyzer MCP   → 观察 / 测量 / 比较 / 验证
FL Studio MCP           → 读取 / 控制 / 修改 / 回读 FL Studio
```

Analyzer MCP 本身**不写入 DAW 参数**。需要修改 Analyzer 的宿主参数时，应由真实 FL Studio Control MCP 完成写入和回读，再由 Analyzer MCP 验证插件实际状态。

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
                 ├─ Adaptive Analysis / Performance Telemetry
                 ├─ Temporal / Masking Evidence
                 ├─ Mid/Side + Stereo Evidence
                 ├─ Tonal / Music-Semantic Evidence
                 └─ Closed-loop Verification Sessions
                         │
                         ▼
                  Cherry Studio / LLM
                         │
                         └─ 外部 FL Studio MCP 负责实际修改和宿主回读
```

多个 Analyzer 可以共用同一个 UDP 端口；只有一个 MCP Bridge 进程应该绑定 UDP `9855`。

## 当前测量能力

主要能力包括：

- Sample Peak、RMS、Crest Factor；
- `libebur128` 提供 LUFS-S / LUFS-I、Current / Session Max True Peak；
- 4096 点 FFT、Hann Window、20 Hz–20 kHz 的 32 个对数 Mid Spectrum 特征；
- Spectral Centroid、约 85% Rolloff、Flatness；
- Full-band 和 8-band L/R Correlation；
- Spectral Flux、RMS Rise、40–160 Hz Temporal Energy；
- Mid RMS、Side RMS、Side/Mid dB、Side Spectrum、分频段 Side/Mid、低频 Stereo Relation 和 Negative Cross-Spectrum Evidence；
- 12-bin Mid-spectrum Chroma、Tonal-center Profile Ranking 和 Single-F0 Harmonic-alignment Evidence；
- Project Overview、Snapshot A/B、Masking Evidence、Controlled Before/After Verification 和 Analyzer Performance Telemetry。

### Signal Validity

```text
关闭   低于 -50 dBFS 持续约 0.4 s
重开   高于 -48 dBFS
```

`signal_present=false` 时，依赖音频内容的字段会变成 unavailable，而不是返回误导性的 0。`null` 表示**当前没有有效测量**，不是数值 0。

### Analyzer ↔ FL Mixer 确定性映射

每个 Live Analyzer 都有 Session Runtime UUID，并向宿主公开：

```text
Parameter ID: identify
Display name: Identify
```

每次 Identify 翻转都会发送 `/aianalyzer/identify`，Transport 停止时同样有效。Bridge 可把 Runtime UUID 绑定到真实 FL Mixer Track / Slot，之后优先使用：

```text
mixer:7/slot:9
```

### 自适应分析与性能控制

大型工程可能在很多 Mixer Track 上都插入 Analyzer，没有必要让每个实例永久运行全部分析。因此插件新增一个真实的宿主参数：

```text
Parameter ID: analysis_profile
Display name: Analysis Profile

0 Eco
1 Balanced
2 Mix
3 Full
```

Profile 只控制**测量计算量**，不会处理或改变声音：

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` 仍是默认值，以保证旧工程兼容。旧工程状态没有 `analysisProfile` 字段时也按 Full 恢复。

不同 Profile 的调度策略：

```text
Eco       不运行 FFT / Loudness 分析
Balanced  降低 FFT 调度频率，约为网络更新尺度
Mix       为 Temporal 恢复 hop-level FFT
Full      Mix + 更低频率的 Semantic 分析
```

实际运行频率还会受 Sample Rate、Transport、音频流和宿主调度影响。

Analyzer MCP 新增：

```text
audio_analysis_status(track)
audio_project_performance()
```

它们会读取插件真正上报的 Profile / Feature Mask，并提供：

```text
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
```

`worker_load_ratio` 只是 **Analyzer 后台 Worker 的忙碌比例**，不是 FL Studio Realtime Audio CPU。`fifo_fill_ratio` 更关键：如果持续升高，说明后台分析跟不上输入音频，Analyzer 数据可能逐渐落后于 DAW 当前播放位置。

推荐按需使用：

```text
读取 audio_analysis_status()
→ 只有确实需要更深证据时，通过 FL Studio MCP 提高 Analysis Profile
→ 回读真实宿主参数
→ 再读 Analyzer 状态确认已生效
→ 完成所需测量
→ 需要时恢复原 Profile
```

为了保持 append-only OSC 兼容，被关闭的功能仍然保留字段位置，但 Bridge 会依据 Feature Mask 将其显式标记为 unavailable，旧工具不会把占位值当成真实测量。

### Project Intelligence / Snapshot A-B

提供工程准备度、最近窗口概览和当前 Bridge Session 内的 Before / After Snapshot。

### Temporal Evidence

```text
audio_temporal_profile()
audio_temporal_compare()
```

Temporal overlap / correlation 是时间共现和共变证据，不是遮蔽概率或处理指令。Temporal 工具需要启用 Temporal 的 Profile。

### Masking Evidence

```text
32 个 Mid Spectrum 特征
→ 16 个 equal ERB-rate 区间
→ 相对频谱占用
→ 相对电平方向权重
→ 可用时加入时间重叠
→ Region-level Masking Evidence
```

```text
audio_masking_evidence()
audio_project_masking_scan()
```

这里是 **equal-ERB-rate feature re-binning**，不是 gammatone / cochlear filterbank，也不是经过听阈校准的心理声学模型。分数是 heuristic evidence，不是可听遮蔽概率。

### Mid/Side 与 Stereo Evidence

```text
audio_stereo_profile(track, seconds=5)
audio_stereo_compare(track_a, track_b, seconds=5)
```

Signed L/R Correlation、Side/Mid Energy、Decorrelation Proxy、Negative Cross-Spectrum、低频 Stereo Relation 和分频段 Stereo 关系保持独立，不定义统一的 Stereo 目标。

### 音频域调性 / Music-semantic Evidence

```text
audio_tonal_profile(track, seconds=8)
audio_tonal_compare(track_a, track_b, seconds=8)
```

Analyzer 提供 normalized 12-bin Chroma、Chroma Energy Coverage、Tonal-center Template Correlation 和 Single-F0 Harmonic-alignment Evidence。Chroma 主要使用约 `80 Hz–5 kHz` 的 Mid Spectrum；候选 F0 搜索约 `55–1000 Hz`。

这些都是音频域证据，不是精确 Key / Note 概率。涉及精确 Note、Key、Chord、Tuning 时，如果 DAW/MIDI MCP 有真实符号数据，应优先用该数据。Tonal 工具需要 Semantic，通常使用 Full。

### 可靠闭环验证

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

`controlled_comparison=true` 只表示当前透明技术 Guardrails 通过，不代表 After 更好、设置正确或应该保留修改。

`closed_loop_complete=true` 还要求调用方提供真实宿主回读。Analyzer 会保存该回读用于审计，但不会独立查询 FL Studio 控制状态。

Verification Session 只保存在当前 Bridge 内存中。

## MCP 工具

MCP **1.1 共 29 个工具**。性能层新增：

```text
audio_analysis_status(track)
audio_project_performance()
```

不要为了“完整”机械调用全部工具。先检查工程和性能状态，再只启用当前问题需要的最低分析层级。

## 用户安装

GitHub **Release 懒人包按照“完全没接触过编程也能安装”设计**。

当前平台：

```text
Windows x64
macOS Apple Silicon arm64
```

不提供 Intel / x86_64 macOS 包。

每个平台只提供一个最终 ZIP，用户只需要解压一次，不会 ZIP 套 ZIP。

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

Windows：全部解压后双击 `Install.cmd`。

macOS Apple Silicon：解压后双击 `Install.command`。如果 Gatekeeper 阻止运行，右键 → **打开**。当前 macOS 包是 ad-hoc 签名，不是 Apple Developer ID Notarization。

## 仓库 MCP 架构

源码和 PyInstaller 永远只有一个入口：

```text
bridge/server.py
```

当前版本关系：

```text
Product version       1.1.0
MCP version           1.1
OSC protocol version  1.1
MCP tools             29
```

内部模块：

```text
bridge/server.py             启动 / Self-test / Tool Registry
bridge/analyzer_core.py      OSC 状态、身份映射、基础工具
bridge/project_tools.py      Project Overview / Snapshot A-B
bridge/temporal_tools.py     Temporal Layer
bridge/masking_tools.py      Masking Evidence Layer
bridge/stereo_tools.py       Mid/Side + Stereo Layer
bridge/semantic_tools.py     Chroma / Tonal-center / Harmonic Evidence
bridge/verification_tools.py Closed-loop Verification
bridge/performance_tools.py  Adaptive Profile / Worker Telemetry
bridge/ci_regression.py      仓库专用 Synthetic Regression
```

`bridge/ci_regression.py` 不进入普通用户 Release。

## Skill

LLM-facing Skill 统一使用英文，主要参考：

```text
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/README-CHERRY-STUDIO.md
skills/ai-analyzer-flstudio/references/analyzer-mcp.md
skills/ai-analyzer-flstudio/references/parameters.md
skills/ai-analyzer-flstudio/references/performance-evidence.md
skills/ai-analyzer-flstudio/references/masking-evidence.md
skills/ai-analyzer-flstudio/references/stereo-evidence.md
skills/ai-analyzer-flstudio/references/tonal-evidence.md
skills/ai-analyzer-flstudio/references/verification-evidence.md
```

Skill 只负责工具调用、Selector / Mapping、Profile 选择、有效性和参数/证据语义，不预设混音审美或处理动作。

## OSC 协议

Analysis 地址：`/aianalyzer/frame`。

OSC **1.1** 继续保持 append-only：

```text
0..58      历史 Core / Signal / Identity 字段
59..64     Temporal + schema marker
65..111    Mid/Side + Stereo + schema marker
112..123   12 Chroma Bins：C..B
124        chroma_energy_ratio
125        single_f0_harmonic_energy_ratio
126        harmonic_f0_candidate_hz
127        schema marker = "0.9"
128        analysis_profile
129        analysis_feature_mask
130        worker_load_ratio
131        fifo_fill_ratio
132        fft_runs_per_second
133        semantic_runs_per_second
134        schema marker = "1.1"
```

已有 `0..127` 不重新解释。历史 `11..42` 仍是 32-band Mid Spectrum。Identify 地址仍是 `/aianalyzer/identify`。

## 实时线程原则

Audio Callback 不执行 FFT、响度、Semantic、OSC、MCP、Verification、文件或网络 I/O。Audio Sample 只写入预分配 SPSC FIFO，其余分析在后台线程完成。

只有 Analysis Profile 真正变化时才会通知后台 Worker；普通 Audio Block 不会反复唤醒 Worker 重申当前 Profile。

功能重新开启时，跨越“未分析空档”会造成语义污染的状态会被重置：Loudness 会重建 ebur128 状态，Temporal 会清理 previous spectrum / accumulator，Semantic 会清缓存。

## 当前限制

- Performance Telemetry 是 Analyzer Worker 自身遥测，不是校准后的 DAW/System CPU Profiler；
- Adaptive Profile 可以减少 Analyzer 计算，但不承诺所有宿主和 Sample Rate 都得到固定比例的 CPU 降幅；
- ERB 仍是 feature re-binning，Masking Evidence 仍是 heuristic；
- Stereo、Temporal、Tonal 指标都是测量/证据，不是 Quality Score；
- Chroma 不是 Transcription，Tonal-center Ranking 不是精确 Key Detection；
- Single-F0 Harmonic Evidence 在 Polyphonic / Noisy / Inharmonic Material 上可能不稳定；
- Topology Fingerprint 不是永久 DAW Project Hash；
- `host_readback` 由调用方/外部 Control MCP 提供，Analyzer 不独立验证；
- Verification Session 和 FL Mixer Binding 都是 Session-scoped；
- LUFS-I / Session Max True Peak 只在 Loudness 启用期间累计；Loudness 关闭后重新开启会开始新的 Loudness 测量状态；
- macOS Release 仅支持 Apple Silicon，且当前未 Notarize。

## 仓库结构

```text
Source/                         JUCE VST3
bridge/server.py                唯一 MCP 入口
bridge/analyzer_core.py         稳定内部 MCP/OSC Core
bridge/*_tools.py               功能模块
bridge/ci_regression.py         仓库专用 MCP Regression
skills/ai-analyzer-flstudio/    英文 LLM-facing Skill
release/                        普通用户 Release 安装器/说明
.github/workflows/build.yml     开发 CI
.github/workflows/release.yml   手动 Release 打包
AGENT.md                        Agent / Maintainer 约束与历史
```

修改仓库前请先阅读 `AGENT.md`。
