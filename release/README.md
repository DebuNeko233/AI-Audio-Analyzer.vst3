# Release / 懒人包发布说明

The normal `build` workflow is for development artifacts. User-facing lazy packages are created by the separate manual workflow:

```text
.github/workflows/release.yml
```

## Publish from GitHub UI

1. Open **Actions**.
2. Select **release-lazy-package**.
3. Click **Run workflow**.
4. Leave `tag` empty to use `v<CMake project version>`.
5. Enable `prerelease` only for beta/test releases.
6. Enable `draft` when you want to inspect the Release before making it public.
7. Run the workflow.

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

## Standalone MCP build

Release packages do not require end users to install Python or pip. The workflow builds Analyzer MCP 0.5 with PyInstaller `onedir` and runs the executable's built-in self-test before packaging.

Two native MCP runtimes are built independently:

```text
windows-latest   → Windows x64
macos-latest     → macOS arm64 / Apple Silicon
```

The macOS lazy package contains only the arm64 MCP runtime. The Release VST3 is also built as arm64 with deployment target macOS 11.0.

Final package layout:

```text
Windows
├─ AI Audio Analyzer.vst3
├─ mcp/
│  ├─ runtime/ai-audio-analyzer-mcp/...
│  └─ source/...
├─ skill/
├─ Install.cmd
├─ Install.ps1
├─ START-HERE.md
├─ INSTALL.zh-CN.md
└─ INSTALL.en.md

macOS Apple Silicon
├─ AI Audio Analyzer.vst3
├─ mcp/
│  ├─ runtime/ai-audio-analyzer-mcp/...
│  └─ source/...
├─ skill/
├─ Install.command
├─ install.sh
├─ START-HERE.md
├─ INSTALL.zh-CN.md
└─ INSTALL.en.md
```

`mcp/source/` remains in every package for development/manual fallback and contains `server.py`, `server_v05.py`, `project_tools.py`, `requirements.txt`, and the Cherry Studio example.

If a tag already has a GitHub Release, re-running the workflow replaces the package/checksum assets instead of creating a duplicate Release.

## 中文说明

普通 `build` Action 只负责开发阶段回归和工件；真正给用户下载的懒人包由：

```text
Actions
→ release-lazy-package
→ Run workflow
```

手动生成。

Release 中的 Analyzer MCP 已经使用 PyInstaller 打包，所以普通用户**不需要 Python、pip、venv 或 PyPI 网络**。

当前 Release 只构建两个目标：

```text
Windows x64
macOS Apple Silicon / arm64
```

不再构建 Intel/x86_64 macOS MCP，也不再生成 universal macOS VST3；macOS Release 的 VST3 和 MCP 都只针对 arm64。

Python 源码版仍保留在 `mcp/source/`，只用于开发、调试和特殊环境 fallback。

## Validation

Normal `build` CI smoke-tests installer/source changes without recompiling VST3 when plugin source did not change:

```text
Windows installer → PowerShell parse
macOS installer   → bash -n
Bridge 0.5        → source self-test + MCP tool regression
VST3              → skipped when Source/CMake did not change
```

The manual Release workflow performs the expensive checks: two PyInstaller native-runtime builds, packaged-runtime self-tests, clean Windows/macOS VST3 builds, lazy-package assembly, checksums, and GitHub Release upload.
