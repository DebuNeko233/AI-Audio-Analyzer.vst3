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
mcp/                         PyInstaller -F 单文件 MCP Runtime
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
2. 右键选择 **全部解压**；
3. 打开解压后的目录；
4. 双击 `Install.cmd`；
5. 如果 Windows 弹出权限提示，允许安装；
6. 等待提示 **Installation completed successfully**；
7. 重新打开 FL Studio，需要时重新扫描 VST3；
8. 按 `MCP-SETUP.md` 把安装程序生成的 MCP 配置加入目标 Agent；
9. 可选：如果客户端支持 Skill 或不支持 MCP Resources，可以导入已安装的 `skill` 目录。

用户侧 Analyzer 文件安装到：

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

## macOS Apple Silicon

1. 下载 `AI-Audio-Analyzer-v<版本>-macOS.zip`；
2. 双击解压；
3. 打开解压后的目录；
4. 双击 `Install.command`；
5. 如果 macOS 阻止运行，右键 `Install.command` -> **打开**；
6. 等待安装成功；
7. 重新打开 FL Studio，需要时重新扫描插件；
8. 按 `MCP-SETUP.md` 把 Analyzer MCP 加入 Agent；
9. 可选：按客户端能力导入 `skill`。

VST3 安装位置：

```text
~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3
```

MCP / Skill：

```text
~/Library/Application Support/AI Audio Analyzer/
```

当前 macOS Release 是 Ad-hoc Signed，**不是 Apple Developer ID Notarized**。

## MCP 配置

安装程序会生成带真实绝对路径的 `cherry-studio-mcp.json`。优先使用生成的文件，不要手动猜路径。

AI Audio Analyzer MCP 1.2 当前暴露 **47 个工具**和 **16 个 Guide Resources**。

MCP 通过 Server Instructions、Tool Descriptions 和 `aianalyzer://guide/*` 自解释；已安装的 `skill/` 仍是长篇 Markdown 的唯一规范来源。

新 Session 或可能切换/重新打开工程后，先调用：

```text
audio_project_identity_status()
```

当前稳定 Project ID 仍未解决。Runtime UUID 是当前插件实例身份，不是持久 Project/Track ID。如果切换/重新打开工程后需要严格隔离历史状态，应重启 Analyzer MCP。

然后检查：

```text
audio_project_status()
audio_song_status()
```

## 整首歌与混音证据

高层工具包括：

```text
audio_song_overview()
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
```

缺失 Coverage 不是静音。A/B/C Section Family 是中性的重复结构标签，不自动代表 Verse/Chorus/Drop。

P6a 的 Dynamics Distribution 是描述性统计。LUFS-S P90-P10 不是标准 EBU LRA；Arbitrary-range Integrated LUFS 和 PLR 当前不可用。

P7a Direct Mono-fold Evidence 只支持 Recent-window。历史任意 Section 的 32-band Mono Evidence，以及 Mono-fold Sample Peak / True Peak 当前不可用。

## Reference Comparison

P8a 工具：

```text
audio_capture_reference(track, label="", seconds=10.0)
audio_list_references()
audio_compare_reference(reference_id, target, seconds=None)
```

P8a Reference 是冻结的结构化测量 Profile，不复制源音频。

当前范围：

```text
Recent Receive-time Window
仅当前 MCP Session
不持久化
不能声称 Whole-song Coverage
```

比较同时提供 Absolute `target - reference` 证据和明确的 RMS-level-normalized Spectral Shape 视图。Normalized View 不会真正施加 Gain，也不会改变声音。

与 Reference 不同只是上下文，不代表一定有问题，也不代表必须执行某个处理。P8a 不输出自动 EQ / Master Match 或质量分数。

## 真实 DAW 修改与验证

Analyzer MCP 只允许修改自己的 `Analysis Profile` 测量设置。

真实 EQ、Compression、Gain、Pan、Routing、Synth、Automation 和 Project 修改都由外部 DAW-control MCP 负责。

已知需要验证的片段时，优先使用：

```text
audio_begin_range_verification(...)
-> 外部修改 + 真实 Host Readback
-> 重播 effective_range
audio_complete_range_verification(...)
```

`controlled_comparison=true` 只表示技术上可比较；`closed_loop_complete=true` 还要求真实 Host Readback。两者都不表示 After 在艺术上一定更好。

## 排错

如果 Agent 看不到 Analyzer 工具：

1. 确认安装程序成功完成；
2. 确认生成 JSON 里的 `command` 指向已安装的 MCP 可执行文件；
3. 确认当前 Agent 已启用该 MCP；
4. 修改配置后刷新/重启 MCP 客户端；
5. 确认没有另一个 Analyzer MCP 进程占用 `127.0.0.1:9855`。

普通用户 Release 必须运行已安装的单文件 MCP Runtime，不要运行仓库里的 Python 源码。