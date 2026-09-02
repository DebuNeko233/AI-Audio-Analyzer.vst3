# AI Audio Analyzer 0.7 — Start Here / 从这里开始

[English manual](INSTALL.en.md) | [中文安装教程](INSTALL.zh-CN.md)

This Release package contains:

```text
AI Audio Analyzer.vst3
mcp/
├─ runtime/     standalone PyInstaller MCP 0.7 runtime
└─ source/      Python source fallback for developers
skill/          English LLM-facing Skill
Install script(s)
INSTALL.en.md
INSTALL.zh-CN.md
```

**Normal installation does not require Python, pip, a virtual environment, or PyPI access.**

Current Release platforms:

```text
Windows x64
macOS Apple Silicon arm64
```

Intel/x86_64 macOS is not included.

## Fastest path / 最快安装

### Windows

Double-click:

```text
Install.cmd
```

The installer copies the VST3, installs the standalone MCP runtime for the current user, runs the MCP self-test, generates `cherry-studio-mcp.json`, and installs the Skill.

### macOS Apple Silicon

Double-click:

```text
Install.command
```

If macOS blocks the downloaded script, right-click it and choose **Open**, or run:

```bash
bash ./install.sh
```

The installer copies the arm64 VST3 and standalone arm64 MCP runtime, removes quarantine metadata, verifies the local plugin signature, runs the MCP self-test, and generates the Cherry Studio configuration.

> Current macOS builds are ad-hoc signed and are not Apple Developer ID notarized.

## MCP 0.7

The packaged runtime uses `server_v07.py` internally and exposes 20 tools.

V0.7 adds stronger masking-related evidence:

```text
audio_masking_evidence()
audio_project_masking_scan()
```

The evidence model re-bins existing Analyzer spectrum features onto equal ERB-rate regions and combines spectral occupancy, relative level, and V0.6 temporal overlap.

It is **not** a gammatone/cochlear filterbank and **not** an audible-masking probability.

The bundled Skill is English-only and teaches the LLM how to use these measurements without prescribing a mixing style.

---

## 中文快速说明

Windows 用户直接双击 `Install.cmd`；macOS Release 仅支持 Apple Silicon（arm64），直接双击 `Install.command`。

普通用户不需要自己安装 Python、pip、MCP SDK，也不依赖 PyPI / 清华 / 阿里云镜像。Release 已把 Python Runtime 和 MCP 依赖打包进 `mcp/runtime/`。

0.7 的 MCP 新增 `audio_masking_evidence()` 和 `audio_project_masking_scan()`，用于提供更强的遮蔽相关证据，但这些结果只是透明的 heuristic evidence，不是“可听遮蔽概率”，也不会自动给出 EQ / Sidechain 等处理方案。

如果自动安装失败或希望完全手动控制安装，请阅读：

- `INSTALL.zh-CN.md`：完整中文教程；
- `INSTALL.en.md`：English manual.

配套 FL Studio 控制 MCP：

https://github.com/rosasynthesiz/flstudio-mcp
