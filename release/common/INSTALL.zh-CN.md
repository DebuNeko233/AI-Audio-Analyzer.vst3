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
skill/                       Cherry Studio / LLM Skill
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
9. 把安装后的 `skill` 文件夹导入给同一个 Agent。

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
7. 按 `MCP-SETUP.md` 配置 MCP，并导入同一个 `skill` 文件夹。

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

建议第一个 Agent 调用：

```text
audio_project_status()
```

当前 AI Audio Analyzer MCP 1.2 共 **41 个工具**。

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
```

Song Memory 保存有界的 1 秒 DAW 时间轴证据。重新播放、Seek、Loop 跳回会建立新的实例局部 Playback Epoch。

A/B/C 是中性的重复结构家族，不是自动 Verse/Chorus/Drop。Track Story 不会自动判断 Bass/Vocal/Drums，也不会自动要求处理。Relationship 的 `shortlist_priority` 只是检查优先级，不是 Masking/Mix Problem 概率或质量分数。

详细 Masking/Stereo/Temporal Pair 工具仍是 Recent-window。

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

`controlled_comparison=true` 只表示技术可比性通过；`closed_loop_complete=true` 还要求调用方提供实际 Host Readback。两者都不表示 After 在艺术上更好。

如果不方便指定明确的 Retained DAW-time Range，旧 Recent-window Verification 仍可使用：

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

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
audio_project_status()
-> 必要时通过 Identify 绑定未映射实例
-> 整曲任务调用 audio_song_status()
-> 采集足够目标 Pass
-> audio_section_map()
-> 根据问题调用 Track Story / Section Profile / Section Relationships
-> 已知 Before/After 歌曲范围时使用 Transport-range Verification
-> 只有真正需要时再调用 Temporal / Masking / Stereo / Tonal 深度证据
```

## 常见问题

安装后看不到插件：完全重启 FL Studio、重新扫描 VST3，并确认插件已经复制到标准目录。

Agent 看不到 MCP 工具：确认安装成功，优先使用生成的 `cherry-studio-mcp.json`，确认 MCP Server 已启用给同一个 Agent，并刷新/重启 Agent 会话。

Analyzer Profile Control 超时：确认 VST3 和 MCP Runtime 来自同一套当前 Release。没有 ACK 就不能当成成功写入。

MCP 配置细节见 `MCP-SETUP.md`。
