# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** 是一个面向 AI / LLM 音乐制作工作流的 JUCE VST3 机器可读音频测量层。

插件直接在 DAW 内测量音频，通过 OSC 将紧凑数据发送给 Analyzer MCP Bridge，再由 Cherry Studio 或其他 MCP 客户端结构化读取电平、响度、频谱、立体声、时间关系、遮蔽、调性、工程概览、**DAW 时间轴整曲记忆、可解释歌曲结构、A/B、性能状态和闭环验证证据**。

当前产品版本：**1.2.0**。

## 项目组成

```text
AI Audio Analyzer
├─ VST3    DAW 内的实时安全测量探针 + Transport Context
├─ MCP     测量 / Song Memory / 结构 / 比较 / 验证工具
└─ Skill   面向 LLM 的英文 MCP 调用和证据语义说明
```

Analyzer 坚持“提供证据，不硬编码审美规则”。不会内置固定 LUFS、Genre EQ、强制 Sidechain/Compression、Stereo 配方、Verse/Chorus/Drop 强制命名、转调、和声修改或母带链。

## 配套 FL Studio MCP

当前工作流配套：

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

```text
AI Audio Analyzer MCP   → 观察 / 测量 / 记忆 / 结构理解 / 比较 / 验证
FL Studio MCP           → 读取 / 控制 / 修改 / 回读 FL Studio
```

Analyzer MCP 本身**不写入 DAW 参数**。真实宿主/工程状态、插件参数写入和回读由实际 DAW Control MCP 负责。

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
                 ├─ Live Instance Registry + 确定性 Track/Slot 映射
                 ├─ Adaptive Analysis / Worker Telemetry
                 ├─ DAW Transport / Continuous Playback Epoch
                 ├─ 1 秒 Song Memory / 多分辨率聚合
                 ├─ 可解释 Section Boundary / A-B-C 重复结构家族
                 ├─ Section Profile / Project Overview / Snapshot A-B
                 ├─ Temporal / Masking / Stereo / Tonal Evidence
                 └─ Closed-loop Verification
                         │
                         ▼
                  Cherry Studio / LLM
                         │
                         └─ 外部 FL Studio MCP 负责实际修改和宿主回读
```

多个 Analyzer 可以共用 UDP `9855`；只有一个 MCP Bridge 进程应绑定该端口。

LLM **不属于实时测量链路**。模型在思考、调用工具或等待 DAW 操作时，Analyzer 仍持续测量并把证据保存到 DAW 时间轴中，之后再由 LLM 查询。

## 当前测量能力

包括：

- Sample Peak、RMS、Crest Factor；
- `libebur128` 提供 LUFS-S / LUFS-I、Current / Pass Max True Peak；
- 4096 点 FFT、Hann Window、20 Hz–20 kHz 的 32 个对数 Mid Spectrum 特征；
- Spectral Centroid、约 85% Rolloff、Flatness；
- Full-band 和 8-band L/R Correlation；
- Spectral Flux、RMS Rise、40–160 Hz Temporal Energy；
- Mid RMS、Side RMS、Side/Mid dB、Side Spectrum、分频段 Stereo 关系和 Negative Cross-Spectrum Evidence；
- 12-bin Chroma、Tonal-center Profile Ranking、Single-F0 Harmonic-alignment Evidence；
- DAW Time / PPQ / BPM / Time Signature、Continuous Playback Epoch、Analyzer Backlog 和 Dropped-block Telemetry；
- 每实例最多 1200 个 1 秒 Song Memory Bin，使用 100 ms Coverage Slot，查询可聚合为 1/2/5/10/15/30 秒；
- 多尺度可解释歌曲段落边界检测和中性的 A/B/C 重复结构家族；
- 即使不同 Analyzer 的实例局部 Epoch 数字不同，也能按 DAW 时间重叠选择对应 Pass，生成 Section 级每轨 Profile；
- Project Overview、Snapshot A/B、Masking Evidence、Controlled Verification 和性能遥测。

### Signal Validity

```text
关闭   低于 -50 dBFS 持续约 0.4 s
重开   高于 -48 dBFS
```

`signal_present=false` 时，依赖内容的字段会变成 unavailable，而不是误导性的 0。`null` 表示**没有有效测量**，不是数值 0。

## Analyzer ↔ FL Mixer 确定性映射

每个 Live Analyzer 都有 Session Runtime UUID，并向宿主公开：

```text
Parameter ID: identify
Display name: Identify
```

每次 Identify 翻转都会发送 `/aianalyzer/identify`。Bridge 可以将 Runtime UUID 绑定到真实 FL Mixer Track / Slot，之后优先使用：

```text
mixer:7/slot:9
```

## Adaptive Analysis

```text
Parameter ID: analysis_profile
Display name: Analysis Profile
0 Eco
1 Balanced
2 Mix
3 Full
```

Profile 只控制**测量计算量**，不会改变声音：

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` 是兼容旧工程的默认值。

