# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** 是面向 AI / LLM 音乐制作工作流的 JUCE VST3 机器可读音频测量层。

它在 DAW 内测量音频，通过 OSC 向 Analyzer MCP Bridge 发送结构化数据，并向 Cherry Studio 或其他 MCP 客户端提供电平、响度、频谱、立体声、时间关系、遮蔽、调性、工程状态、DAW 时间轴 Song Memory、可解释歌曲结构、Track Story、Section-aware Mix Relationships、Coverage-aware Dynamics Distribution、Energy-aware Mono-fold Compatibility、性能遥测、身份范围说明和闭环验证证据。

当前产品版本：**1.2.0**。

## 系统边界

```text
AI Audio Analyzer VST3
  -> 实时安全测量 + DAW Transport Context

AI Audio Analyzer MCP
  -> 观察 / 记忆 / 结构 / 比较 / 验证
  -> 明确告知当前 Project / Runtime Identity 能保证什么、不能保证什么
  -> 通过 Server Instructions / Tool Description / Guide Resources 自解释
  -> 只允许控制 Analyzer 自己的 Analysis Profile

外部 DAW-control MCP
  -> 读取 / 修改 / 回读 DAW、工程和插件状态
```

当前 FL Studio 控制层配套项目：

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

Analyzer MCP **不是通用 DAW 控制服务器**。唯一的 Analyzer 自有写入是宿主可见的 `analysis_profile` 参数，因为它只改变测量计算量，不改变音频信号。

EQ、Compression、Gain、Pan、Routing、Synth、Automation、Arrangement/Project State 等声音或工程修改仍由外部 DAW-control MCP 负责。

## 架构

```text
FL Studio / DAW
|
+-- Mixer Track A -- AI Audio Analyzer.vst3
+-- Mixer Track B -- AI Audio Analyzer.vst3
+-- Master --------- AI Audio Analyzer.vst3
                         |
                         | OSC 测量，默认 127.0.0.1:9855
                         v
                 Analyzer MCP Bridge
                 +-- Server Instructions + Tool Descriptions
                 +-- 按需 aianalyzer://guide/* Resources
                 +-- Live Instance Registry + 确定性 Binding
                 +-- Project / Runtime Identity Scope Disclosure
                 +-- Adaptive Analysis / Worker Telemetry
                 +-- Analyzer 自有 Loopback Profile Control + ACK
                 +-- DAW Transport + 实例局部 Playback Epoch
                 +-- 1 秒 Song Memory + Coverage Accounting
                 +-- 可解释 Section Boundary + Recurrence Family
                 +-- Track Story
                 +-- 有界 Section-aware Relationship Shortlist
                 +-- Coverage-aware Retained Dynamics Distribution
                 +-- Recent-window Direct Mono-fold RMS / Energy Evidence
                 +-- Recent-window + Transport-range Verification
                 +-- Temporal / Masking / Stereo / Tonal Evidence
                         |
                         v
                  Cherry Studio / LLM
                         |
                         +-- 外部 DAW-control MCP 执行真实修改/回读
```

多个 Analyzer 实例可以发送到同一个 UDP 测量端口；只有一个 MCP Bridge 应绑定 UDP `9855`。

LLM 不在实时音频测量链路内。Agent 思考或调用其他工具时，Analyzer 仍持续测量。

## 当前测量能力

- Sample Peak、RMS、Crest Factor；
- `libebur128` 提供 LUFS-S / LUFS-I / True Peak；
- 4096 点 FFT、32 个对数频谱带；
- Spectral Centroid / Rolloff / Flatness；
- 全频段和分频段 Stereo Correlation；
- Mid/Side、Side Spectrum、Side/Mid、Negative-cross Evidence；
- Spectral Flux、RMS Rise、Low-band Temporal Energy；
- 12-bin Chroma、Tonal-center Ranking、Single-F0 Harmonic Evidence；
- DAW Time / PPQ / BPM / Time Signature / Loop / Play / Record；
- 实例局部 Transport Epoch；
- Estimated Analyzer Lag / Dropped Blocks；
- 1 秒 Song Memory + 100 ms Coverage Slot；
- 可解释 Section Boundary + 中性 A/B/C Recurrence Family；
- Section Profile、Track Story、Section-aware Relationship Shortlist；
- Coverage-aware RMS / LUFS-S / Crest / Observed Peak Distribution；
- 基于现有 Mid/Side 证据的 Recent-window Direct Mono-fold RMS 与 32 Band-center Energy Compatibility；
- Project Snapshot A/B、Recent-window Verification；
- Transport-anchored Same-range Before/After Verification；
- Adaptive Analysis Profile 与 Worker/FIFO Telemetry。

