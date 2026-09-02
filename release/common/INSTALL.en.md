# AI Audio Analyzer — Installation Guide

[中文安装教程](INSTALL.zh-CN.md)

This package is intended for Cherry Studio + FL Studio workflows and contains the VST3 analyzer, Analyzer MCP bridge, and Cherry Studio Skill in one archive.

## Package layout

```text
AI Audio Analyzer.vst3
mcp/
  server.py
  requirements.txt
  cherry-studio.example.json
skill/
  SKILL.md
  references/
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
Install.cmd / Install.ps1        Windows package
Install.command / install.sh     macOS package
```

Companion FL Studio control MCP:

https://github.com/rosasynthesiz/flstudio-mcp

## Recommended automatic installation

### Windows

Double-click `Install.cmd`.

If Windows asks for UAC permission, allow it. Administrator access is needed to copy the VST3 into the standard system VST3 directory.

Advanced usage from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\Install.ps1
```

Select a PyPI source explicitly if needed:

```powershell
.\Install.ps1 -PyPI official
.\Install.ps1 -PyPI tsinghua
.\Install.ps1 -PyPI aliyun
```

The default `auto` mode tries official PyPI first and then falls back to Tsinghua TUNA and Aliyun.

### macOS

Double-click `Install.command` or run:

```bash
bash ./install.sh
```

Choose a PyPI source explicitly if required:

```bash
AI_ANALYZER_PYPI=official bash ./install.sh
AI_ANALYZER_PYPI=tsinghua bash ./install.sh
AI_ANALYZER_PYPI=aliyun bash ./install.sh
```

The default `auto` mode uses the same fallback order as Windows.

## What the automatic installer does

The installer performs these operations without editing your FL Studio project:

- installs the VST3;
- copies `mcp/` and `skill/` into a stable per-user application-data directory;
- finds Python 3.10+ and prefers Python 3.12;
- creates a dedicated Python virtual environment;
- installs `mcp>=2,<3` and `python-osc` from `requirements.txt`;
- validates the MCP Python imports and compiles `server.py`;
- writes an absolute-path Cherry Studio configuration snippet named `cherry-studio-mcp.json`;
- prints the Skill folder that should be imported into Cherry Studio.

It does **not** automatically modify Cherry Studio's own settings files because those paths and formats can change between versions. Instead, it generates a ready-to-copy configuration file.

## Python installation

The Analyzer MCP requires Python **3.10 or newer**. Python 3.12 is the recommended compatibility target for the lazy installer.

### Windows

The installer first checks these sources:

```text
py -3.12
py -3
python
python3
```

If no compatible Python is found and `winget` is available, it runs:

```powershell
winget install -e --id Python.Python.3.12 --scope user
```

Manual alternatives:

- Python official downloads: https://www.python.org/downloads/windows/
- Windows package manager: `winget install -e --id Python.Python.3.12 --scope user`

When installing Python manually, enabling the Python Launcher (`py`) is recommended.

### macOS

The installer checks `python3.12`, `python3`, and `python`. If none are suitable and Homebrew is already installed, it uses:

```bash
brew install python@3.12
```

If neither Python nor Homebrew is installed, the interactive installer can offer to install Homebrew first. You can decline and install Python manually instead.

Manual alternatives:

- Python official downloads: https://www.python.org/downloads/macos/
- Homebrew: https://brew.sh/

## PyPI and mirror problems

The Python interpreter and PyPI are separate things:

- **Python** is the runtime itself.
- **PyPI** is the package index used by pip to download `mcp`, `python-osc`, and their dependencies.

The lazy installer supports these package indexes:

```text
official   https://pypi.org/simple
tsinghua   https://pypi.tuna.tsinghua.edu.cn/simple
aliyun     https://mirrors.aliyun.com/pypi/simple/
```

You can test dependency installation manually:

```bash
python -m pip install -r requirements.txt -i https://pypi.org/simple
```

or:

```bash
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

Do not permanently change your global pip mirror unless you want that setting to affect all Python projects.

If pip fails with SSL/certificate errors on a company or school network, the problem can be an HTTPS inspection proxy rather than PyPI itself. In that case, use your organization's approved CA/proxy configuration instead of disabling TLS verification.

## Manual installation — Windows

### 1. Install the VST3

Copy:

```text
AI Audio Analyzer.vst3
```

to:

```text
C:\Program Files\Common Files\VST3\
```

