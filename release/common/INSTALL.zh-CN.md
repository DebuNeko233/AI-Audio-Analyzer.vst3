# AI Audio Analyzer — 中文安装教程

[English manual](INSTALL.en.md)

Release 懒人包包含 VST3、**已经用 PyInstaller 打包好的 Analyzer MCP**、Cherry Studio Skill 和自动安装脚本。普通用户不需要安装 Python、pip，也不需要访问 PyPI。

配套 FL Studio 控制 MCP：

https://github.com/rosasynthesiz/flstudio-mcp

## 包内结构

Windows：

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
START-HERE.md
INSTALL.zh-CN.md
INSTALL.en.md
```

macOS：

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
START-HERE.md
INSTALL.zh-CN.md
INSTALL.en.md
```

macOS 包同时包含 Apple Silicon 与 Intel 两套原生 MCP Runtime，安装器会根据 `uname -m` 自动选择，不要求 Rosetta。

# 推荐：自动安装

## Windows

直接双击：

```text
Install.cmd
```

标准 VST3 目录位于 `Program Files`，因此只在复制插件时会弹出 UAC。MCP 和 Skill 仍安装在当前用户目录：

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

安装器会：复制 VST3、复制 standalone MCP、运行 MCP 内建 self-test、复制 Skill，并生成可直接用于 Cherry Studio 的 `cherry-studio-mcp.json`。

## macOS

双击：

```text
Install.command
```

如果 macOS 阻止脚本本身启动，可以右键 `Install.command` → **打开**，或在终端运行：

```bash
bash ./install.sh
```

安装器会把 VST3 放到：

```text
~/Library/Audio/Plug-Ins/VST3/
```

MCP 和 Skill 放到：

```text
~/Library/Application Support/AI Audio Analyzer/
```

并自动选择 `arm64` 或 `x86_64` MCP Runtime、移除下载 Quarantine、执行 MCP self-test、生成 Cherry Studio 配置。

# 普通用户为什么不需要 Python

Release 中的 MCP 使用 PyInstaller `onedir` 模式打包。Python 解释器和 `mcp`、`python-osc` 等运行依赖已经包含在 `mcp/runtime/` 内。

因此普通安装路径是：

```text
Cherry Studio
    ↓ stdio
ai-audio-analyzer-mcp(.exe)
    ↓ OSC UDP 9855
AI Audio Analyzer.vst3
```

而不是：

```text
Cherry Studio → python → server.py → pip dependencies
```

这会直接避免以下常见问题：Python 版本不匹配、`mcp.server.fastmcp` 旧环境、依赖装到错误解释器、PyPI 连接失败、清华/阿里镜像问题、venv 配错路径。

# Cherry Studio 配置

自动安装后会生成：

Windows：

```text
%LOCALAPPDATA%\AI Audio Analyzer\cherry-studio-mcp.json
```

macOS：

```text
~/Library/Application Support/AI Audio Analyzer/cherry-studio-mcp.json
```

配置的核心形式是：

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

Windows 的 `command` 指向 `.exe`。macOS 指向当前 CPU 架构对应的可执行文件。

不要在终端中另外常驻一个 Analyzer MCP，同时又让 Cherry Studio 启动第二个，因为默认只有一个进程可以绑定 UDP `9855`。

# 安装 Skill

自动安装后 Skill 位于当前用户的 AI Audio Analyzer 应用目录下的 `skill/`。在 Cherry Studio 中导入该目录。

0.5 Skill 应优先使用工程级工具，例如：

```text
audio_project_status()
audio_mix_overview()
audio_capture_snapshot()
audio_compare_snapshots()
```

并继续使用 0.4 Identify 建立 Analyzer ↔ FL Mixer Track/Slot 映射。

# Windows 手动安装（不安装 Python）

1. 将 `AI Audio Analyzer.vst3` 复制到：

```text
C:\Program Files\Common Files\VST3\
```

2. 将包内 `mcp/` 和 `skill/` 保存到稳定目录，例如：

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

3. 手动测试 MCP：

```powershell
$env:AI_ANALYZER_SELF_TEST='1'
& "$env:LOCALAPPDATA\AI Audio Analyzer\mcp\runtime\ai-audio-analyzer-mcp\ai-audio-analyzer-mcp.exe"
Remove-Item Env:AI_ANALYZER_SELF_TEST
```

应该返回类似：

```json
{"ok": true, "server": "AI Audio Analyzer MCP", "entrypoint": "0.5"}
```

