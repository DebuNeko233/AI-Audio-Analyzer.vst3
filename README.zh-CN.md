# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** 是面向 AI / LLM 音乐制作工作流的 JUCE VST3 机器可读音频测量层。

它在 DAW 内持续测量音频，通过 OSC 向 Analyzer MCP 发送结构化数据，并向 Cherry Studio 或其他 MCP 客户端提供实时证据、Transport-aligned Song Memory、可解释歌曲结构、Track Story、Section-aware Relationships、Coverage-aware Dynamics Distribution、Direct Mono-fold Compatibility、Session Reference Comparison、性能遥测、身份范围说明和闭环验证证据。

当前产品版本：**1.2.0**。

## 系统边界

```text
AI Audio Analyzer VST3
  -> 实时安全测量 + DAW Transport Context

AI Audio Analyzer MCP
  -> 观察 / 记忆 / 结构 / 比较 / 验证
  -> 冻结 Session Reference Profile 并比较目标证据
  -> 明确 Project / Runtime Identity 的当前保证范围
  -> 通过 Server Instructions / Tool Descriptions / Guide Resources 自解释
  -> 只允许控制 Analyzer 自己的 Analysis Profile

外部 DAW-control MCP
  -> 读取 / 修改 / 回读 DAW、工程和插件状态
```

当前 FL Studio 控制层配套项目：

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

Analyzer MCP **不是通用 DAW 控制服务器**。唯一的 Analyzer 自有写入是 `analysis_profile`，因为它只改变 Analyzer 的测量计算量，不改变音频信号。

EQ、Compression、Gain、Pan、Routing、Synth、Automation、Arrangement/Project State 等声音或工程修改仍由外部 DAW-control MCP 负责。

## 架构

```text
FL Studio / DAW
|
+-- Mixer Track A -- AI Audio Analyzer.vst3
+-- Mixer Track B -- AI Audio Analyzer.vst3
+-- Master --------- AI Audio Analyzer.vst3
                         |
                         | OSC，默认 127.0.0.1:9855
                         v
                 Analyzer MCP Bridge
                 +-- Live Instance + 确定性 Binding
                 +-- Analysis Profile + Worker Telemetry
                 +-- DAW Transport + Instance-local Epoch
                 +-- 1 秒 Song Memory + Coverage
                 +-- Section Map / Track Story / Relationships
                 +-- Dynamics Distribution
                 +-- Recent-window Mono-fold Evidence
                 +-- Frozen Session Reference Comparison
                 +-- Recent + Same-range Verification
                 +-- Temporal / Masking / Stereo / Tonal Evidence
                         |
                         v
                  Cherry Studio / LLM
                         |
                         +-- 外部 DAW-control MCP 执行真实修改与回读
```

多个 Analyzer 实例可以向同一 UDP 测量端口发送数据，但只能有一个 Analyzer MCP 进程绑定 UDP `9855`。

LLM 不在实时音频链路内。Agent 思考或调用其他工具时，Analyzer 仍会持续测量。

## 测量与感知能力

- Sample Peak、RMS、Crest Factor；
- `libebur128` 提供 LUFS-S / LUFS-I / True Peak；
- 4096 点 FFT、32 个对数频谱带；
- Spectral Centroid / Rolloff / Flatness；
- 全频段及分频段 Stereo Correlation；
- Mid/Side、Side Spectrum、Side/Mid、Negative-cross Evidence；
- Spectral Flux、RMS Rise、低频时间能量；
- 12-bin Chroma、Tonal-center Ranking、Single-F0 Harmonic Evidence；
- DAW Time / PPQ / BPM / 拍号 / Loop / Play / Record；
- Instance-local Transport Epoch；
- Estimated Analyzer Lag、Dropped Blocks；
- 1 秒 Song Memory + 100 ms Coverage Slot；
- 可解释 Section Boundary 与中性的 A/B/C Recurrence Family；
- Section Profile、Track Story、Section-aware Relationship Shortlist；
- Coverage-aware RMS / LUFS-S / Crest / Peak / True-Peak Distribution；
- Recent-window Mono-fold RMS + 32-band-center Compatibility Evidence；
- Frozen Session Reference Profile + Absolute / RMS-level-normalized Comparison；
- Snapshot A/B、Recent-window Verification、Transport-anchored Same-range Verification；
- Eco / Balanced / Mix / Full Analysis Profile 与 Worker/FIFO Telemetry。

Analyzer 只提供证据，不在 MCP Core 中写死固定流派配方、固定 LUFS 目标、必须执行的 EQ/Sidechain/Compression/Stereo 操作、Verse/Chorus/Drop 语义标签、和声修改、母带链或 Reference Matching 配方。