Then fully restart FL Studio and run a plugin rescan.

### 2. Install Python

Verify:

```powershell
py -3.12 --version
```

or:

```powershell
python --version
```

A version of 3.10+ is required.

### 3. Create the MCP environment

From the package directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\mcp\requirements.txt
```

If official PyPI is slow:

```powershell
python -m pip install -r .\mcp\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. Configure Cherry Studio

Use the virtual-environment Python as `command` and the absolute path to `mcp/server.py` as the first argument.

Example:

```json
{
  "mcpServers": {
    "ai-audio-analyzer": {
      "command": "C:\\absolute\\path\\.venv\\Scripts\\python.exe",
      "args": ["C:\\absolute\\path\\mcp\\server.py"],
      "env": {
        "AI_ANALYZER_OSC_HOST": "127.0.0.1",
        "AI_ANALYZER_OSC_PORT": "9855"
      }
    }
  }
}
```

### 5. Import the Skill

Import the packaged `skill/` folder into Cherry Studio.

## Manual installation — macOS

### 1. Install the VST3

Copy the plugin to:

```text
~/Library/Audio/Plug-Ins/VST3/
```

Create the directory if required:

```bash
mkdir -p "$HOME/Library/Audio/Plug-Ins/VST3"
```

### 2. Gatekeeper / quarantine

Current GitHub builds are ad-hoc signed and are **not Apple-notarized**. GitHub/browser downloads can receive the `com.apple.quarantine` attribute.

Remove it from the installed plugin:

```bash
xattr -dr com.apple.quarantine \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

Verify the signature:

```bash
codesign --verify --deep --strict --verbose=4 \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

If the ad-hoc signature became invalid after local file manipulation, repair it:

```bash
codesign --force --deep --sign - --timestamp=none \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

Then remove quarantine again and fully restart FL Studio before rescanning.

### 3. Install Python and MCP dependencies

With Homebrew:

```bash
brew install python@3.12
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r ./mcp/requirements.txt
```

Tsinghua mirror example:

```bash
python -m pip install -r ./mcp/requirements.txt \
  -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. Configure Cherry Studio

Example:

```json
{
  "mcpServers": {
    "ai-audio-analyzer": {
      "command": "/absolute/path/.venv/bin/python",
      "args": ["/absolute/path/mcp/server.py"],
      "env": {
        "AI_ANALYZER_OSC_HOST": "127.0.0.1",
        "AI_ANALYZER_OSC_PORT": "9855"
      }
    }
  }
}
```

### 5. Import the Skill

Import `skill/` into Cherry Studio.

## Troubleshooting

### FL Studio does not show the VST3

Check that the bundle itself is located directly under a scanned VST3 directory and that you did not accidentally install an extra nested archive directory.

Expected macOS form:

```text
~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3/Contents/...
```

Expected Windows form:

```text
C:\Program Files\Common Files\VST3\AI Audio Analyzer.vst3\Contents\...
```

Then fully restart FL Studio and force a plugin rescan.

### Cherry Studio says `Connection closed`

Run the generated MCP command in a terminal and read the traceback. Common causes are:

- wrong Python executable;
- dependencies were installed into a different Python environment;
- another Analyzer bridge already owns UDP port `9855`;
- an old `server.py` from MCP SDK v1 is being used.

The current bridge requires MCP Python SDK 2.x. Repair the environment with:

```bash
python -m pip install -U "mcp>=2,<3" python-osc
```

Do not leave `server.py` running manually while Cherry Studio also launches it.

### `No module named mcp.server.fastmcp`

That is an old MCP v1 bridge/import. Use the `mcp/` folder from the current release and reinstall:

```bash
python -m pip install -U "mcp>=2,<3" python-osc
```

### MCP works but `audio_list_tracks()` is empty

Check all of the following:

- `AI Audio Analyzer` is inserted on the intended Mixer Track;
- FL Studio is actually processing audio when measurements are expected;
- OSC host is `127.0.0.1` unless intentionally changed;
- OSC port is `9855` on both sides;
- no second bridge process is competing for the port.

### Multiple Analyzer instances

All plugin instances intentionally send to the same UDP port. Use the v0.4 `Identify` workflow with the companion FL Studio MCP to bind runtime UUIDs to Mixer Track/Slot positions.

Companion project:

https://github.com/rosasynthesiz/flstudio-mcp
