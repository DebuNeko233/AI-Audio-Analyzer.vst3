# AI Audio Analyzer 0.6 — Start Here / 从这里开始

[English manual](INSTALL.en.md) | [中文安装教程](INSTALL.zh-CN.md)

This Release package contains / 懒人包包含：

```text
AI Audio Analyzer.vst3
mcp/
├─ runtime/     standalone PyInstaller MCP 0.6
└─ source/      Python source fallback
skill/
platform install script(s)
INSTALL.en.md
INSTALL.zh-CN.md
```

**Normal installation does not require Python, pip, a virtual environment, or PyPI access.**

**普通用户不需要自己安装 Python、pip、venv、MCP SDK，也不依赖 PyPI。**

## Windows x64

Double-click / 双击：

```text
Install.cmd
```

The installer copies the VST3, installs the standalone MCP for the current user, runs the MCP self-test, copies the Skill, and generates `cherry-studio-mcp.json`.

安装器会复制 VST3、安装 Standalone MCP、执行 Self-test、复制 Skill，并生成 Cherry Studio MCP 配置。

## macOS Apple Silicon arm64

Current macOS Releases support **Apple Silicon / arm64 only**. Intel/x86_64 Macs are not included.

当前 macOS Release **仅支持 Apple Silicon / arm64**，不提供 Intel/x86_64 包。

Double-click / 双击：

```text
Install.command
```

If macOS blocks the downloaded script itself / 如果系统拦截脚本：

```text
Right-click Install.command → Open
右键 Install.command → 打开
```

or / 或：

```bash
bash ./install.sh
```

The installer installs the arm64 VST3 and standalone MCP, removes quarantine metadata where possible, verifies/repairs the local ad-hoc VST3 signature, runs MCP self-test, copies the Skill and generates `cherry-studio-mcp.json`.

> Current macOS builds are ad-hoc signed and are **not Apple Developer ID notarized**.

## MCP 0.6

The packaged executable uses MCP entry point `server_v06.py` internally and includes the V0.4 mapping tools, V0.5 project/Snapshot tools and V0.6 temporal tools. The user still launches only the packaged `ai-audio-analyzer-mcp` executable; no Python command is required.

## After installation / 安装后

1. Fully quit and restart FL Studio, then rescan VST3 plugins if necessary.
2. Add the generated `cherry-studio-mcp.json` configuration to Cherry Studio.
3. Import the installed `skill/` folder into Cherry Studio.
4. If DAW control is required, also install: https://github.com/rosasynthesiz/flstudio-mcp

如果自动安装失败，或需要手动安装 / Python 源码 fallback，请阅读完整中英文教程。