Analyzer MCP 提供：

```text
audio_analysis_status(track)
audio_project_performance()
```

遥测包括：

```text
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
```

`worker_load_ratio` 是 **Analyzer 后台 Worker** 的忙碌比例，不是 FL Studio Realtime Audio CPU。实际 Analysis Profile 写入仍由 DAW Control MCP 完成，Analyzer MCP 负责回读/验证。

## 面向 LLM 延迟的 Song Memory

协议 1.2 的目标不是让 LLM 更实时，而是让 LLM **晚几秒也能准确查询刚才发生的音乐**：

```text
DAW 播放
→ Analyzer 持续测量
→ 测量绑定到估算后的 DAW Time / PPQ
→ MCP 写入 1 秒 Song Memory
→ LLM 稍后按整曲 / 时间段读取
```

高层工具：

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(track, resolution_seconds=5, ...)
```

`transport_epoch` 是某个 Analyzer 实例的一次**连续播放 Pass**。停止后重新播放、Seek、Loop 跳回或明显 Transport Discontinuity 都会开启新 Epoch。

Epoch 改变时，Worker 会丢弃旧 FIFO Backlog，并重置 LUFS-I / Pass Max True Peak、Temporal 连续状态和 Semantic Cache。新 Epoch 的 Transport 坐标要等 Worker acknowledgement 后才重新标记有效，避免出现“旧音频 + 新位置”。

不同 Analyzer 的 Epoch 是**实例局部计数器**，不能因为数字相同就假定是同一工程 Pass。

数据质量字段包括：

```text
estimated_analysis_lag_ms
dropped_blocks
data_age_seconds
coverage_ratio
```

`estimated_analysis_lag_ms` 只描述 Analyzer FIFO + FFT Window 的估算滞后，不包含网络或 LLM 思考延迟。

Song Memory 使用 100 ms Coverage Slot，因此把 1 秒 Bin 聚合成 5/10/30 秒时，不会把稀疏数据错误变成 100% 覆盖。

## 可解释歌曲结构理解层

第一版歌曲结构层完全建立在已有 Song Memory 上，**不增加实时 DSP，不修改 OSC 1.2 Wire Format，也不引入神经网络**。

流程：

```text
Song Memory
→ Robust Feature Normalization
→ 2 / 4 / 8 秒多尺度前后窗口比较
→ Explainable Novelty Curve
→ Adaptive Threshold + Minimum Section Spacing
→ S01 / S02 / ... Section
→ Section Similarity
→ 中性 A / B / C / ... 重复结构家族
```

工具：

```text
audio_section_map(
  reference_track=None,
  transport_epoch=None,
  min_section_seconds=8,
  sensitivity=0.55,
  family_similarity=0.78,
  max_sections=48,
  max_tracks=32
)

audio_section_profile(section_id, map_id=None, max_tracks=32, max_related=8)
```

Boundary Detection 会综合可用的：

```text
跨轨 Active / Inactive 变化
RMS / LUFS-S
Spectral Centroid / Broad Spectral Balance
Chroma
Stereo Correlation / Width
Crest / Spectral Flux
```

`boundary strength` 只是**结构变化证据**，不是“这里一定是正式段落边界”的概率。

Section 会得到类似：

```text
S01  A
S02  B
S03  C
S04  B
S05  C
```

这里的 A/B/C 只表示“结构上存在重复/相似”，**绝不自动等于**：

```text
A = Intro
B = Verse
C = Chorus
```

如果 FL Studio / DAW MCP 能提供 Marker、Playlist Label、Pattern Name、Arrangement Metadata、MIDI/Project Annotation，或者用户明确给出了结构，那么这些精确工程信息优先用于命名。

跨轨 Section 分析不会要求各实例 Epoch 数字相同。它会在同一 DAW 时间范围内为每个支持轨选择**覆盖最好**的保留 Pass。例如：

```text
Master epoch 7
Kick epoch 3
Vocal epoch 11
```

仍然可以属于同一实际歌曲范围。

缺失 Song Memory 也不会被当成静音或段落边界；`coverage_gaps` 会显式告诉 LLM 哪里缺数据。

推荐整曲调用顺序：

```text
audio_project_status()
→ audio_song_status()
→ 播放/采集足够的目标 Pass
→ audio_section_map()
→ 只对相关 Section 调用 audio_section_profile()
→ 仍需原始时间变化时才调用 audio_song_timeline()
→ 再针对具体关系调用 Temporal / Masking / Stereo / Tonal
```

这样可以显著减少 LLM Token 消耗，也避免整曲混音只依赖“最近 5 秒”。

## 其他证据层

Temporal：

```text
audio_temporal_profile()
audio_temporal_compare()
```

Masking：

```text
audio_masking_evidence()
audio_project_masking_scan()
```

当前 Masking 使用 equal-ERB-rate feature re-binning，不是经过听阈校准的 cochlear 模型，分数不是可听遮蔽概率。

Stereo / Mid-Side：

```text
audio_stereo_profile()
audio_stereo_compare()
```

Signed Correlation、Side/Mid Energy、Negative-cross 和各频段 Stereo 关系保持独立，不定义万能 Stereo 目标。

Tonal：

```text
audio_tonal_profile()
audio_tonal_compare()
```

Chroma / Tonal-center / Single-F0 都属于音频域证据，不是精确 Key / Note 概率。精确符号信息应优先使用 DAW/MIDI 数据。

## Closed-loop Verification

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

流程：

```text
Before Baseline
→ 外部 DAW MCP 实际写入
→ 回读真实宿主状态
→ Comparable After Capture
→ Comparability Guardrails
→ After - Before Deltas
```

`controlled_comparison=true` 只表示技术可比性通过；`closed_loop_complete=true` 还要求实际 Host Readback。两者都不表示“After 更好”。

当前 Verification 仍是 Recent-window 模式，尚未实现 Transport-anchored Same-range Verification。

## MCP 工具

MCP **1.2 共 34 个工具**。整曲/结构高层入口包括：

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
audio_section_map(...)
audio_section_profile(...)
```

