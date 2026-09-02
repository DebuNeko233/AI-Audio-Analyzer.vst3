# AI Audio Analyzer — Installation Guide

[中文安装教程](INSTALL.zh-CN.md)

The Release package contains the VST3, a **PyInstaller-packaged standalone Analyzer MCP runtime**, the Cherry Studio Skill, and automatic installers. Normal users do **not** need to install Python, pip, or access PyPI.

Companion FL Studio control MCP:

https://github.com/rosasynthesiz/flstudio-mcp

## Package layout

Windows:

```text
AI Audio Analyzer.vst3
mcp/
├─ runtime/
│  └─ ai-audio-analyzer-mcp/
│     ├─ ai-audio-analyzer-mcp.exe
│     └─ _internal/...
└─ source/
   ├─ server.py
   ├─ server_v05.py
   ├─ project_tools.py
   ├─ requirements.txt
   └─ cherry-studio.example.json
skill/
Install.cmd
Install.ps1
```

macOS:

```text
AI Audio Analyzer.vst3
mcp/
├─ runtime/
│  ├─ arm64/ai-audio-analyzer-mcp/...
│  └─ x86_64/ai-audio-analyzer-mcp/...
└─ source/...
skill/
Install.command
install.sh
```

The macOS archive contains native MCP runtimes for both Apple Silicon and Intel. The installer selects the correct runtime automatically; Rosetta is not required for the MCP.

## Recommended automatic installation

### Windows

Double-click:

```text
Install.cmd
```

UAC is requested only for copying the VST3 into the standard `Program Files` location. MCP and Skill files remain under the current user's application-data directory:

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

The installer copies the standalone MCP runtime, runs its built-in self-test, copies the Skill, and creates `cherry-studio-mcp.json` with an absolute executable path.

### macOS

Double-click:

```text
Install.command
```

If macOS blocks the script itself, right-click `Install.command` and choose **Open**, or run:

```bash
bash ./install.sh
```

The VST3 is installed to:

```text
~/Library/Audio/Plug-Ins/VST3/
```

MCP and Skill files are installed to:

```text
~/Library/Application Support/AI Audio Analyzer/
```

The installer selects `arm64` or `x86_64`, removes quarantine metadata, runs the MCP self-test, and generates the Cherry Studio configuration.

## Why normal users do not need Python

The Release MCP uses PyInstaller `onedir` packaging. The Python interpreter and dependencies such as MCP SDK 2.x and `python-osc` are bundled inside `mcp/runtime/`.

Normal runtime path:

```text
Cherry Studio
    ↓ stdio
ai-audio-analyzer-mcp(.exe)
    ↓ OSC UDP 9855
AI Audio Analyzer.vst3
```

This avoids Python-version mismatches, wrong virtual environments, PyPI connectivity problems, and stale MCP v1 installations.

## Cherry Studio configuration

Automatic installation writes:

Windows:

```text
%LOCALAPPDATA%\AI Audio Analyzer\cherry-studio-mcp.json
```

macOS:

```text
~/Library/Application Support/AI Audio Analyzer/cherry-studio-mcp.json
```

The important shape is:

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

Do not keep another Analyzer MCP process running manually while Cherry Studio starts its own copy, because only one process should bind UDP port `9855`.

## Manual installation — Windows, no Python

1. Copy `AI Audio Analyzer.vst3` to:

```text
C:\Program Files\Common Files\VST3\
```

2. Keep `mcp/` and `skill/` in a stable directory such as:

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

3. Test the packaged MCP:

```powershell
$env:AI_ANALYZER_SELF_TEST='1'
& "$env:LOCALAPPDATA\AI Audio Analyzer\mcp\runtime\ai-audio-analyzer-mcp\ai-audio-analyzer-mcp.exe"
Remove-Item Env:AI_ANALYZER_SELF_TEST
```

4. Point Cherry Studio `command` at that `.exe`; leave `args` empty.

5. Import the `skill/` directory.

## Manual installation — macOS, no Python

1. Copy the VST3:

```bash
mkdir -p "$HOME/Library/Audio/Plug-Ins/VST3"
ditto "./AI Audio Analyzer.vst3" \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

2. Current GitHub builds are ad-hoc signed and are **not Apple Developer ID notarized**. Remove quarantine from the installed plugin:

```bash
xattr -dr com.apple.quarantine \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

Verify:

```bash
codesign --verify --deep --strict --verbose=4 \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

If needed, repair the local ad-hoc signature:

```bash
codesign --force --deep --sign - --timestamp=none \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

3. Select the native MCP runtime using `uname -m`:

```text
mcp/runtime/arm64/...       Apple Silicon
mcp/runtime/x86_64/...      Intel
```

4. Remove MCP quarantine and self-test:

```bash
xattr -dr com.apple.quarantine ./mcp
chmod +x ./mcp/runtime/$(uname -m)/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
AI_ANALYZER_SELF_TEST=1 \
  ./mcp/runtime/$(uname -m)/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
```

5. Point Cherry Studio `command` at that executable and leave `args` empty.

## Advanced/developer fallback: run MCP from Python source

Use `mcp/source/` only when developing the Bridge, debugging PyInstaller, modifying the server, or when the standalone runtime fails in an unusual environment.

Python **3.10+** is required; Python 3.12 is recommended.

Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\mcp\source\requirements.txt
$env:AI_ANALYZER_SELF_TEST='1'
python .\mcp\source\server_v05.py
```

macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r ./mcp/source/requirements.txt
AI_ANALYZER_SELF_TEST=1 python ./mcp/source/server_v05.py
```

For source mode, Cherry Studio `command` is the virtual-environment Python and `args` contains the absolute path to `server_v05.py`.

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

Do not disable TLS verification to work around corporate/school proxy certificate problems.

## Troubleshooting

### FL Studio cannot find the plugin

Expected locations:

```text
Windows: C:\Program Files\Common Files\VST3\AI Audio Analyzer.vst3\Contents\...
macOS:   ~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3/Contents/...
```

Fully quit FL Studio, reopen it, and force a plugin rescan.

### macOS blocks the plugin

Use the bundled installer first. For manual installation, remove `com.apple.quarantine` as shown above. The current Release is not notarized.

### Cherry Studio reports `Connection closed`

Run the packaged executable with `AI_ANALYZER_SELF_TEST=1`. If self-test passes, verify that Cherry Studio points to the same executable and that no second bridge process owns UDP `9855`.

Python/PyPI are not involved in the normal Release runtime. Only debug those if you intentionally selected source mode.

### `No module named mcp.server.fastmcp`

This indicates an old source environment. The packaged Release runtime already contains MCP SDK 2.x and does not require pip repair.

### MCP works but no Analyzer instances appear

Verify that `AI Audio Analyzer` is inserted in FL Studio, the plugin and MCP both use `127.0.0.1:9855`, and FL Studio is processing audio when measurements are expected.

Multiple Analyzer instances intentionally share one UDP port. Use the v0.4 Identify mapping and v0.5 project tools for deterministic Mixer Track/Slot analysis.