`null` 表示**不可用**，不是数值 0。缺失 Coverage 不是静音。

## Project / Runtime Identity 范围

当前 `runtime_id` 是**当前运行中的插件实例 UUID**，不是持久 Project ID 或 Track ID。同一个工程重新打开后，Analyzer runtime UUID 会重新生成。

先调用：

```text
audio_project_identity_status()
```

当前保证：

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id scope                        live_plugin_instance
runtime_id persistent                   false
same-project reopen UUID stable         false
binding scope                           mcp_session
cross-project retained-state isolation  not guaranteed
```

在可信的 Project Identity 接入前，如果切换或重新打开工程且需要严格隔离历史状态，应重新启动 Analyzer MCP。

## 确定性 Analyzer ↔ FL Mixer 映射

每个 Analyzer 实例提供：

```text
Parameter ID: identify
Display name: Identify
```

Identify 变化会发送 `/aianalyzer/identify`，Bridge 可以把 runtime UUID 绑定到真实 FL Mixer Track/Slot，然后使用：

```text
mixer:7/slot:9
```

不要在 Identify 可用时根据频谱、名称或音乐角色猜测插件实例身份。Binding 只在当前 MCP Session 内有效。

## Adaptive Analysis Profile

```text
0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

`Full` 是兼容性默认值。

Analyzer 自有控制工具：

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

必须区分：

```text
control_acknowledged  目标 VST3 接收并应用了请求
telemetry_confirmed   新测量帧已经报告目标 Profile
```

该控制只走 Loopback，本身不会改变声音。

## Transport-aware Song Memory

OSC 1.2 将 DAW Transport Context 附到测量数据上：

```text
DAW 播放
-> Analyzer 持续测量
-> MCP 保存 1 秒 DAW-time Bin
-> LLM 之后可以回查已经发生的片段
```

主要工具：

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
```

```text
canonical bin size       1 second
coverage slot            100 ms
retained bins            up to 1200 / Analyzer instance
retained span            about 20 minutes / instance
scope                    current MCP session
```

`transport_epoch` 是单个 Analyzer 实例的一次连续播放 Pass。不同实例的 Epoch 数字不需要相同，也不能当成 Project Identity。

## 可解释歌曲结构

```text
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
```

A/B/C 只表示重复结构 Family，不自动等于 Intro / Verse / Chorus / Drop。

`audio_track_story()` 描述一条轨道在不同 Section 中如何变化；`audio_section_relationships()` 只返回值得进一步检查的有界 Pair Shortlist。

`shortlist_priority` 不是 Masking Probability、问题概率、质量分数或处理命令。

## Coverage-aware Dynamics Distribution

P6a 已合入主线：

```text
audio_dynamics_distribution(...)
```

策略：

```text
minimum per-bin coverage floor
+
covered-seconds weighting
```

可返回 RMS、LUFS-S、Crest、Observed Sample Peak、Observed True Peak 的 P10/P25/P50/P75/P90、IQR、P90-P10 等描述性统计。

关键边界：

- `lufs_s_interpercentile_range_lu` 不是 EBU LRA；
- P6a 没有实现标准化 EBU LRA；
- Arbitrary-range Integrated LUFS 当前不可用；
- Arbitrary-range PLR 当前不可用；
- Section Delta 只是描述，不是质量分数或处理建议。

详见 `skills/ai-analyzer-flstudio/references/dynamics-evidence.md`。

## Energy-aware Mono-fold Compatibility

P7a 已合入主线：

```text
audio_mono_compatibility(track, seconds=5.0)
```

Analyzer 已有：

```text
M = 0.5 * (L + R)
S = 0.5 * (L - R)
(L_power + R_power)/2 = M_power + S_power
```

因此 P7a 不增加新的实时 DSP 或 OSC 字段，就可以返回全频段 Mono-fold RMS Loss、32 个 Band-center 的 Mid/Side Energy Evidence，以及多个频段组的折叠损失。

`inspection_priority` 只是 Energy-aware 检查排序，不是可听问题概率、相位问题概率、质量分数、Pass/Fail 或处理建议。

当前限制：

- 历史任意 Section 的 32-band Mono-fold 需要后续 Retained Detail；
- P7a 不直接测 Mono-fold Sample Peak / True Peak；
- 不允许从 Stereo Peak、True Peak、RMS、Correlation 等反推这两个值。

详见 `skills/ai-analyzer-flstudio/references/mono-compatibility.md`。

## Session-scoped Reference Engine

P8a 新增：

```text
audio_capture_reference(track, label="", seconds=10.0)
audio_list_references()
audio_compare_reference(reference_id, target, seconds=None)
```

Reference 是**冻结的结构化测量 Profile**，不是复制的音频文件。当前只存在于正在运行的 MCP Session 中，并使用 Recent Receive-time Window。

比较保持多个证据维度独立：

```text
Energy / Loudness
32-band Spectrum + Coarse Regions
Stereo Correlation / Width
P7a Mono-fold Compatibility
```

频谱同时提供：

```text
Absolute target_minus_reference