4. Cherry Studio 的 `command` 指向上述 `.exe`，`args` 留空。

5. 导入 `skill/`。

# macOS 手动安装（不安装 Python）

1. 复制 VST3：

```bash
mkdir -p "$HOME/Library/Audio/Plug-Ins/VST3"
ditto "./AI Audio Analyzer.vst3" \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

2. 当前 GitHub Release 仍是 ad-hoc 签名，不是 Apple Developer ID Notarization 正式公证包。下载后建议移除 Quarantine：

```bash
xattr -dr com.apple.quarantine \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

验证签名：

```bash
codesign --verify --deep --strict --verbose=4 \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

必要时本地重新 ad-hoc 签名：

```bash
codesign --force --deep --sign - --timestamp=none \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

3. 保存 `mcp/` 和 `skill/`，然后按机器架构选择 MCP：

```bash
uname -m
```

Apple Silicon 使用：

```text
mcp/runtime/arm64/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
```

Intel 使用：

```text
mcp/runtime/x86_64/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
```

4. 移除 MCP Quarantine 并自检：

```bash
xattr -dr com.apple.quarantine ./mcp
chmod +x ./mcp/runtime/$(uname -m)/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
AI_ANALYZER_SELF_TEST=1 \
  ./mcp/runtime/$(uname -m)/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
```

5. Cherry Studio 的 `command` 指向该可执行文件，`args` 留空。

# 高级 / 开发者：使用 Python 源码运行 MCP

只有以下情况才建议使用 `mcp/source/`：开发 Bridge、调试 PyInstaller、需要修改源码，或 standalone runtime 在特殊环境下无法启动。

要求 Python **3.10+**，推荐 Python 3.12。

Windows：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\mcp\source\requirements.txt
$env:AI_ANALYZER_SELF_TEST='1'
python .\mcp\source\server_v05.py
```

macOS：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r ./mcp/source/requirements.txt
AI_ANALYZER_SELF_TEST=1 python ./mcp/source/server_v05.py
```

源码方式配置 Cherry Studio 时：`command` 指向 venv Python，`args` 指向 `server_v05.py`，不要再使用旧入口作为默认配置。

## Python 本体与 PyPI 镜像

如果你选择源码模式，Python 本体和 PyPI 是两回事：Python 是解释器，PyPI 是 pip 下载依赖的仓库。

可用索引：

```text
官方      https://pypi.org/simple
清华 TUNA https://pypi.tuna.tsinghua.edu.cn/simple
阿里云    https://mirrors.aliyun.com/pypi/simple/
```

例如：

```bash
python -m pip install -r requirements.txt -i https://pypi.org/simple
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

不建议为本项目永久修改全局 pip 源。SSL / Certificate / Proxy 错误应按网络环境配置 CA/代理，不要关闭 TLS 验证。

# 常见故障

## FL Studio 扫不到插件

确认路径直接是：

Windows：

```text
C:\Program Files\Common Files\VST3\AI Audio Analyzer.vst3\Contents\...
```

macOS：

```text
~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3/Contents/...
```

然后完全退出 FL Studio，重新打开并强制重新扫描。

## macOS 提示无法验证 / 已阻止

先使用包内 `Install.command`。手动安装则执行上面的 `xattr -dr com.apple.quarantine`。当前 Release 未做 Apple Notarization，这是已知分发限制。

## Cherry Studio 显示 `Connection closed`

首先直接运行 MCP self-test。若 self-test 成功，检查 Cherry Studio `command` 是否指向正确的 packaged executable。

其次检查 UDP `9855` 是否已经被另一个 Analyzer Bridge 占用。不要同时启动源码版和 PyInstaller 版 MCP。

如果使用源码模式，再检查 Python / MCP SDK 环境；正常 Release runtime 不涉及 Python 或 PyPI。

## `No module named mcp.server.fastmcp`

这只应该出现在旧源码环境。当前 Release standalone runtime 已内置 MCP 2.x，不需要 pip 修复。若你主动使用源码模式，请安装：

```bash
python -m pip install -U "mcp>=2,<3" python-osc
```

## MCP 正常但没有 Analyzer

检查 VST3 是否插入目标 Mixer Track、OSC Host 是否为 `127.0.0.1`、端口是否为 `9855`、FL Studio 是否正在处理需要测量的音频。

一个工程可以放多个 Analyzer，全部共享同一个 UDP `9855`。使用 Identify + `audio_instance_map()` 建立确定的 Mixer Track/Slot 映射。
