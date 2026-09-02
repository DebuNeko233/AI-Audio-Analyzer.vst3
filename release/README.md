# Release / 懒人包发布说明

The normal `build` workflow is for development validation/artifacts. User-facing lazy packages are created by the manual workflow:

```text
.github/workflows/release.yml
```

## Publish from GitHub UI

1. Open **Actions**.
2. Select **release-lazy-package**.
3. Click **Run workflow**.
4. Leave `tag` empty to use `v<CMake project version>`.
5. Enable `prerelease` only for beta/test releases.
6. Enable `draft` when you want to inspect the Release before publication.
7. Run the workflow.

Current public product version is **0.7.0**.

The workflow publishes:

```text
AI-Audio-Analyzer-v<version>-Windows.zip
AI-Audio-Analyzer-v<version>-macOS.zip
SHA256SUMS.txt
```

Supported Release targets:

```text
Windows x64
macOS Apple Silicon / arm64
```

Intel/x86_64 macOS is intentionally not built or packaged.

## Standalone MCP 0.7

Release packages use PyInstaller **one-file mode (`-F` / `--onefile`)** built from the single supported entrypoint:

```text
bridge/server.py
```

Do not add version-named entrypoints such as `server_v08.py`. MCP/protocol versions are metadata, not startup filenames.

The PyInstaller output is one executable per platform. The lazy package intentionally keeps the existing runtime directory path for installer/config compatibility:

```text
Windows
mcp/runtime/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp.exe

macOS
mcp/runtime/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
```

There is no PyInstaller `_internal/` directory in the one-file runtime.

Current source modules packaged for developer fallback:

```text
server.py
analyzer_core.py
project_tools.py
temporal_tools.py
masking_tools.py
requirements.txt
cherry-studio.example.json
```

MCP 0.7 exposes 20 tools and adds:

```text
audio_masking_evidence()
audio_project_masking_scan()
```

The VST3 frame schema remains V0.6-compatible; V0.7 masking evidence is computed in the Bridge from existing spectrum, level, and temporal measurements.

The **actual one-file executable** must pass its built-in self-test before lazy-package assembly continues.

## Native runtime matrix

```text
windows-latest   → Windows x64 MCP runtime
macos-latest     → macOS arm64 MCP runtime
```

No macOS Intel runtime is built. The macOS VST3 is also arm64-only with deployment target macOS 11.0.

## Final package layout

Windows:

```text
AI-Audio-Analyzer-v<version>-Windows/
├─ AI Audio Analyzer.vst3
├─ mcp/
│  ├─ runtime/
│  │  └─ ai-audio-analyzer-mcp/
│  │     └─ ai-audio-analyzer-mcp.exe
│  └─ source/
│     ├─ server.py
│     ├─ analyzer_core.py
│     ├─ project_tools.py
│     ├─ temporal_tools.py
│     ├─ masking_tools.py
│     ├─ requirements.txt
│     └─ cherry-studio.example.json
├─ skill/
├─ Install.cmd
├─ Install.ps1
├─ START-HERE.md
├─ INSTALL.zh-CN.md
└─ INSTALL.en.md
```

macOS Apple Silicon has the same logical structure plus `Install.command` and `install.sh`; its runtime directory contains only the single `ai-audio-analyzer-mcp` executable.

`mcp/source/` is retained for development/manual fallback only.

## Release validation layers

Do not conflate these states:

```text
source syntax/self-test
PyInstaller one-file build
one-file packaged-runtime self-test
VST3 build
lazy-package assembly
checksum generation
GitHub Release publication
```

A source self-test does not prove the packaged runtime works, and a packaged runtime self-test does not prove the VST3 or final Release package succeeded.

## macOS signing / Gatekeeper

Current macOS builds are ad-hoc signed and are **not Apple Developer ID notarized**.

The Release installer handles current quarantine/Gatekeeper requirements and verifies/repairs the local VST3 signature when needed.

Do not claim notarization unless the workflow actually performs and verifies Apple notarization.

## 中文说明

普通 `build` Action 用于开发验证和开发工件；真正给用户下载的懒人包由：

```text
Actions
→ release-lazy-package
→ Run workflow
```

手动生成。

当前 Release 目标只有 Windows x64 和 macOS Apple Silicon / arm64，不构建 Intel/x86_64 macOS。

MCP 使用 PyInstaller **`-F` / `--onefile` 单文件模式**打包，唯一源码和打包入口始终是 `bridge/server.py`。普通用户不需要 Python、pip、venv 或 PyPI。

为了不破坏安装器和 Cherry Studio 的既有路径，懒人包仍保留 `mcp/runtime/ai-audio-analyzer-mcp/` 这一层目录，但目录中只有一个 MCP executable，不再包含 `_internal/`。

0.7 新增的是 Bridge 侧的 ERB-rate 重分箱 + 相对电平 + V0.6 时间重叠证据模型。它不会增加 OSC 字段，也不应被描述成可听遮蔽概率或自动混音指令。

Python 源码版继续保留在 `mcp/source/`，用于开发、调试和特殊环境 fallback。
