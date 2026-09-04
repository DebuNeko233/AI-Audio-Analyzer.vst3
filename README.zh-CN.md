# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** 是一个面向 AI / LLM 音乐制作工作流的 JUCE VST3 机器可读音频测量层。

插件直接在 DAW 内测量音频，通过 OSC 将紧凑数据发送给 Analyzer MCP Bridge，再由 Cherry Studio 或其他 MCP 客户端结构化读取电平、响度、频谱、立体声、时间关系、遮蔽、调性、工程概览、**DAW 时间轴整曲记忆**、A/B、性能状态和闭环验证证据。

当前产品版本：**1.2.0**。

## 项目组成

```text
AI Audio Analyzer
├─ VST3    DAW 内的实时安全测量探针
├─ MCP     结构化测量 / 时间轴 / 比较 / 验证工具
└─ Skill   面向 LLM 的英文 MCP 调用和参数语义说明
```

Skill **不是风格化混音/和声教程**，不会内置固定 LUFS、EQ、压缩、Sidechain、Stereo、转调、和声修改或母带处理配方。

## 配套 FL Studio MCP

当前工作流配套：

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

```text
AI Audio Analyzer MCP   → 观察 / 测量 / 记忆 / 比较 / 验证
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
                 ├─ DAW Transport / Continuous Playback Epoch
                 ├─ 1 秒 Song Timeline Memory / 多分辨率聚合
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

LLM **不属于实时测量链路**。模型在思考、调用工具或等待外部 DAW 操作时，Analyzer 仍会持续测量并把证据保存到 DAW 时间轴记忆中。这样 LLM 晚几秒读取也不会错过刚才发生的音乐内容。

## 当前测量能力

主要能力包括：

- Sample Peak、RMS、Crest Factor；
- `libebur128` 提供 LUFS-S / LUFS-I、Current / Pass Max True Peak；
- 4096 点 FFT、Hann Window、20 Hz–20 kHz 的 32 个对数 Mid Spectrum 特征；
- Spectral Centroid、约 85% Rolloff、Flatness；
- Full-band 和 8-band L/R Correlation；
- Spectral Flux、RMS Rise、40–160 Hz Temporal Energy；
- Mid RMS、Side RMS、Side/Mid dB、Side Spectrum、分频段 Side/Mid、低频 Stereo Relation 和 Negative Cross-Spectrum Evidence；
- 12-bin Mid-spectrum Chroma、Tonal-center Profile Ranking 和 Single-F0 Harmonic-alignment Evidence；
- DAW Transport Time / PPQ / BPM / Time Signature、Continuous Playback Epoch、Analyzer Backlog Estimate 和 Dropped-block Telemetry；
- 每个 Analyzer 最多 1200 个 1 秒 Song Memory Bin（20 分钟），查询时可聚合为 1/2/5/10/15/30 秒；
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

大型工程可能在很多 Mixer Track 上都插入 Analyzer，没有必要让每个实例永久运行全部分析。因此插件提供真实宿主参数：

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

Analyzer MCP 提供：

```text
audio_analysis_status(track)
audio_project_performance()
```

重要遥测：

```text
worker_load_ratio
fifo_fill_ratio
fft_runs_per_second
semantic_runs_per_second
```

`worker_load_ratio` 只是 **Analyzer 后台 Worker 的忙碌比例**，不是 FL Studio Realtime Audio CPU。`fifo_fill_ratio` 持续升高说明分析可能逐渐落后于 DAW 当前播放位置。

为了保持 append-only OSC 兼容，被关闭的功能仍保留字段位置，但 Bridge 会依据 Feature Mask 将其显式标记为 unavailable。

### 面向 LLM 延迟的整曲时间轴记忆

协议 1.2 的核心目标不是让 LLM “更实时”，而是让 LLM **即使晚几秒也能查询刚才的音乐**：

```text
DAW 播放
→ Analyzer 持续测量
→ 测量帧绑定到估算后的 DAW Time / PPQ
→ MCP 写入 1 秒 Song Memory
→ LLM 稍后按整曲 / 时间段查询
```

高层工具：

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(track, resolution_seconds=5, ...)
```

`transport_epoch` 表示某个 Analyzer 实例的一次**连续播放段**。以下情况会开启新的 Epoch：

```text
停止后重新播放
Seek / 拖动播放头
Loop 跳回
其他明显 Transport Discontinuity
```

Epoch 改变时，Worker 会丢弃 FIFO 中旧 Epoch 的积压音频，并重置 LUFS-I / Pass Max True Peak、Temporal Previous-state 和 Semantic Cache，避免把跳转前后的音频错误拼成同一次连续播放。

`transport_epoch` 是**实例局部计数器**。不同 Analyzer 如果加载时间不同，不应只凭相同 Epoch 数字认定属于同一工程 Pass。Project Song 工具会报告 Epoch 是否一致，并保留真实 DAW 时间范围供 LLM 判断。

