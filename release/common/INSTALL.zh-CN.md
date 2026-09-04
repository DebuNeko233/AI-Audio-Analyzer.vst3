# AI Audio Analyzer 1.2 — 中文安装教程

[English guide](INSTALL.en.md) | [Agent / MCP 配置](MCP-SETUP.md)

这个 Release 的原则就是：**给完全没接触过编程的人使用**。

正常安装不需要 Python、pip、venv、源码、包管理器，也不需要自己输入命令。

当前提供：

```text
Windows x64
macOS Apple Silicon arm64
```

不提供 Intel / x86_64 macOS 包。

## 包内有什么

```text
AI Audio Analyzer.vst3
mcp/                         已打包好的 Analyzer MCP 单文件程序
skill/                       Cherry Studio / LLM Skill
START-HERE.md
MCP-SETUP.md                 Agent/MCP 配置说明 + JSON 示例
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
对应平台的一键安装文件
```

用户 Release **不会夹带 MCP Python 源码**、仓库回归测试代码、`requirements.txt`、开发源码配置示例、PyInstaller `_internal`，也不会出现“ZIP 里面再套 ZIP”。

## Windows 安装

1. 下载 `AI-Audio-Analyzer-v<版本>-Windows.zip`；
2. 右键 ZIP → **全部解压缩**；
3. 打开解压后的文件夹；
4. 双击 `Install.cmd`；
5. Windows 弹出管理员权限确认时点击允许；这个权限只用于把 VST3 复制到标准插件目录；
6. 等到窗口显示 **Installation completed successfully**；
7. 完全退出并重新打开 FL Studio；
8. 如果没有看到 AI Audio Analyzer，在 FL Studio Plugin Manager 里重新扫描插件；
9. 按照 `MCP-SETUP.md`，把生成的 MCP 配置加入实际要使用 Analyzer 的 Agent/Assistant；
10. 把安装后的 `skill` 文件夹导入给同一个 Agent/Assistant。

安装器会把当前用户的 Analyzer 文件放到：

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

安装完成时会显示 `cherry-studio-mcp.json`、`MCP-SETUP.md` 和 `skill` 文件夹的位置。

## macOS Apple Silicon 安装

1. 下载 `AI-Audio-Analyzer-v<版本>-macOS.zip`；
2. 双击 ZIP 解压；
3. 打开解压后的文件夹；
4. 双击 `Install.command`；
5. 如果 macOS 阻止运行，右键 `Install.command` → **打开**；
6. 等到显示安装成功；
7. 完全退出并重新打开 FL Studio，需要时重新扫描插件；
8. 按照 `MCP-SETUP.md`，把生成的 MCP 配置加入实际要使用 Analyzer 的 Agent/Assistant；
9. 把安装后的 `skill` 文件夹导入给同一个 Agent/Assistant。

VST3 会安装到：

```text
~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3
```

Analyzer MCP 与 Skill 会安装到：

```text
~/Library/Application Support/AI Audio Analyzer/
```

当前 macOS 包是 ad-hoc 签名，**不是 Apple Developer ID Notarization**。

## 把 Analyzer MCP 加入 Agent

安装器会自动生成 `cherry-studio-mcp.json`，其中已经写好了本机安装后 MCP 可执行文件的真实绝对路径。

完整流程和 Windows/macOS JSON 示例在 `MCP-SETUP.md`。最短流程：

1. 打开 Cherry Studio 或其他支持 MCP 客户端里的 MCP Server 设置；
2. 导入安装器生成的 `cherry-studio-mcp.json`，或手动建立相同的 `mcpServers.ai-audio-analyzer` 配置；
3. 把该 MCP Server 启用/分配给实际要使用 Analyzer 的 Agent/Assistant；
4. 把安装好的 `skill` 文件夹导入给同一个 Agent；
5. 刷新或重启 Agent 会话，确认能看到 `audio_project_status()` 等 Analyzer 工具。

优先使用安装器生成的 JSON，而不是自己手输路径。

## AI Audio Analyzer 1.2 的整曲能力

1.2 的重点不是让 LLM 强行进入实时音频链路，而是让 Analyzer 持续测量、LLM 稍后读取。

整曲高层工具：

```text
audio_song_status()
audio_song_overview()
audio_song_timeline(...)
```

MCP 会保存有界的 1 秒 DAW 时间轴 Song Memory。重新播放、Seek、Loop 跳回会建立新的 Continuous Playback Epoch，避免把无关时间位置混在一起。

现在还提供可解释歌曲结构、Track Story 和 Section-aware Relationships 工具：

```text
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
```

