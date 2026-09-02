# AI Audio Analyzer 0.7 — Installation Guide

[中文安装教程](INSTALL.zh-CN.md)

The Release contains the VST3, a **PyInstaller-packaged standalone Analyzer MCP 0.7 runtime**, the Cherry Studio Skill and automatic installers. Normal users do **not** need Python, pip, a virtual environment or PyPI.

Companion FL Studio control MCP:

https://github.com/rosasynthesiz/flstudio-mcp

## Supported platforms

```text
Windows x64
macOS Apple Silicon arm64
```

Intel/x86_64 macOS is not included in current Releases.

## Package layout

```text
AI Audio Analyzer.vst3
mcp/
├─ runtime/ai-audio-analyzer-mcp/...
└─ source/
   ├─ server.py
   ├─ analyzer_core.py
   ├─ project_tools.py
   ├─ temporal_tools.py
   ├─ masking_tools.py
   ├─ requirements.txt
   └─ cherry-studio.example.json
skill/
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
platform installer script(s)
```

The packaged executable remains named `ai-audio-analyzer-mcp` (`.exe` on Windows). Source/PyInstaller startup always uses `server.py`; MCP/protocol versions are metadata, not versioned filenames.

## Recommended automatic installation

### Windows

Double-click `Install.cmd`.

The standard VST3 directory is under `Program Files`, so UAC is requested only for the plugin copy. MCP, Skill and generated configuration remain under the current user:

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

The installer copies the VST3, installs the standalone MCP runtime, runs its built-in self-test, copies the Skill and generates `cherry-studio-mcp.json` with the absolute executable path.

### macOS Apple Silicon

The installer requires:

```bash
uname -m
```

to report `arm64`.

Double-click `Install.command`. If macOS blocks the downloaded script itself, right-click it → **Open**, or run:

```bash
bash ./install.sh
```

Install locations:

```text
VST3  ~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3
MCP   ~/Library/Application Support/AI Audio Analyzer/mcp/
Skill ~/Library/Application Support/AI Audio Analyzer/skill/
```

The installer removes quarantine metadata where possible, verifies the installed VST3 signature and repairs it with a local ad-hoc signature if required, then self-tests the standalone MCP and generates `cherry-studio-mcp.json`.

Current GitHub builds are **ad-hoc signed and not Apple Developer ID notarized**.

## Cherry Studio configuration

Automatic installation generates:

```text
Windows: %LOCALAPPDATA%\AI Audio Analyzer\cherry-studio-mcp.json
macOS:   ~/Library/Application Support/AI Audio Analyzer/cherry-studio-mcp.json
```

The normal packaged-runtime shape is:

```json
{
  "mcpServers": {
    "ai-audio-analyzer": {
      "command": "/absolute/path/to/ai-audio-analyzer-mcp",
      "args": [],
      "env": {
        "AI_ANALYZER_OSC_HOST": "127.0.0.1",
        "AI_ANALYZER_OSC_PORT": "9855"
      }
    }
  }
}
```

Do not keep another Analyzer MCP instance running manually while Cherry Studio starts this one. Only one Bridge process should bind UDP port `9855`.

## Manual standalone self-test

Windows:

```powershell
$env:AI_ANALYZER_SELF_TEST='1'
& "$env:LOCALAPPDATA\AI Audio Analyzer\mcp\runtime\ai-audio-analyzer-mcp\ai-audio-analyzer-mcp.exe"
Remove-Item Env:AI_ANALYZER_SELF_TEST
```

macOS:

```bash
AI_ANALYZER_SELF_TEST=1 \
  ./mcp/runtime/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
```

A healthy 0.7 runtime reports JSON containing fields similar to:

```json
{
  "ok": true,
  "entrypoint": "server.py",
  "mcp_version": "0.7",
  "osc_protocol_version": "0.6",
  "tool_count": 20
}
```

## Skill

Import the packaged/installed `skill/` directory into Cherry Studio.

The Skill is English-only by project policy and teaches MCP invocation, mapping, validity, parameter semantics, temporal evidence and masking-evidence limitations. It does not impose a mixing style.

MCP 0.7 includes 20 tools, including:

```text
audio_project_status()
audio_mix_overview()
audio_capture_snapshot()
audio_compare_snapshots()
audio_temporal_profile()
audio_temporal_compare()
audio_masking_evidence()
audio_project_masking_scan()
```

V0.4 Identify remains the deterministic way to map Analyzer instances to FL Mixer Track/Slot locations.

## Advanced developer fallback — Python source

Use source mode only for Bridge development, PyInstaller debugging or unusual standalone-runtime fallback.

Python **3.10+** is required; Python 3.12 is recommended.

Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\mcp\source\requirements.txt
$env:AI_ANALYZER_SELF_TEST='1'
python .\mcp\source\server.py
```

macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r ./mcp/source/requirements.txt
AI_ANALYZER_SELF_TEST=1 python ./mcp/source/server.py
```

For source mode, Cherry Studio `command` points to the venv Python and `args` points to the absolute `server.py` path.

### PyPI mirrors for source mode

```text
official   https://pypi.org/simple
tsinghua   https://pypi.tuna.tsinghua.edu.cn/simple
aliyun     https://mirrors.aliyun.com/pypi/simple/
```

Do not disable TLS verification to work around certificate/proxy problems.

## Troubleshooting

### FL Studio cannot find the plugin

Expected locations:

```text
Windows: C:\Program Files\Common Files\VST3\AI Audio Analyzer.vst3\Contents\...
macOS:   ~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3/Contents/...
```

Fully quit FL Studio, reopen it and force a plugin rescan.

### macOS blocks the plugin or installer

Prefer the bundled installer. If the script itself is blocked, right-click → Open or run `bash ./install.sh`. Manual VST3 installation may require removing `com.apple.quarantine` and locally verifying/repairing the ad-hoc signature. The Release is not notarized.

### Intel Mac

Current Releases do not contain x86_64 binaries. The macOS installer intentionally requires arm64.

### Cherry Studio reports `Connection closed`

Run the packaged MCP self-test first. If it succeeds, verify Cherry Studio points to the same executable and confirm no other Bridge owns UDP `9855`.

Python/PyPI are irrelevant to the normal standalone Release runtime.

### `No module named mcp.server.fastmcp`

This should only occur in a stale source environment. The packaged runtime already contains MCP SDK 2.x. If intentionally using source mode, reinstall from `mcp/source/requirements.txt` and launch `server.py`.

### MCP works but no Analyzer appears

Verify the VST3 is loaded, OSC host/port matches `127.0.0.1:9855`, and FL Studio is processing audio when measurements are needed. Multiple Analyzer instances share the same UDP port. Use Identify + `audio_instance_map()` for deterministic mapping.

### Temporal tools say unsupported/unavailable

V0.6 temporal tools require frames from **AI Audio Analyzer VST3 0.6+**. Also check `signal_present`, `temporal_supported`, `temporal_valid` and requested window coverage.

### Masking evidence is unavailable

V0.7 masking evidence requires valid spectrum history for both tracks. Time-weighted evidence also depends on usable V0.6-aligned frames. Treat returned scores as heuristic evidence, not audible-masking probability.
