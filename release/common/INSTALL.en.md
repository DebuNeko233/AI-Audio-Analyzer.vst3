# AI Audio Analyzer 0.6 — Installation Guide

[中文安装教程](INSTALL.zh-CN.md)

The Release contains the VST3, a **PyInstaller-packaged standalone Analyzer MCP 0.6 runtime**, the Cherry Studio Skill and automatic installers. Normal users do **not** need Python, pip, a virtual environment or PyPI.

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
   ├─ server_v05.py
   ├─ server_v06.py
   ├─ project_tools.py
   ├─ temporal_tools.py
   ├─ requirements.txt
   └─ cherry-studio.example.json
skill/
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
platform installer script(s)
```

The packaged executable is still named `ai-audio-analyzer-mcp` (`.exe` on Windows). Internally the current MCP source entry point is `server_v06.py`.

## Recommended automatic installation

### Windows

Double-click:

```text
Install.cmd
```

The standard VST3 directory is under `Program Files`, so UAC is requested only for the plugin copy. MCP, Skill and generated configuration remain under the current user:

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

The installer:

1. copies `AI Audio Analyzer.vst3` to the standard VST3 location;
2. installs the standalone MCP runtime;
3. runs `AI_ANALYZER_SELF_TEST=1` against the packaged executable;
4. copies the Skill;
5. generates `cherry-studio-mcp.json` with the absolute executable path.

### macOS Apple Silicon

The installer requires `uname -m` to report:

```text
arm64
```

Double-click:

```text
Install.command
```

If macOS blocks the downloaded script itself, right-click `Install.command` → **Open**, or run:

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

The configuration shape is:

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

## Manual installation — Windows, no Python

1. Copy the plugin to:

```text
C:\Program Files\Common Files\VST3\AI Audio Analyzer.vst3
```

2. Keep `mcp/` and `skill/` in a stable location, for example:

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

3. Test the packaged MCP:

```powershell
$env:AI_ANALYZER_SELF_TEST='1'
& "$env:LOCALAPPDATA\AI Audio Analyzer\mcp\runtime\ai-audio-analyzer-mcp\ai-audio-analyzer-mcp.exe"
Remove-Item Env:AI_ANALYZER_SELF_TEST
```

A healthy 0.6 runtime reports JSON containing approximately:

```json
{"ok":true,"server":"AI Audio Analyzer MCP","tool_count":18,"entrypoint":"0.6"}
```

4. Point Cherry Studio `command` to the `.exe`, keep `args` empty, and import `skill/`.

## Manual installation — macOS Apple Silicon, no Python

Confirm architecture:

```bash
uname -m
```

Expected:

```text
arm64
```

Copy the VST3:

```bash
mkdir -p "$HOME/Library/Audio/Plug-Ins/VST3"
ditto "./AI Audio Analyzer.vst3" \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

Remove quarantine and verify the ad-hoc signature:

```bash
xattr -dr com.apple.quarantine \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"

codesign --verify --deep --strict --verbose=4 \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

If verification fails after local copying/quarantine handling, repair the local ad-hoc signature:

```bash
codesign --force --deep --sign - --timestamp=none \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

Standalone MCP executable:

```text
mcp/runtime/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
```

Self-test:

```bash
xattr -dr com.apple.quarantine ./mcp
chmod +x ./mcp/runtime/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
AI_ANALYZER_SELF_TEST=1 \
  ./mcp/runtime/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
```

Point Cherry Studio `command` to that executable and keep `args` empty.

## Skill

Import the packaged/installed `skill/` directory into Cherry Studio.

The Skill teaches MCP invocation and measurement semantics only. It does not impose a mixing style. MCP 0.6 includes 18 tools, including:

```text
audio_project_status()
audio_mix_overview()
audio_capture_snapshot()
audio_compare_snapshots()
audio_temporal_profile()
audio_temporal_compare()
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
python .\mcp\source\server_v06.py
```

macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r ./mcp/source/requirements.txt
AI_ANALYZER_SELF_TEST=1 python ./mcp/source/server_v06.py
```

For source mode, Cherry Studio `command` points to the venv Python and `args` points to the absolute `server_v06.py` path.

### PyPI mirrors for source mode

```text
official   https://pypi.org/simple
tsinghua   https://pypi.tuna.tsinghua.edu.cn/simple
aliyun     https://mirrors.aliyun.com/pypi/simple/
```

Examples:

```bash
python -m pip install -r requirements.txt -i https://pypi.org/simple
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

Do not disable TLS verification to work around certificate/proxy problems.

## Troubleshooting

### FL Studio cannot find the plugin

Expected plugin locations:

```text
Windows: C:\Program Files\Common Files\VST3\AI Audio Analyzer.vst3\Contents\...
macOS:   ~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3/Contents/...
```

Fully quit FL Studio, reopen it and force a plugin rescan.

### macOS blocks the plugin or installer

Prefer the bundled installer. If the script itself is blocked, right-click → Open or run `bash ./install.sh`. Manual VST3 installation requires the quarantine/signature steps above. The Release is not notarized.

### Intel Mac

Current Releases do not contain x86_64 binaries. The macOS installer intentionally requires arm64.

### Cherry Studio reports `Connection closed`

Run the packaged MCP self-test first. If it succeeds, verify Cherry Studio points to the same executable and confirm no other Bridge owns UDP `9855`.

Python/PyPI are irrelevant to the normal standalone Release runtime.

### `No module named mcp.server.fastmcp`

This should only occur in a stale source environment. The packaged runtime already contains MCP SDK 2.x. If intentionally using source mode, reinstall from `mcp/source/requirements.txt` and launch `server_v06.py`.

### MCP works but no Analyzer appears

Verify the VST3 is loaded, OSC host/port matches `127.0.0.1:9855`, and FL Studio is processing audio when measurements are needed. Multiple Analyzer instances share the same UDP port. Use Identify + `audio_instance_map()` for deterministic mapping.

### Temporal tools say unsupported/unavailable

V0.6 temporal tools require frames from **AI Audio Analyzer VST3 0.6+**. Also check `signal_present`, `temporal_supported`, `temporal_valid` and requested window coverage. An older VST3 can still provide the older measurements but cannot provide V0.6 temporal descriptors.