`audio_section_map()` 可以发现 Section 级变化点，并把重复结构归为中性的 A/B/C/... 家族；`audio_section_profile()` 用于查看一个 Section 内多条 Analyzer 轨道；`audio_track_story()` 则用于查看一个 Analyzer 实例在整首歌各个 Section 中怎样变化，包括 Coverage-aware 活动度、Energy、Spectrum、Stereo、Temporal、Tonal 证据、相邻 Section Delta、同 Family 各维度变化和相对极值。

`audio_section_relationships()` 会有界筛出“哪些 Track Pair 在某个 Section/Family 值得继续检查”，并保留各自 Coverage、Activity、RMS、Width、Transport Epoch 和方向性差值。它的 `shortlist_priority` **只是检查优先级启发式**，不是 Masking 概率、Mix Problem 概率、质量分数，也不等于必须做 EQ/Sidechain。当前深度 Pair 工具仍主要分析最近窗口，因此要把它们作为历史 Section 的深度证据时，应先定位/重放对应 Section。

这些 A/B/C **不是自动识别的 Verse / Chorus / Drop 名称**。Track Story 也不会根据测量自动把轨道判定成 Bass/Vocal/Drums，更不会自动产生 EQ、Compression 或 Stereo 操作。如果 DAW 中有 Marker、Playlist Label、Arrangement Metadata、Mixer Track Name 或用户明确提供了结构，应优先使用这些精确信息。

MCP 1.2 当前共有 **38 个工具**。

## Analysis Profile

```text
0 Eco
1 Balanced
2 Mix
3 Full
```

Profile 只影响 Analyzer 的测量计算量，不处理声音，也不是音质模式。

```text
Eco       Core
Balanced  Core + Loudness + Spectrum + Stereo
Mix       Balanced + Temporal
Full      Mix + Semantic
```

`Full` 是兼容旧工程的默认值。

当前 Analyzer MCP 可以直接控制 live VST3 自己的 Analysis Profile：

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

这条控制链路只走本机 loopback，并按 live Analyzer 的 Runtime UUID 定位实例；真正的 `analysis_profile` 宿主参数会在非实时 Audio Callback 的路径上应用，并返回明确 ACK。

必须区分：

```text
control_acknowledged  目标 VST3 已接受/应用 Profile 请求
telemetry_confirmed   新的测量帧也已经回报目标 Profile
```

即使 DAW 停止播放，也可以收到控制 ACK；而新的 Telemetry 通常需要宿主继续进行音频处理。

这也是 Analyzer MCP **唯一允许的写入能力**。它不能修改 EQ、Compression、Gain、Pan、Routing、Synth、Automation、Arrangement 或其他 DAW/插件状态。所有会改变声音或工程状态的写入，以及真实宿主回读，仍然由真正的 DAW Control MCP 负责。

## 推荐第一次使用流程

```text
audio_project_status()
→ 需要时通过 Identify 绑定未映射的 Analyzer
→ 整曲任务调用 audio_song_status()
→ 播放/采集足够的目标 Pass
→ audio_section_map() 获取结构上下文
→ 对需要看“跨 Section 变化”的轨调用 audio_track_story()
→ 对需要看“一个 Section 内多轨状态”的位置调用 audio_section_profile()
→ 需要判断“哪些 Pair 在哪些 Section/Family 值得深挖”时调用 audio_section_relationships()
→ 把最近窗口 Pair 工具用于历史 Section 前先定位/重放该 Section
→ 再按问题选择 Temporal / Masking / Stereo / Tonal 工具
```

如果所需证据家族当前被关闭，应只切换到满足任务要求的最低 Analysis Profile，而不是把所有 Analyzer 都设为 Full。

Analyzer 返回的是测量证据，不会自动决定 EQ、Compression、Sidechain、Stereo Processing、母带响度目标、歌曲 Key、轨道角色、Verse/Chorus/Drop 名称，也不会把 Relationship Shortlist 自动等同为“已确认的混音问题”。

## 常见问题

如果安装后看不到插件：

- 完全重启 FL Studio；
- 在 Plugin Manager 重新扫描 VST3；
- 确认插件已复制到平台标准 VST3 目录。

如果 Agent 看不到 Analyzer MCP 工具：

- 确认安装器执行成功；
- 优先使用生成的 `cherry-studio-mcp.json`，不要自己猜 MCP 路径；
- 确认 MCP Server 已启用给同一个导入 Skill 的 Agent；
- 刷新/重启 Agent 会话。

如果 Analyzer Profile Control 工具超时：

- 确认安装的 VST3 与 MCP Runtime 来自同一套当前 Release；
- 旧版 VST3 没有本机 Profile Control Receiver；
- 没有 ACK 时绝不能把请求当作成功写入。

如果 macOS 阻止安装器，右键 `Install.command` → **打开**。当前包未做 Apple Notarization。

MCP 配置细节请看 `MCP-SETUP.md`。