Analyzer 坚持“提供证据，不硬编码审美规则”。不会内置固定 LUFS、Genre EQ、强制 Sidechain/Compression/Stereo 配方、Verse/Chorus/Drop 强制命名、转调、和声修改或母带链。

`null` 表示**不可用**，不是数值 0。

缺失的 Retained Coverage 不等于静音。

## Project / Runtime Identity 范围

当前 Analyzer 的 `runtime_id` 是**一次 Live Plugin Instance 的 UUID**，不是永久 Project ID，也不是永久 Track ID。

VST3 不会把这个 Runtime UUID 序列化保存进工程，因此即使重新打开的是**同一个 FL Studio 工程**，Analyzer Runtime UUID 也会重新生成。

调用方可以直接调用：

```text
audio_project_identity_status()
```

当前会明确返回类似：

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id scope                        live_plugin_instance
runtime_id persistent                   false
same-project reopen UUID stable         false
binding scope                           mcp_session
cross-project retained-state isolation  not guaranteed
```

这意味着：

- 不要把 `runtime_id` 当永久 Project/Track 身份；
- 新的 Runtime UUID **不能证明**用户已经切换了工程，因为重新打开同一个工程也会产生新 UUID；
- `mixer:<index>/slot:<slot>` Binding 是当前 MCP Session 内的确定性定位，不是永久 Track ID；
- 如果 MCP 进程一直运行，Song Memory、Section Map、Snapshot、Relationship、Verification 等 Session Memory 可能在用户切换/重开工程后继续留在内存里；
- 当前还不能保证这些 Retained State 已按稳定 Project ID 自动隔离；
- 在 P3/P5 接入可信 Project Identity 之前，如果需要严格工程隔离，切换或重新打开工程后应重启 Analyzer MCP，再进行新的分析。

绝不能用 BPM、轨道数量、轨道名、Mixer Index、Topology Fingerprint、Transport Epoch 或 Runtime UUID 自己拼一个“Project ID”。

## Analyzer ↔ FL Mixer 确定性映射

每个 Live Analyzer 都有 Session Runtime UUID，并公开：

```text
Parameter ID: identify
Display name: Identify
```

Identify 切换会发出 `/aianalyzer/identify`。Bridge 可以把该 Runtime UUID 绑定到真实 FL Mixer Track/Slot，之后优先使用：

```text
mixer:7/slot:9
```

不要根据轨名或音频内容猜测实例身份。

Binding 只在当前 MCP Session 内有效。插件实例重建或工程重新打开后需要重新 Identify/Bind。

## Adaptive Analysis Profile

```text
Parameter ID: analysis_profile
Display name: Analysis Profile

0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

`Full` 是兼容默认值。

Analyzer 自有控制工具：

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

必须区分：

```text
control_acknowledged  目标 VST3 已接受/应用请求
telemetry_confirmed   新测量帧已经报告目标 Profile
```

这条控制链只在本机 Loopback 内工作，不改变声音。

## Transport-aware Song Memory

协议 1.2 把 DAW Transport Context 附加到测量，使 LLM 可以在音乐经过后再查询。

```text
DAW 播放
-> Analyzer 持续测量
-> MCP 保存 1 秒 DAW-time Bin
-> LLM 稍后查询 Retained Evidence
```

