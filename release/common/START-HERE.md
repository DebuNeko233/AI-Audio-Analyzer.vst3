# AI Audio Analyzer 1.2 — Start Here / 从这里开始

[English guide](INSTALL.en.md) | [中文教程](INSTALL.zh-CN.md) | [Agent / MCP setup](MCP-SETUP.md)

This package is designed for users who have never used Python, a terminal, or programming tools.

You only need to **unzip the downloaded Release once** and run the installer inside.

## Windows

1. Download the file ending in `Windows.zip`.
2. Right-click the ZIP and choose **Extract All**.
3. Open the extracted folder.
4. Double-click `Install.cmd`.
5. Approve the Windows permission prompt if it appears.
6. Wait until the installer says **Installation completed successfully**.
7. Restart FL Studio and rescan plugins if needed.
8. Open `MCP-SETUP.md` and add the generated MCP configuration to the Agent/Assistant that will use Analyzer.
9. Import the packaged `skill` folder for the same Agent/Assistant.

## macOS Apple Silicon

1. Download the file ending in `macOS.zip`.
2. Double-click the ZIP to extract it.
3. Open the extracted folder.
4. Double-click `Install.command`.
5. If macOS blocks it, right-click `Install.command` and choose **Open**.
6. Wait until the installer says **Installation completed successfully**.
7. Restart FL Studio and rescan plugins if needed.
8. Open `MCP-SETUP.md` and add the generated MCP configuration to the Agent/Assistant that will use Analyzer.
9. Import the packaged `skill` folder for the same Agent/Assistant.

Current macOS Release supports **Apple Silicon (arm64) only**. Intel Macs are not supported by the packaged Release.

## What is inside

```text
AI Audio Analyzer.vst3
mcp/                         standalone Analyzer MCP executable
skill/                       Cherry Studio / LLM Skill
Install.cmd / Install.ps1    Windows installer
Install.command / install.sh macOS installer
START-HERE.md
MCP-SETUP.md                 Agent/MCP setup + copyable JSON examples
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
```

There is **no MCP Python source code** in the user Release. There is also no Python environment, requirements file, PyInstaller `_internal` tree, developer source configuration example, or nested Release ZIP.

After installation, the installer tells you where to find the generated `cherry-studio-mcp.json`, `MCP-SETUP.md`, and installed Skill folder. The generated JSON contains the correct absolute MCP executable path for your computer.

AI Audio Analyzer 1.2 adds DAW-time Song Memory so the Agent can query audio evidence after the passage has already played. The current MCP can also build an explainable section map and group recurring sections into neutral A/B/C families. These families are **not automatic Verse/Chorus/Drop labels**; exact DAW/project markers remain authoritative when available.

Analysis Profiles (`Eco`, `Balanced`, `Mix`, `Full`) reduce unnecessary Analyzer work in projects with many plugin instances. They affect measurement computation only and do not change the audio. Current Analyzer MCP can change a live Analyzer's own Analysis Profile through its local control channel and receive an explicit acknowledgement. This control is intentionally limited to Analyzer measurement workload; all sound-changing DAW/plugin parameters still belong to the actual DAW-control MCP.

Current MCP 1.2 exposes **36 tools**.

---

# 中文快速说明

这个 Release 按“**完全没接触过编程也能安装**”设计。

你不需要安装 Python，不需要 pip，不需要打开命令行，也不需要理解 MCP 源码。

## Windows

1. 下载名称以 `Windows.zip` 结尾的文件；
2. 右键 ZIP → **全部解压缩**；
3. 打开解压后的文件夹；
4. 双击 `Install.cmd`；
5. Windows 弹出权限确认时点击允许；
6. 等待显示 **Installation completed successfully**；
7. 重启 FL Studio，需要时重新扫描插件；
8. 打开 `MCP-SETUP.md`，把安装器生成的 MCP 配置加入实际要使用 Analyzer 的 Agent/Assistant；
9. 把 `skill` 文件夹导入给同一个 Agent/Assistant。

## macOS Apple Silicon

1. 下载名称以 `macOS.zip` 结尾的文件；
2. 双击 ZIP 解压；
3. 打开解压后的文件夹；
4. 双击 `Install.command`；
5. 如果 macOS 阻止运行，右键 `Install.command` → **打开**；
6. 等待显示安装成功；
7. 重启 FL Studio，需要时重新扫描插件；
8. 打开 `MCP-SETUP.md`，把安装器生成的 MCP 配置加入实际要使用 Analyzer 的 Agent/Assistant；
9. 把 `skill` 文件夹导入给同一个 Agent/Assistant。

当前 macOS Release **只支持 Apple Silicon / arm64**，不提供 Intel Mac 包。

安装完成后，安装器会显示 `cherry-studio-mcp.json`、`MCP-SETUP.md` 和 Skill 文件夹的位置。生成的 JSON 已写好本机 MCP 可执行文件的真实绝对路径。

AI Audio Analyzer 1.2 支持 DAW 时间轴 Song Memory，LLM 即使晚几秒读取也能查询已经播放过的证据；同时 MCP 可以生成可解释的歌曲 Section Map，并把重复结构归为中性的 A/B/C 家族。**A/B/C 不等于自动识别的 Verse/Chorus/Drop**，如果 DAW/工程里有精确 Marker，应优先使用真实工程信息。

`Eco / Balanced / Mix / Full` Analysis Profile 只控制 Analyzer 的测量计算量，不会改变声音。当前 Analyzer MCP 可以通过本机控制通道修改 live Analyzer 自己的 Analysis Profile，并收到明确 ACK；这个写入范围只限 Analyzer 的测量负载，任何会改变声音或工程状态的 DAW/插件参数仍由真正的 DAW Control MCP 负责。

当前 MCP 1.2 共提供 **36 个工具**。
