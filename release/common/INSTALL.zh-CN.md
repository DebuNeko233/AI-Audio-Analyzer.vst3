# AI Audio Analyzer 0.9 — 中文安装教程

[English guide](INSTALL.en.md)

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
mcp/                         已打包好的 Analyzer 连接程序
skill/                       Cherry Studio Skill
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
对应平台的一键安装文件
```

用户 Release **不会夹带 MCP Python 源码**，也不会包含 `requirements.txt`、开发者配置示例、PyInstaller `_internal` 或“ZIP 里面再套一个 ZIP”。

## Windows 安装

1. 下载 `AI-Audio-Analyzer-v<版本>-Windows.zip`；
2. 右键 ZIP → **全部解压缩**；
3. 打开解压后的文件夹；
4. 双击 `Install.cmd`；
5. Windows 弹出管理员权限确认时点击允许；这个权限只用于把 VST3 复制到标准插件目录；
6. 等到窗口显示 **Installation completed successfully**；
7. 完全退出并重新打开 FL Studio；
8. 如果没有看到 AI Audio Analyzer，在 FL Studio Plugin Manager 里重新扫描插件。

安装器会把当前用户的 Analyzer 文件放到：

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

安装完成时，窗口会直接显示两个位置：

```text
cherry-studio-mcp.json
skill\
```

在 Cherry Studio 里添加 MCP 时使用第一个文件，导入 Skill 时选择第二个文件夹。

## macOS Apple Silicon 安装

1. 下载 `AI-Audio-Analyzer-v<版本>-macOS.zip`；
2. 双击 ZIP 解压；
3. 打开解压后的文件夹；
4. 双击 `Install.command`；
5. 如果 macOS 阻止运行，右键 `Install.command` → **打开**；
6. 等到显示安装成功；
7. 完全退出并重新打开 FL Studio，需要时重新扫描插件。

VST3 会安装到：

```text
~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3
```

Analyzer MCP 与 Skill 会安装到：

```text
~/Library/Application Support/AI Audio Analyzer/
```

不需要打开终端。要查看这个目录，可以在 Finder 里选择 **前往 → 前往文件夹…**，然后粘贴上面的路径。

当前 macOS 包是 ad-hoc 签名，**不是 Apple Developer ID Notarization**。安装器会自动处理当前 Release 所需的 Quarantine / 本地签名检查。

## Cherry Studio

安装完成后，安装器会告诉你：

1. `cherry-studio-mcp.json` 在哪里——用于添加 Analyzer MCP；
2. `skill` 文件夹在哪里——用于导入 AI Audio Analyzer Skill。

Skill 使用英文，以提高不同 LLM 对工具说明和参数含义的稳定理解。Skill 只教模型怎么调用 MCP 和理解测量数据，不预设具体混音风格、调性修正、和声改写或 Stereo 处理配方。

AI Audio Analyzer 0.9 新增 Chroma、Tonal-Center Candidate 和 Single-F0 Harmonic Alignment 等音频域语义证据。它们只用于测量和辅助理解，不会自动修改音符、和弦或调性。安装方式没有增加任何额外步骤。

## FL Studio 找不到插件

按顺序尝试：

1. 完全退出 FL Studio；
2. 重新打开；
3. 打开 Plugin Manager；
4. 重新扫描插件；
5. 查找 `AI Audio Analyzer`。

## Cherry Studio 连不上 Analyzer

重新运行一次安装器。安装器会自动检查 Analyzer 连接程序，并重新生成 `cherry-studio-mcp.json`。

另外确认电脑上没有同时运行第二个 AI Audio Analyzer MCP。

## macOS 提示无法打开安装器

不要直接双击，改为：

1. 右键 `Install.command`；
2. 选择 **打开**；
3. macOS 再次确认时继续选择 **打开**。

## 重要说明

Release ZIP 是已经做好的最终用户包。里面没有 MCP 源码，也不需要你自己安装任何编程依赖。