不要为了“完整”机械调用全部 34 个工具。应先高层理解整曲/Section，再按具体问题下钻。

## 用户安装

GitHub **Release 懒人包按“没接触过编程也能安装”设计**。

支持：

```text
Windows x64
macOS Apple Silicon arm64
```

每个平台一个最终 ZIP，只解压一次。

```text
AI Audio Analyzer.vst3
mcp/
└─ ai-audio-analyzer-mcp[.exe]   PyInstaller -F 单文件程序
skill/
START-HERE.md
MCP-SETUP.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
平台安装文件
```

用户 Release **不会包含 MCP Python 源码**、`requirements.txt`、venv、PyInstaller `_internal`、开发源码配置示例或嵌套 ZIP。

Windows：双击 `Install.cmd`。

macOS Apple Silicon：双击 `Install.command`。当前 macOS 包为 ad-hoc 签名，并非 Apple Developer ID Notarization。

安装器会生成带真实 MCP 可执行文件绝对路径的 `cherry-studio-mcp.json`。按照 `MCP-SETUP.md` 添加到支持 MCP 的 Agent/Assistant，并给同一个 Agent 导入 `skill` 文件夹。

## 仓库 MCP 架构

源码和 PyInstaller 永远只有一个入口：

```text
mcp/server.py
```

当前版本关系：

```text
Product version       1.2.0
MCP version           1.2
OSC protocol version  1.2
MCP tools             34
```

内部模块：

```text
mcp/server.py             启动 / Self-test / Tool Registry
mcp/analyzer_core.py      OSC State / Identity / Binding / Base Tools
mcp/project_tools.py      Project Overview / Snapshot A-B
mcp/temporal_tools.py     Temporal
mcp/masking_tools.py      Masking Evidence
mcp/stereo_tools.py       Mid/Side + Stereo
mcp/semantic_tools.py     Chroma / Tonal-center / Harmonic Evidence
mcp/performance_tools.py  Adaptive Profile / Worker Telemetry
mcp/song_tools.py         DAW Transport / Pass Memory / Song Summaries
mcp/section_tools.py      Section Boundary / Recurrence / Section Profile
mcp/verification_tools.py Controlled Verification
mcp/ci_regression.py      仓库内 Synthetic Regression
```

## OSC Protocol

Analysis Address：`/aianalyzer/frame`。

OSC **1.2** 继续保持 Append-only。当前尾部：

```text
128  analysis_profile
129  analysis_feature_mask
130  worker_load_ratio
131  fifo_fill_ratio
132  fft_runs_per_second
133  semantic_runs_per_second
134  schema marker = "1.1"
135  transport_supported
136  transport_time_seconds
137  transport_ppq_position
138  transport_bpm
139  transport_time_signature_numerator
140  transport_time_signature_denominator
141  transport_is_playing
142  transport_is_recording
143  transport_is_looping
144  transport_loop_start_ppq
145  transport_loop_end_ppq
146  transport_epoch
147  estimated_analysis_lag_ms
148  dropped_blocks
149  schema marker = "1.2"
```

歌曲结构层只读取 MCP Song Memory，不修改上述协议。

## License

AI Audio Analyzer 使用 **MIT License**。详见 [LICENSE](LICENSE)。
