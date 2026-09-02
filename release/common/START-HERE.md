# AI Audio Analyzer — Start Here / 从这里开始

[English manual](INSTALL.en.md) | [中文安装教程](INSTALL.zh-CN.md)

This Release package contains:

```text
AI Audio Analyzer.vst3
mcp/
├─ runtime/     standalone PyInstaller MCP runtime
└─ source/      Python source fallback for developers
skill/
Install script(s)
INSTALL.en.md
INSTALL.zh-CN.md
```

**Normal installation does not require Python, pip, a virtual environment, or PyPI access.**

## Fastest path / 最快安装

### Windows

Double-click:

```text
Install.cmd
```

The installer will request Administrator permission only for the VST3 copy, install the standalone MCP runtime for the current user, run its built-in self-test, generate `cherry-studio-mcp.json`, and copy the Cherry Studio Skill.

### macOS

Current macOS Release packages support **Apple Silicon (arm64) only**. Intel/x86_64 Macs are not included.

Double-click:

```text
Install.command
```

If macOS blocks the downloaded script itself, right-click it and choose **Open**, or run:

```bash
bash ./install.sh
```

The installer installs the arm64 VST3 and arm64 standalone MCP runtime, removes quarantine metadata, validates the packaged MCP runtime, and generates `cherry-studio-mcp.json`.

> Current macOS builds are ad-hoc signed and are not Apple Developer ID notarized. The installer handles the current quarantine/Gatekeeper development-distribution issue; see the full manual for details.

---

## 中文快速说明

Windows 用户直接双击 `Install.cmd`。macOS Release **仅支持 Apple Silicon（arm64）**，Intel/x86_64 Mac 不再提供构建包；Apple Silicon 用户直接双击 `Install.command`。

**普通用户不再需要自己安装 Python、pip、MCP SDK，也不依赖 PyPI / 清华 / 阿里云镜像。** Release 已经把 Python Runtime 和 MCP 依赖打包进 `mcp/runtime/`。

如果 macOS 连 `Install.command` 本身都阻止打开，可以**右键 → 打开**，或者执行：

```bash
bash ./install.sh
```

如果自动安装失败，或你希望完全手动控制安装，请阅读：

- `INSTALL.zh-CN.md`：完整中文教程，包括 Gatekeeper、手动 standalone 安装，以及 Python/PyPI 源码 fallback；
- `INSTALL.en.md`：English manual.

配套 FL Studio 控制 MCP：

https://github.com/rosasynthesiz/flstudio-mcp
