# AI Audio Analyzer 1.2 — 中文安装教程

[English guide](INSTALL.en.md) | [Agent / MCP 配置](MCP-SETUP.md)

这个 Release 按“**完全没接触过编程也能安装**”设计。正常安装不需要 Python、pip、venv、源码、包管理器，也不需要自己输入命令。

支持：

```text
Windows x64
macOS Apple Silicon arm64
```

不提供 Intel / x86_64 macOS 包。

## 包内内容

```text
AI Audio Analyzer.vst3
mcp/                         已打包好的单文件 MCP Runtime
skill/                       canonical 长篇 Guide + 可选客户端 Skill
START-HERE.md
MCP-SETUP.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
对应平台安装文件
```

用户 Release 不包含 MCP Python 源码、仓库回归测试代码、`requirements.txt`、开发配置、PyInstaller `_internal` 或嵌套 ZIP。

## Windows

1. 下载 `AI-Audio-Analyzer-v<版本>-Windows.zip`；
2. 右键 → **全部解压缩**；
3. 打开解压后的文件夹；
4. 双击 `Install.cmd`；
5. Windows 弹出管理员权限确认时允许；该权限用于把 VST3 复制到标准插件目录；
6. 等待显示 **Installation completed successfully**；
7. 重启 FL Studio，需要时重新扫描 VST3；
8. 按 `MCP-SETUP.md` 把生成的 MCP 配置启用给目标 Agent；
9. 可选：如果客户端支持 Skill，或者不支持 MCP Resources，再导入安装后的 `skill` 文件夹。

用户侧 Analyzer 文件位于：

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

## macOS Apple Silicon

1. 下载 `AI-Audio-Analyzer-v<版本>-macOS.zip`；
2. 双击 ZIP 解压；
3. 打开文件夹并双击 `Install.command`；
4. 如果 macOS 阻止运行，右键 `Install.command` → **打开**；
5. 等待安装成功；
6. 重启 FL Studio，需要时重新扫描插件；
7. 按 `MCP-SETUP.md` 配置 MCP；
8. 可选：按客户端能力决定是否导入同一个 `skill` 文件夹。

VST3 安装到：

```text
~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3
```

MCP / Skill 安装到：

```text
~/Library/Application Support/AI Audio Analyzer/
```

当前 macOS 包是 ad-hoc 签名，**不是 Apple Developer ID Notarization**。

## 把 Analyzer MCP 加入 Agent

安装器会生成 `cherry-studio-mcp.json`，里面已经写好单文件 MCP Runtime 的真实绝对路径。

优先直接使用这个文件，不要手动猜路径。完整 JSON 示例见 `MCP-SETUP.md`。

当前 AI Audio Analyzer MCP 1.2 在 Stacked P7a 分支共 **44 个工具**。

## MCP Self-Describing API

即使客户端没有手动导入 packaged Skill，Analyzer MCP 仍然可以让调用方理解基本使用方法。

它会通过：

```text
Server instructions
44 个 Tool description
15 个 MCP Resources: aianalyzer://guide/*
```

暴露基本调用顺序、工具用途和关键语义限制。

`skill/` 仍然会跟随 Release 安装，因为其中的 `SKILL.md` 与 `references/*.md` 是 MCP Resources 的 canonical 长篇 Markdown 内容源，同时也能被支持 Skill 的客户端直接导入。

如果客户端支持 MCP Resources，可以先读取：

```text
aianalyzer://guide/index
```

然后只读取当前任务需要的 Guide，不要机械加载全部内容。P6a Dynamics 的详细 Guide 是：

```text
aianalyzer://guide/dynamics-evidence
```

P7a Mono-fold 的详细 Guide 是：

```text
aianalyzer://guide/mono-compatibility
```

如果客户端不支持 MCP Resources，则建议把安装后的 `skill` 文件夹导入给同一个 Agent，以获得同一份完整长篇专业说明。

如果物理 `skill` 目录缺失，Server instructions 和 Tool descriptions 仍提供最低限度自解释能力，但详细 Guide Resources 不可用。

新会话开始时，或者用户可能切换/重新打开了工程时，建议第一个调用：