为了考虑 Analyzer 自身延迟，协议同时提供：

```text
estimated_analysis_lag_ms
dropped_blocks
data_age_seconds
```

`estimated_analysis_lag_ms` 是由 FIFO Backlog + FFT Window Center 估算的 Analyzer 处理滞后，不包含网络延迟，也不包含 LLM 思考延迟。LLM 应优先读取 Song Memory，而不是假设“最新收到的一帧就是 DAW 此刻正在发出的声音”。

当前 Song Memory 只保存在 MCP Session 内存中，还不是永久工程数据库；自动 Verse / Chorus / Bridge 分段和命名也尚未实现。

对于协议 1.2 Analyzer，LUFS-I 和 Pass Max True Peak 在 Transport Epoch 改变时重新开始累计；Snapshot 工具自身不会额外重置 Loudness。Legacy Analyzer 保留旧的 Reset / Prepare 语义。

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

Signed L/R Correlation、Side/Mid Energy、Decorrelation Proxy、Negative Cross-Spectrum、低频 Stereo Relation 和分频段 Stereo 关系保持独立，不定义统一 Stereo 目标。

### 音频域调性 / Music-semantic Evidence

```text
audio_tonal_profile(track, seconds=8)
audio_tonal_compare(track_a, track_b, seconds=8)
```

Analyzer 提供 normalized 12-bin Chroma、Chroma Energy Coverage、Tonal-center Template Correlation 和 Single-F0 Harmonic-alignment Evidence。涉及精确 Note、Key、Chord、Tuning 时，如果 DAW/MIDI MCP 有真实符号数据，应优先使用该数据。

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

`controlled_comparison=true` 只表示当前技术 Guardrails 通过，不代表 After 更好、设置正确或应该保留修改。

`closed_loop_complete=true` 还要求调用方提供真实宿主回读。当前 Verification 仍是 Recent-window 模型；未来会在 Song Timeline 上进一步加入“同一 DAW 时间段”的 Transport-anchored Verification。

## MCP 工具

MCP **1.2 共 32 个工具**。新增整曲高层入口：

```text
audio_song_status()
audio_song_overview(transport_epoch=None, max_tracks=32)
audio_song_timeline(track, resolution_seconds=5, transport_epoch=None, start_seconds=None, end_seconds=None, max_bins=240)
```

整曲混音/母带任务建议：

```text
audio_project_status()
→ audio_song_status()
→ audio_song_overview()
→ 根据需要读取某轨 audio_song_timeline()
→ 再针对具体问题调用 Temporal / Masking / Stereo / Tonal 工具
```

不要为了“完整”机械调用全部 32 个工具。

## 用户安装

GitHub **Release 懒人包按照“完全没接触过编程也能安装”设计**。

当前平台：

```text
Windows x64
macOS Apple Silicon arm64
```

每个平台只提供一个最终 ZIP，用户只需要解压一次，不会 ZIP 套 ZIP。

```text
AI Audio Analyzer.vst3
mcp/
└─ ai-audio-analyzer-mcp[.exe]   PyInstaller -F 单文件程序
skill/
START-HERE.md
MCP-SETUP.md                     Agent/MCP 配置说明 + 可复制 JSON 示例
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
对应平台的一键安装文件
```

用户 Release **不会包含 MCP Python 源码**、`requirements.txt`、venv、PyInstaller `_internal`、开发源码配置示例或嵌套 ZIP。

Windows：全部解压后双击 `Install.cmd`。

macOS Apple Silicon：解压后双击 `Install.command`。如果 Gatekeeper 阻止运行，右键 → **打开**。当前 macOS 包是 ad-hoc 签名，不是 Apple Developer ID Notarization。