高层工具：

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
```

Song Memory：

```text
Canonical Bin           1 秒
Coverage Slot           100 ms
Retained Bins           每 Analyzer 最多 1200
Retained Span           每实例约 20 分钟
Query Resolutions       1 / 2 / 5 / 10 / 15 / 30 秒
Scope                   当前 MCP Session
```

`transport_epoch` 是某个 Analyzer 实例的一次连续播放 Pass。不同实例独立计数，数字相同不代表工程全局同一 Pass。

Song Memory 当前还没有 Stable Project ID 分区。用户切换/重开工程但 MCP 不重启时，必须把旧 Retained Evidence 视为“可能属于之前工程”。

Transport 坐标适合整曲/Section/Range 推理，不是 Sample-accurate 编辑坐标。

## 可解释歌曲结构

```text
Song Memory
-> Robust Normalization
-> 2 / 4 / 8 秒 Novelty
-> Adaptive Boundaries
-> S01 / S02 / ...
-> 中性 A / B / C / ... Recurrence Family
```

工具：

```text
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
```

A/B/C 只是重复结构家族，不自动等于 Intro/Verse/Chorus/Drop。

### Track Story

`audio_track_story(track, map_id)` 汇总单条 Analyzer 在各 Section 中的 Activity、Level、Spectrum、Stereo、Temporal、Chroma、Coverage/Lag/Drop、相邻 Delta、同 Family 各维度变化和相对极值。

它不会生成统一“质量/一致性分数”，也不会仅凭测量推断轨道角色或自动要求处理。

### Section-aware Mix Relationships

`audio_section_relationships(...)` 返回有界的 Pair Shortlist，用于指出哪些轨道关系在特定 Section/Family 值得继续检查。

`shortlist_priority` 只是检查优先级，不是 Masking Probability、Audibility Probability、Mix-problem Probability、Quality Score 或处理建议。

详细 Masking/Stereo/Temporal Pair 工具仍是 Recent-window；历史 Section Shortlist 不会自动让它们变成 Historical Range Analyzer。

## Coverage-aware Dynamics Distribution

P6a 新增一个高层工具：

```text
audio_dynamics_distribution(
  track,
  transport_epoch=None,
  start_seconds=None,
  end_seconds=None,
  map_id=None,
  section_id=None,
  compare_section_id=None,
  minimum_range_coverage=...,
  minimum_bin_coverage=...
)
```

支持 Selected Retained Pass Span、显式 DAW-time Range、Cached Section Map Section，并可通过 `compare_section_id` 做 Section-to-section 描述性对比。

Coverage Policy：

```text
每个 1 秒 Bin 的最小 Coverage Floor
+
Accepted Bin 按 Covered Seconds 加权
```

返回结果会明确给出 Accepted / Rejected / Missing Bin 数量；Missing Coverage 永远不会被补成 Silence 或 0。

当前可输出 RMS、LUFS-S、Crest、Observed Sample-Peak Maxima、Observed True-Peak Maxima 的 P10/P25/P50/P75/P90、IQR、P90-P10 Spread 等描述性统计。RMS 还会单独给出 Covered-seconds Power-domain Mean，避免把 dB Percentile 和能量平均混为一谈。

重要边界：

- `lufs_s_interpercentile_range_lu` 只是 `P90(LUFS-S) - P10(LUFS-S)`，**不是 EBU Loudness Range**；
- P6a 不实现标准 EBU LRA；
- Retained `lufs_i_latest` 是 Pass-cumulative，因此不能冒充 Arbitrary-range Integrated LUFS；
- 没有 Scope-compatible Integrated Loudness 时，不输出 Arbitrary-range PLR；
- Section Delta 只是描述证据，不是 Quality Score 或处理建议；
- MCP Core 不内置固定 Genre/Mastering LUFS、Crest、LRA、PLR Target。

详细语义见 `skills/ai-analyzer-flstudio/references/dynamics-evidence.md`。

## Energy-aware Mono-fold Compatibility

P7a 新增一个直接的 Recent-window Fold-down 工具：

```text
audio_mono_compatibility(track, seconds=5.0)
```

VST3 现有 Worker 已经计算：

```text
M = 0.5 * (L + R)
S = 0.5 * (L - R)
```

因此 P7a 不需要增加 Realtime DSP 或 OSC 字段。现有 Mid RMS 就是普通 `(L+R)/2` Mono Fold 的 RMS，并且：

```text
(L_power + R_power)/2 = M_power + S_power
```

工具会返回 Direct Full-band Fold-down Evidence 和 32 个 Analyzer Band-center Energy Evidence，包括：

```text
stereo_rms_db
mono_fold_rms_db
mono_fold_rms_delta_db
mid_db / side_db
stereo_equivalent_energy_db
mono_fold_delta_db
energy_loss_fraction
relative_band_energy
inspection_priority
```

还会按 `20-120 Hz`、`120-500 Hz`、`500 Hz-2 kHz`、`2-5 kHz`、`5-20 kHz` 给出分组摘要。

`inspection_priority` 只是 Energy-aware Inspection Shortlist，不是 Audibility Probability、Phase-problem Probability、Quality Score、Pass/Fail Threshold 或处理建议。

当 Mid 到达 Analyzer 的 `-120 dB` 测量地板时，结果会标记 `floor_censored=true`，返回受测量地板约束的相对损失，而不是伪造一个低于测量能力的“精确抵消深度”。

当前边界是有意保留的：

- P7a 是 Recent Receive-time Evidence，不是任意 Historical/Section 32-band 分析；
- 当前 Song Memory 没有保留完整 Historical 32-band Mid/Side Detail；
- P7a 不直接测量 Mono-fold Sample Peak；
- P7a 不直接测量 Mono-fold True Peak；
- 不能从 Stereo Peak、True Peak、RMS、Correlation 或 Side/Mid 推算这两个 Peak 指标；
- Direct Peak / True-Peak Fold-down 属于可选 P7b；
- Correlation、Side/Mid、Negative-cross 和 Direct Fold-down Loss 必须继续作为独立证据维度；
- MCP 不内置 `correlation < 0 = bad`、`all lows must be mono`、`mono_fold_delta < X = fail` 这类固定规则。

详细语义见 `skills/ai-analyzer-flstudio/references/mono-compatibility.md`。

## Closed-loop Verification

现在有两条验证路径。

### Recent-window Verification

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

当无法或没有必要指定明确 DAW-time Range 时使用。

### Transport-anchored Same-range Verification

当 Agent 可以确定并重放一个 DAW 时间范围时优先使用：

```text
audio_begin_range_verification(
  label,
  start_seconds,
  end_seconds,
  target_selectors=None,
  minimum_coverage=...
)