RMS-level-normalized Shape:
target_gain_to_reference_db = reference_rms - target_rms
normalized_delta = (target_band + target_gain_to_reference_db) - reference_band
```

Level-normalized 只是比较视图，不会修改任何音频。

Reference Evidence 是上下文，不是自动配方。MCP 不会把“Reference 在 8 kHz 高 2 dB”直接变成“给目标加 2 dB”，也不会生成全局质量分数，更不会把两个不同歌曲中的 Section Label 自动当成同一个语义结构。

当前 P8a 限制：

- MCP 退出后 Reference 消失；
- Recent-window Capture 不能声称 Whole-song Coverage；
- 历史任意 Section 的 32-band Reference Capture 等待 P4b；
- Persistent Reference Library 等待可信 Project Identity / P5；
- 外部参考音频的 Faster-than-realtime Scan 属于后续 P10。

详见 `skills/ai-analyzer-flstudio/references/reference-comparison.md`。

## Closed-loop Verification

Recent-window：

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

Transport-anchored Same-range：

```text
audio_begin_range_verification(...)
audio_complete_range_verification(...)
audio_range_verification_status(...)
```

Same-range 模式会按 1 秒 Retained Bin 规范化范围、按 Coverage 为每个 Analyzer 独立选择本地 Epoch、防止 Before 数据被误用成 After，并要求调用方提供外部 DAW-control MCP 的真实 Host Readback 才能得到 `closed_loop_complete=true`。

`controlled_comparison=true` 只表示技术上可比较，不表示 After 在艺术上更好。

## Self-describing MCP API

MCP 提供：

```text
Server Instructions
Tool Descriptions
aianalyzer://guide/* MCP Resources
```

`skill/` 仍是长篇知识的唯一规范来源，Resource 按需读取相同 Markdown。

当前共有 **16 个 Guide Resources**，包括：

```text
aianalyzer://guide/index
aianalyzer://guide/core
aianalyzer://guide/analyzer-mcp
aianalyzer://guide/dynamics-evidence
aianalyzer://guide/mono-compatibility
aianalyzer://guide/reference-comparison
aianalyzer://guide/verification-evidence
```

## MCP Tools

MCP **1.2 当前暴露 47 个工具**。

高层工具包括：

```text
audio_project_identity_status()
audio_project_status()
audio_song_status()
audio_song_overview()
audio_section_map(...)
audio_track_story(...)
audio_section_relationships(...)
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
audio_begin_range_verification(...)
audio_complete_range_verification(...)
```

不要机械调用全部 47 个工具。先使用高层工具，再按问题钻取必要证据。

## 用户安装

GitHub Release 面向没有编程经验的用户。

支持：

```text
Windows x64
macOS Apple Silicon arm64
```

每个平台只提供一个最终 ZIP。普通用户包中不会包含 MCP Python 源码、`requirements.txt`、venv、PyInstaller `_internal`、开发配置或嵌套 ZIP。

典型结构：

```text
AI Audio Analyzer.vst3
mcp/
  ai-audio-analyzer-mcp[.exe]   PyInstaller -F 单文件运行时
skill/                          Skill + MCP Resource 内容
START-HERE.md
MCP-SETUP.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
平台安装脚本
```

Windows：解压后运行 `Install.cmd`。

macOS Apple Silicon：解压后运行 `Install.command`。当前 macOS 构建为 Ad-hoc Signed，不是 Developer ID Notarized。

## 当前仓库元数据

```text
Product version             1.2.0
MCP version                 1.2
OSC analysis protocol       1.2
Analyzer control protocol   local revision 1
MCP tools                   47
Self-description schema     1
Guide resources             16
```

P8a 只增加 `mcp/reference_tools.py` 和 MCP/Skill 能力，不改变 VST3 DSP、OSC `0..149` 字段或 Analyzer Control Revision。

`mcp/reference_regression.py` 只用于 CI，不进入 Beginner Release。

## License

AI Audio Analyzer 使用 **MIT License**。详见 [LICENSE](LICENSE)。