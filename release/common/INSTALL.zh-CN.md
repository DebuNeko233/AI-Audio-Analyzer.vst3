# AI Audio Analyzer 1.1 — 中文安装教程

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
mcp/                         已打包好的 Analyzer MCP 程序
skill/                       Cherry Studio Skill
START-HERE.md
MCP-SETUP.md                 Agent/MCP 配置说明 + JSON 示例
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
对应平台的一键安装文件
```

用户 Release **不会夹带 MCP Python 源码**、仓库回归测试代码、`requirements.txt`、开发源码配置示例、PyInstaller `_internal`，也不会出现“ZIP 里面再套一个 ZIP”。

## Windows 安装

1. 下载 `AI-Audio-Analyzer-v<版本>-Windows.zip`；
2. 右键 ZIP → **全部解压缩**；
3. 打开解压后的文件夹；
4. 双击 `Install.cmd`；
5. Windows 弹出管理员权限确认时点击允许；这个权限只用于把 VST3 复制到标准插件目录；
6. 等到窗口显示 **Installation completed successfully**；
7. 完全退出并重新打开 FL Studio；
8. 如果没有看到 AI Audio Analyzer，在 FL Studio Plugin Manager 里重新扫描插件；
9. 按照 `MCP-SETUP.md`，把生成的 MCP 配置加入实际要使用 Analyzer 的 Agent/Assistant。

安装器会把当前用户的 Analyzer 文件放到：

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

安装完成时会直接显示 `cherry-studio-mcp.json`、`MCP-SETUP.md` 和 `skill` 文件夹的位置。

## macOS Apple Silicon 安装

1. 下载 `AI-Audio-Analyzer-v<版本>-macOS.zip`；
2. 双击 ZIP 解压；
3. 打开解压后的文件夹；
4. 双击 `Install.command`；
5. 如果 macOS 阻止运行，右键 `Install.command` → **打开**；
6. 等到显示安装成功；
7. 完全退出并重新打开 FL Studio，需要时重新扫描插件；
8. 按照 `MCP-SETUP.md`，把生成的 MCP 配置加入实际要使用 Analyzer 的 Agent/Assistant。

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

完整的新手配置流程和 Windows/macOS JSON 示例都在 `MCP-SETUP.md`。最短流程是：

1. 打开 Cherry Studio 或其他支持 MCP 的客户端里的 MCP Server 设置；
2. 导入安装器生成的 `cherry-studio-mcp.json`，或手动建立相同的 `mcpServers.ai-audio-analyzer` 配置；
3. 把这个 MCP Server 启用/分配给实际要使用 Analyzer 的 Agent/Assistant；
4. 把安装好的 `skill` 文件夹导入给同一个 Agent；
5. 刷新或重启 Agent 会话，确认它能看到 `audio_project_status()` 等 Analyzer 工具。

优先使用安装器生成的 JSON，而不是自己手输路径，因为生成文件已经包含当前电脑上的正确安装路径。

## Cherry Studio Skill

Skill 使用英文，以提高不同 LLM 对工具说明和参数含义的稳定理解。它会教模型发现 Analyzer、按任务选择最低需要的 Analysis Profile、理解测量数据，以及正确运行 Before/After Verification；不会预设具体混音、母带、和声或 Stereo 处理风格。

## Analysis Profile

AI Audio Analyzer 向宿主公开以下测量 Profile：

```text
Eco
Balanced
Mix
Full
```

它们只改变 **Analyzer 自己的测量计算量**，不会处理或改变声音。

`Full` 是兼容默认值。AI 工作流可以在需要时通过真实 DAW-control MCP 临时切换到更轻或更深的 Profile，回读宿主设置，再由 Analyzer 状态确认是否生效。普通用户安装时不需要配置这些内容。

## 闭环验证

Analyzer MCP 可以保存修改前的 Before 测量，在外部 Control MCP 修改并回读真实宿主状态后，再测量 After，并检查两次测量是否满足透明的技术可比条件。

这不代表 Analyzer 自己控制 FL Studio；而且“技术上可比”也不代表修改后的声音在艺术上更好。

普通用户不需要手动配置这套流程，LLM-facing Skill 会告诉 Agent 如何正确调用。

## FL Studio 找不到插件

1. 完全退出 FL Studio；
2. 重新打开；
3. 打开 Plugin Manager；
4. 重新扫描插件；
5. 查找 `AI Audio Analyzer`。

## Agent 看不到 Analyzer MCP 工具

1. 重新运行安装器，让它检查独立 MCP 程序并重新生成 `cherry-studio-mcp.json`；
2. 确认生成的 MCP Server 已经启用给当前 Agent/Assistant；
3. 修改 MCP 配置后刷新或重启客户端；
4. 按 `MCP-SETUP.md` 对照 JSON 示例检查配置；
5. 确认电脑上没有同时运行第二个 AI Audio Analyzer MCP。

## macOS 提示无法打开安装器

右键 `Install.command` → **打开**。如果 macOS 再次确认，继续选择 **打开**。

## 重要说明

Release ZIP 是已经做好的最终用户包。里面没有 MCP 源码，也不需要你自己安装任何编程依赖。