```text
audio_project_identity_status()
```

当前身份范围：

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id scope                        live_plugin_instance
same-project reopen UUID stable         false
cross-project retained-state isolation  not guaranteed
```

Analyzer Runtime UUID 不是永久 Project/Track ID。即使重新打开的是**同一个 FL Studio 工程**，Runtime UUID 也会重新生成，所以“出现新 UUID”不能证明“工程已经切换”。

如果 Analyzer MCP 在切换/重开工程时一直运行，上一个工程的 Song Memory、Section Map、Snapshot、Relationship、Verification 等状态可能仍留在 RAM，目前还没有 Stable Project ID 自动分区。在后续接入可信 Project Identity 之前，如果要求严格隔离，切换或重新打开工程后应重启 Analyzer MCP。

然后再检查当前 Session：

```text
audio_project_status()
```

## 整曲与 Section 工作流

高层工具包括：

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
```

Song Memory 保存有界的 1 秒 DAW 时间轴证据。重新播放、Seek、Loop 跳回会建立新的实例局部 Playback Epoch。Song Memory 当前属于 MCP Session State，还没有按 Stable Project ID 自动隔离。

A/B/C 是中性的重复结构家族，不是自动 Verse/Chorus/Drop。Track Story 不会自动判断 Bass/Vocal/Drums，也不会自动要求处理。Relationship 的 `shortlist_priority` 只是检查优先级，不是 Masking/Mix Problem 概率或质量分数。

详细 Masking/Stereo/Temporal Pair 工具仍是 Recent-window。P7a Mono Compatibility 同样是 Recent-window，不能把它描述成任意 Historical/Section 32-band Evidence。

## Coverage-aware Dynamics Distribution

使用：

```text
audio_dynamics_distribution(...)
```

可以分析 Selected Retained Transport Pass、显式 DAW-time Range 或 Cached Section。P6a 对 1 秒 Retained Bin 设置最小 Coverage Floor，并按 Accepted Bin 的 Covered Seconds 加权。

当前输出 RMS、LUFS-S、Crest、Observed per-bin Sample Peak Maxima、Observed per-bin True Peak Maxima 的描述性分布。Missing Bin 永远保持 Missing，不会补成 Silence 或 0。

重要边界：

- `lufs_s_interpercentile_range_lu` 只是 LUFS-S 的 P90-P10 Spread，不是标准 EBU Loudness Range；
- P6a 不实现标准 EBU LRA；
- Retained `lufs_i_latest` 是 Pass-cumulative，因此不能当作 Arbitrary-range Integrated LUFS；
- 没有 Scope-compatible Integrated Loudness 时不输出 Arbitrary-range PLR；
- Section-to-section Delta 只是描述证据，不是 Quality Score 或处理建议。

## Direct Mono-fold Compatibility

使用：

```text
audio_mono_compatibility(track, seconds=5.0)
```

P7a 直接复用 Analyzer 已有的 Mid/Side Evidence。当前 Worker 已定义：

```text
M = 0.5 * (L + R)
S = 0.5 * (L - R)
(L_power + R_power)/2 = M_power + S_power
```

因此现有 Mid RMS 就是普通 `(L+R)/2` Mono Fold 的 RMS，现有 32 个 Mid/Side Band-center Power 也能提供直接的 Fold-down Energy Comparison，不需要增加新的 Realtime DSP 或 OSC 字段。

重要边界：

- 当前只分析 Recent Receive-time Window，不是任意 Historical/Section 32-band 分析；
- `inspection_priority` 只是 Energy-aware Inspection Shortlist，不是 Quality Score、Audibility Probability、Pass/Fail 或处理建议；
- Correlation、Side/Mid、Negative-cross 与 Direct Mono-fold Energy 必须继续作为独立证据；
- `floor_censored=true` 表示 Mid 已触及 Analyzer `-120 dB` 测量地板，低于该地板的抵消深度不能精确断言；
- Mid+Side 都不可测的 Band-center 继续返回 unavailable，而不是制造极端抵消；
- P7a 不直接测量 Mono-fold Sample Peak；
- P7a 不直接测量 Mono-fold True Peak；
- 不能从 Stereo Peak、True Peak、RMS、Correlation 或 Side/Mid 推算这两个 Mono Peak 值；
- Direct Peak / True-Peak Fold-down 属于可选 P7b；
- MCP 不内置 `all lows must be mono`、`correlation < 0 = bad`、`mono_fold_delta < X = fail` 这类固定规则。

