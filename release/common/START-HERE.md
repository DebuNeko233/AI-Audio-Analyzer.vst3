# AI Audio Analyzer — Start Here / 从这里开始

[English manual](INSTALL.en.md) | [中文安装教程](INSTALL.zh-CN.md)

This release package contains:

```text
AI Audio Analyzer.vst3
mcp/
skill/
Install script(s)
INSTALL.en.md
INSTALL.zh-CN.md
```

## Fastest path / 最快安装

### Windows

Double-click:

```text
Install.cmd
```

The installer will:

1. request Administrator permission only when installing the VST3;
2. install `AI Audio Analyzer.vst3` to the standard VST3 directory;
3. find a usable Python 3.10+ installation, preferring Python 3.12;
4. install Python 3.12 with `winget` if Python is missing and winget is available;
5. create an isolated virtual environment for the Analyzer MCP;
6. install MCP dependencies, with automatic PyPI mirror fallback;
7. generate a ready-to-copy `cherry-studio-mcp.json`;
8. copy the Cherry Studio Skill to the local AI Audio Analyzer application folder.

### macOS

Double-click:

```text
Install.command
```

If macOS blocks the downloaded `Install.command` itself, right-click it and choose **Open**, or open Terminal in the package folder and run:

```bash
bash ./install.sh
```

The installer will:

1. install the VST3 to `~/Library/Audio/Plug-Ins/VST3/`;
2. remove quarantine metadata from the plugin to handle the current non-notarized development build;
3. verify or repair the ad-hoc code signature;
4. find Python 3.10+, preferring Python 3.12;
5. use Homebrew to install Python 3.12 when available;
6. optionally offer to install Homebrew when neither Python nor Homebrew is available;
7. create an isolated MCP virtual environment;
8. install MCP dependencies with PyPI mirror fallback;
9. generate `cherry-studio-mcp.json`.

> macOS note: current GitHub builds are ad-hoc signed, not Apple Developer ID notarized. The installer removes the download quarantine attribute for this plugin. Read the manual for details.

---

## 中文快速说明

Windows 用户直接双击 `Install.cmd`。macOS 用户直接双击 `Install.command`。

如果 macOS 连 `Install.command` 本身都阻止打开，可以**右键 → 打开**，或者在该目录打开终端执行：

```bash
bash ./install.sh
```

自动安装脚本会处理 VST3 安装、Python 检测、MCP 虚拟环境、依赖安装、PyPI 镜像回退，以及 Cherry Studio MCP 配置文件生成。

如果自动安装失败，或你希望完全手动控制安装过程，请阅读：

- `INSTALL.zh-CN.md`：完整中文教程；
- `INSTALL.en.md`：English manual。

配套 FL Studio 控制 MCP：

https://github.com/rosasynthesiz/flstudio-mcp
