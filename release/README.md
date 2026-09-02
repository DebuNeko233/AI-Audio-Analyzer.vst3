# Release / 懒人包发布说明

普通 `build` Workflow 用于开发回归和开发 Artifact。面向用户的懒人包由独立的手动 Workflow 创建：

```text
.github/workflows/release.yml
```

## 从 GitHub UI 发布

```text
Actions
→ release-lazy-package
→ Run workflow
```

- `tag` 留空：自动使用 `v<CMake project version>`；
- `prerelease=true`：测试 / Beta；
- `draft=true`：先生成 Draft Release 检查；
- 已存在同 Tag Release 时会覆盖上传 ZIP / checksum，而不是再建一个同名 Release。

当前版本为 **0.6.0**，正常会生成：

```text
AI-Audio-Analyzer-v0.6.0-Windows.zip
AI-Audio-Analyzer-v0.6.0-macOS.zip
SHA256SUMS.txt
```

## 支持平台

```text
Windows x64
macOS Apple Silicon arm64
```

Intel / x86_64 macOS 不构建、不打包。

## Standalone MCP

Release 使用 PyInstaller `onedir` 打包 **MCP 0.6**。当前 PyInstaller 入口：

```text
bridge/server_v06.py
```

构建矩阵：

```text
windows-latest → Windows x64 MCP
macos-latest   → macOS arm64 MCP
```

每个 Runtime 在进入最终懒人包前都必须运行：

```text
AI_ANALYZER_SELF_TEST=1
```

并确认当前 MCP 0.6 的工具注册完整。

普通用户不需要安装 Python、pip、venv 或访问 PyPI。源码 fallback 仍保留在 `mcp/source/`。

## 懒人包结构

```text
Windows
├─ AI Audio Analyzer.vst3
├─ mcp/
│  ├─ runtime/ai-audio-analyzer-mcp/...
│  └─ source/
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
│  └─ source/
├─ skill/
├─ Install.command
├─ install.sh
├─ START-HERE.md
├─ INSTALL.zh-CN.md
└─ INSTALL.en.md
```

`mcp/source/` 当前应包含：

```text
server.py
server_v05.py
server_v06.py
project_tools.py
temporal_tools.py
requirements.txt
cherry-studio.example.json
```

## VST3 构建目标

```text
Windows → x64
macOS   → arm64, deployment target macOS 11.0
```

macOS VST3 当前为 ad-hoc signed，不是 Apple Developer ID Notarized。安装脚本会处理当前开发分发下的 Quarantine / Gatekeeper 问题，但文档不得宣称已经 Notarize。

## 0.6 发布内容

VST3 0.6 在 `/aianalyzer/frame` 的旧字段 0..58 后追加 Temporal Tail：

```text
59 temporal_window_seconds
60 spectral_flux_mean
61 spectral_flux_peak
62 rms_rise_peak_db
63 low_band_energy_db
64 frame_schema_version = "0.6"
```

MCP 0.6 新增：

```text
audio_temporal_profile()
audio_temporal_compare()
```

旧 OSC Prefix 保持兼容；Identify Schema 没有变化。

## Validation

开发 CI 应分别证明：

```text
Python syntax / MCP regression
V0.4 Identify mapping regression
V0.5 Project/Snapshot regression
V0.6 Temporal regression
Windows VST3 build
macOS arm64 VST3 build
installer syntax checks
```

手动 Release Workflow 还必须额外证明：

```text
Windows PyInstaller build + packaged self-test
macOS arm64 PyInstaller build + packaged self-test
Windows lazy-package assembly
macOS lazy-package assembly
SHA256 generation
GitHub Release publication
```

不要因为源码 self-test 成功就声称 Release 已构建成功。