## Same-range Before/After 验证

如果要验证一个已知歌曲范围上的真实 DAW/插件修改，优先使用：

```text
audio_begin_range_verification(...)
-> 外部 DAW-control MCP 执行真实修改
-> 外部 DAW-control MCP 回读实际宿主状态
-> 重放返回的 effective_range
audio_complete_range_verification(...)
```

Same-range 规则：

- 小数请求会明确归一到 1 秒 Retained Song Memory Bin；
- 每个 Analyzer 独立按 Coverage 优先、Recency 次优选择自己的本地 Epoch；
- 跨轨不要求 Epoch 数字相同；
- After 必须来自冻结 Baseline Receive-time Fence 后首次观测到的干净 Pass；
- 修改前 Retained Memory 不能偷偷当成 After；
- 历史 Feature 可比性看所选 Pass 真正保留的字段，不拿当前 Live Profile 冒充过去状态；
- 如果选中 After 的 Dropped-block Evidence 更高，则不通过 Controlled Comparison；
- 不会用 Pass-cumulative `lufs_i_latest` 伪造 Arbitrary-range LUFS-I。

`controlled_comparison=true` 只表示技术可比性通过；`closed_loop_complete=true` 还要求调用方提供实际 Host Readback。两者都不表示 After 在艺术上更好，也不能证明 Persistent Project Identity。

如果不方便指定明确的 Retained DAW-time Range，旧 Recent-window Verification 仍可使用：

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

怀疑已经切换/重开工程时，两种 Verification 都不能直接跨工程续用，除非有可信外部 Project Identity 或已经建立干净的新 MCP Session。

## Analysis Profile

```text
0 Eco
1 Balanced
2 Mix
3 Full
```

Profile 只改变 Analyzer 测量计算量，不改变声音。

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

Analyzer 自有 Profile 工具：

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

必须区分：

```text
control_acknowledged  目标 VST3 已接受/应用 Profile 请求
telemetry_confirmed   新测量帧已经报告目标 Profile
```

这是 Analyzer MCP 唯一允许的写入。所有真正改变声音/工程的参数与实际 Host Readback 仍由 DAW-control MCP 负责。

## 推荐第一次使用

```text
连接 Analyzer MCP
-> 用 Server instructions / Tool descriptions 作为最低使用契约
-> 需要详细语义时，若客户端支持 Resources，按需读取对应 aianalyzer://guide/*
-> audio_project_identity_status()
-> 若工程已切换/重开且要求严格隔离，先重启 Analyzer MCP
-> audio_project_status()
-> 必要时通过 Identify 绑定未映射实例
-> 整曲任务调用 audio_song_status()
-> 采集足够目标 Pass
-> audio_section_map()
-> 根据问题调用 Track Story / Section Profile / Section Relationships
-> 需要 Retained Dynamics 时调用 audio_dynamics_distribution()
-> 需要当前 Direct Mono Translation Evidence 时调用 audio_mono_compatibility()
-> 已知 Before/After 歌曲范围时使用 Transport-range Verification
-> 只有真正需要时再调用 Temporal / Masking / Stereo / Tonal 深度证据
```

## 常见问题

安装后看不到插件：完全重启 FL Studio、重新扫描 VST3，并确认插件已经复制到标准目录。

Agent 看不到 MCP 工具：确认安装成功，优先使用生成的 `cherry-studio-mcp.json`，确认 MCP Server 已启用给目标 Agent，并刷新/重启 Agent 会话。是否导入 Skill 不影响 MCP Tool 本身是否出现。

Analyzer Profile Control 超时：确认 VST3 和 MCP Runtime 来自同一套当前 Release。没有 ACK 就不能当成成功写入。

MCP 配置细节见 `MCP-SETUP.md`。