-> 外部 DAW-control MCP 执行真实修改
-> 外部 DAW-control MCP 回读实际宿主状态
-> 重放返回的 effective_range

audio_complete_range_verification(
  verification_id,
  change_summary="...",
  host_readback="..."
)

audio_range_verification_status(...)
```

关键语义：

- 小数范围会同时返回 Requested Range 与按 1 秒 Song Memory 归一后的 `effective_range`；
- 每个 Analyzer 独立选择覆盖最佳的本地 Epoch；
- Pass 选择先看 Coverage，再用 Recency 破平局；
- 跨轨不要求 Epoch 数字相同；
- After 必须来自冻结 Receive-time Fence 之后首次观测到的干净 Retained Pass；
- 修改前 Song Memory 不能被偷偷复用为 After；
- 历史可比性看 Retained Evidence 实际拥有的测量族，不拿“当前 Profile”冒充过去的 Profile；
- 若选中 After 的累计 Dropped Blocks 更高，则不通过 Controlled Comparison；
- Same-range 模式中的 `active_ratio` 是描述证据，不再充当 Passage Identity；
- 当前不会伪造 Arbitrary-range LUFS-I Delta，因为 Retained `lufs_i_latest` 是 Pass-cumulative，而不是任意范围独立积分值；
- Analyzer 仍不执行任何改变声音的写入。

同样需要注意：Same-range Verification 只能证明技术比较条件，不会自动证明 Persistent Project Identity。怀疑用户已经切换/重开工程时，不能把旧 Verification Session 直接续到新工程。

```text
controlled_comparison=true
```

只表示技术可比性通过。

```text
closed_loop_complete=true
```

还要求调用方提供实际 Host Readback。

两者都不表示 After 在艺术上更好。

## MCP Self-Describing API

即使客户端没有额外导入 Skill，MCP Server 自己也会提供最低限度的正确使用方法。

当前分成三层：

```text
Server Instructions
  -> 初始化顺序和跨工具必须遵守的硬规则

Tool Descriptions
  -> tools/list 阶段就能看到每个工具的用途

MCP Resources
  -> 需要时再读取完整 Skill / Reference Markdown