安装器会生成包含真实 MCP 可执行文件绝对路径的 `cherry-studio-mcp.json`。按照 `MCP-SETUP.md` 把配置加入支持 MCP 的客户端，并**启用给真正要使用 Analyzer 的 Agent/Assistant**，再把 `skill` 文件夹导入给同一个 Agent。

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
MCP tools             32
```

内部模块：

```text
mcp/server.py             启动 / Self-test / Tool Registry
mcp/analyzer_core.py      OSC 状态、身份映射、基础工具
mcp/project_tools.py      Project Overview / Snapshot A-B
mcp/temporal_tools.py     Temporal Layer
mcp/masking_tools.py      Masking Evidence Layer
mcp/stereo_tools.py       Mid/Side + Stereo Layer
mcp/semantic_tools.py     Chroma / Tonal-center / Harmonic Evidence
mcp/performance_tools.py  Adaptive Profile / Worker Telemetry
mcp/song_tools.py         DAW Transport / Song Pass / Latency-aware Timeline Memory
mcp/verification_tools.py Closed-loop Verification
mcp/ci_regression.py      仓库专用 Synthetic Regression
```

`mcp/ci_regression.py` 不进入普通用户 Release。

## Skill

LLM-facing Skill 统一使用英文，主要参考：

```text
skills/ai-analyzer-flstudio/SKILL.md
skills/ai-analyzer-flstudio/README-CHERRY-STUDIO.md
skills/ai-analyzer-flstudio/references/analyzer-mcp.md
skills/ai-analyzer-flstudio/references/parameters.md
skills/ai-analyzer-flstudio/references/performance-evidence.md
skills/ai-analyzer-flstudio/references/song-memory.md
skills/ai-analyzer-flstudio/references/masking-evidence.md
skills/ai-analyzer-flstudio/references/stereo-evidence.md
skills/ai-analyzer-flstudio/references/tonal-evidence.md
skills/ai-analyzer-flstudio/references/verification-evidence.md
```

Skill 只负责工具调用、Selector / Mapping、Profile 选择、有效性、时间轴/延迟和参数/证据语义，不预设混音审美或处理动作。

## OSC 协议

Analysis 地址：`/aianalyzer/frame`。

OSC **1.2** 继续保持 append-only：

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
135        transport_supported
136        transport_time_seconds
137        transport_ppq_position
138        transport_bpm
139        transport_time_signature_numerator
140        transport_time_signature_denominator
141        transport_is_playing
142        transport_is_recording
143        transport_is_looping
144        transport_loop_start_ppq
145        transport_loop_end_ppq
146        transport_epoch
147        estimated_analysis_lag_ms
148        dropped_blocks
149        schema marker = "1.2"
```

已有 `0..134` 不重新解释。历史 `11..42` 仍是 32-band Mid Spectrum。Identify 地址仍是 `/aianalyzer/identify`。

## 实时线程原则

Audio Callback 不执行 FFT、响度、Semantic、OSC、MCP、Verification、文件或网络 I/O。Audio Sample 只写入预分配 SPSC FIFO，其余分析在后台线程完成。

DAW Transport 在 `processBlock()` 中从宿主读取，但只通过 Atomic 交给 Worker，不进行网络 I/O、锁或重分析。Transport Epoch 改变后，由后台 Worker 异步丢弃旧 FIFO Backlog 并重置跨 Pass 状态。

功能重新开启时，跨越“未分析空档”会造成语义污染的状态同样会重置：Loudness 重建 ebur128，Temporal 清理 Previous Spectrum / Accumulator，Semantic 清缓存。

## 当前限制

- Transport Time / PPQ 是考虑当前 FIFO Backlog 和 FFT Window Center 后的 Worker-side 估算，适合整曲/段落推理，不是 Sample-accurate 编辑坐标；
- Song Memory 目前只存在 MCP Session 内存中，还没有永久 Project Database；
- 尚未自动识别/命名 Verse、Chorus、Bridge；
- `transport_epoch` 是 Instance-local，不是永久 Project-wide Pass ID；
- Performance Telemetry 是 Analyzer Worker 自身遥测，不是 DAW/System CPU Profiler；
- ERB 仍是 feature re-binning，Masking Evidence 仍是 heuristic；
- Stereo、Temporal、Tonal 指标都是测量/证据，不是 Quality Score；
- Chroma 不是 Transcription，Tonal-center Ranking 不是精确 Key Detection；
- Single-F0 Harmonic Evidence 在 Polyphonic / Noisy / Inharmonic Material 上可能不稳定；
- `host_readback` 由调用方/外部 Control MCP 提供，Analyzer 不独立验证；
- Verification Session 和 FL Mixer Binding 都是 Session-scoped；
- 对协议 1.2 实例，LUFS-I / Pass Max True Peak 在当前连续 Transport Epoch 内累计；Playback Start、Seek、Loop 跳转或 Loudness 重新启用都会开始新的 Loudness 状态。Legacy 实例保留旧 Reset / Prepare 语义；
- macOS Release 仅支持 Apple Silicon，且当前未 Notarize。

## 仓库结构

```text
Source/                         JUCE VST3
mcp/server.py                   唯一 MCP 入口
mcp/analyzer_core.py            稳定内部 MCP/OSC Core
mcp/*_tools.py                  功能模块（包括 Song Timeline Memory）
mcp/ci_regression.py            仓库专用 MCP Regression
skills/ai-analyzer-flstudio/    英文 LLM-facing Skill
release/                        普通用户 Release 安装器/说明
.github/workflows/build.yml     开发 CI
.github/workflows/release.yml   手动 Release 打包
AGENT.md                        Agent / Maintainer 约束与历史
```

修改仓库前请先阅读 `AGENT.md`。

## 开源协议

AI Audio Analyzer 项目代码采用 **MIT License** 开源，完整协议见 [LICENSE](LICENSE)。

第三方依赖和组件继续遵循各自许可证；本仓库的 MIT License 不会替代或覆盖这些第三方许可证条款。