```

不会把整个 Skill 原样塞进 Server Instructions。长篇知识仍然只维护一份：仓库/Release 中的 `skill/` 是 canonical source，MCP Resource 运行时直接读取同一份文件。

当前 Guide Resource：

```text
aianalyzer://guide/index
aianalyzer://guide/core
aianalyzer://guide/analyzer-mcp
aianalyzer://guide/parameters
aianalyzer://guide/performance-evidence
aianalyzer://guide/song-memory
aianalyzer://guide/section-structure
aianalyzer://guide/track-story
aianalyzer://guide/section-relationships
aianalyzer://guide/dynamics-evidence
aianalyzer://guide/mono-compatibility
aianalyzer://guide/masking-evidence
aianalyzer://guide/stereo-evidence
aianalyzer://guide/tonal-evidence
aianalyzer://guide/verification-evidence
```

调用方应该只读取当前任务需要的 Guide，不要一次把所有 Resources 塞进上下文。

支持 Skill 的客户端仍然可以直接导入外部 Skill；MCP Resources 只是让同一份长篇内容也能通过 MCP 协议按需读取，不是另一套重复文档。

CI 会强制所有 MCP Tool 和 Guide Resource 都有非空 Description，并验证固定的 Guide Resource Registry。

## MCP 工具

MCP **1.2 在当前 Stacked P7a 分支共 44 个工具**。

高层工具包括：

```text
audio_project_identity_status()
audio_project_status()
audio_set_analysis_profile(...)
audio_set_project_analysis_profile(...)
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
audio_begin_range_verification(...)
audio_complete_range_verification(...)
audio_range_verification_status(...)
```

新的 Agent/MCP Session 开始时，以及用户可能切换/重开工程时，优先检查 `audio_project_identity_status()`，再决定历史状态能不能继续使用。

不要机械调用全部 44 个工具。先高层理解，再按问题下钻。

## 用户安装

GitHub Release 按“没有编程经验也能安装”设计。

支持：

```text
Windows x64
macOS Apple Silicon arm64
```

每个平台一个最终 ZIP。用户 Release 不包含 MCP Python 源码、`requirements.txt`、venv、PyInstaller `_internal`、开发配置或嵌套 ZIP。

典型内容：

```text
AI Audio Analyzer.vst3
mcp/
  ai-audio-analyzer-mcp[.exe]   PyInstaller -F 单文件
skill/                          canonical Skill + MCP Resource 内容源
START-HERE.md
MCP-SETUP.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
平台安装文件
```

Windows：解压后运行 `Install.cmd`。

macOS Apple Silicon：解压后运行 `Install.command`。当前 macOS 包为 ad-hoc 签名，不是 Developer ID Notarization。

## 仓库 MCP 架构

唯一支持的源码/PyInstaller 入口：

```text
mcp/server.py
```

当前 Stacked P7a 分支版本关系：

```text
Product version             1.2.0
MCP version                 1.2
OSC analysis protocol       1.2
Analyzer control protocol   本机 revision 1
MCP tools                   44
Self-description schema     1
Guide resources             15
```

Runtime Modules：

```text
mcp/server.py
mcp/analyzer_core.py
mcp/self_description.py
mcp/project_tools.py
mcp/project_identity_tools.py
mcp/temporal_tools.py
mcp/masking_tools.py
mcp/stereo_tools.py
mcp/semantic_tools.py
mcp/performance_tools.py
mcp/control_tools.py
mcp/song_tools.py
mcp/section_tools.py
mcp/track_story_tools.py
mcp/section_relationship_tools.py
mcp/verification_tools.py
mcp/range_tools.py
mcp/range_verification_tools.py
mcp/dynamics_tools.py
mcp/mono_compatibility_tools.py
```

仓库 CI-only Regression：

```text
mcp/ci_regression.py
mcp/relationship_regression.py
mcp/range_verification_regression.py
mcp/dynamics_regression.py
mcp/mono_compatibility_regression.py
```

这些 Regression 文件不会进入面向普通用户的 Release Runtime。

## OSC Protocol

Analysis Address：`/aianalyzer/frame`。

OSC **1.2** 继续 Append-only。Track Story、Section Relationships、Transport-range Verification、Project Identity Disclosure、MCP Self-Description、P6a Retained Dynamics Distribution 和 P7a Derived Mono-fold Energy Evidence 都没有修改既有 `0..149` 索引。

Analyzer 自有 Analysis Profile Control 使用独立的本机 Loopback Control Protocol，Revision 1。

## Skill

LLM-facing Skill/reference 内容继续保持英文。完整 Skill/Reference Markdown 仍是长篇使用方法的 canonical source，同时通过 `aianalyzer://guide/*` MCP Resources 按需暴露；不要在 `server.py` 里再维护一份重复全文。

当前新增相关长篇 Reference：

```text
skills/ai-analyzer-flstudio/references/dynamics-evidence.md
skills/ai-analyzer-flstudio/references/mono-compatibility.md
```

## License

AI Audio Analyzer 使用 **MIT License**。详见 [LICENSE](LICENSE)。