# AI Audio Analyzer 0.6 — 中文安装教程

[English manual](INSTALL.en.md)

Release 懒人包包含 VST3、**PyInstaller 打包好的 Analyzer MCP 0.6 Standalone Runtime**、Cherry Studio Skill 和自动安装脚本。普通用户不需要安装 Python、pip、venv，也不需要访问 PyPI。

配套 FL Studio 控制 MCP：

https://github.com/rosasynthesiz/flstudio-mcp

## 平台支持

```text
Windows x64
macOS Apple Silicon arm64
```

当前 Release 不提供 Intel / x86_64 macOS 包。

## 包内结构

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
平台安装脚本
```

打包后的可执行文件仍叫 `ai-audio-analyzer-mcp`（Windows 为 `.exe`）；当前源码 MCP 入口已经是 `server_v06.py`。

# 推荐：自动安装

## Windows

直接双击：

```text
Install.cmd
```

标准 VST3 目录位于 `Program Files`，所以只有复制插件时需要 UAC。MCP、Skill 和生成的 Cherry Studio 配置仍保存在当前用户目录：

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

安装器会：

1. 把 `AI Audio Analyzer.vst3` 复制到标准 VST3 目录；
2. 安装 Standalone MCP Runtime；
3. 对打包后的 MCP 执行 `AI_ANALYZER_SELF_TEST=1`；
4. 复制 Skill；
5. 生成包含绝对 executable 路径的 `cherry-studio-mcp.json`。

## macOS Apple Silicon

安装器要求：

```bash
uname -m
```

返回：

```text
arm64
```

双击：

```text
Install.command
```

如果 macOS 阻止脚本本身启动，可以右键 `Install.command` → **打开**，或执行：

```bash
bash ./install.sh
```

安装位置：

```text
VST3  ~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3
MCP   ~/Library/Application Support/AI Audio Analyzer/mcp/
Skill ~/Library/Application Support/AI Audio Analyzer/skill/
```

安装器会移除可处理的 Quarantine，验证安装后的 VST3 签名；必要时做本地 ad-hoc 重签名，然后运行 Standalone MCP Self-test 并生成 `cherry-studio-mcp.json`。

当前 GitHub Build 是 **ad-hoc signed，并没有 Apple Developer ID Notarization**。

# Cherry Studio 配置

自动安装后生成：

```text
Windows: %LOCALAPPDATA%\AI Audio Analyzer\cherry-studio-mcp.json
macOS:   ~/Library/Application Support/AI Audio Analyzer/cherry-studio-mcp.json
```

核心结构：

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

不要自己常驻运行另一个 Analyzer MCP，同时又让 Cherry Studio 再启动一个。默认 UDP `9855` 只能由一个 Bridge Process 绑定。

# Windows 手动安装（不安装 Python）

1. 复制插件到：

```text
C:\Program Files\Common Files\VST3\AI Audio Analyzer.vst3
```

2. 把 `mcp/` 和 `skill/` 放到稳定目录，例如：

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

3. 测试打包后的 MCP：

```powershell
$env:AI_ANALYZER_SELF_TEST='1'
& "$env:LOCALAPPDATA\AI Audio Analyzer\mcp\runtime\ai-audio-analyzer-mcp\ai-audio-analyzer-mcp.exe"
Remove-Item Env:AI_ANALYZER_SELF_TEST
```

健康的 0.6 Runtime 应返回包含类似内容的 JSON：

```json
{"ok":true,"server":"AI Audio Analyzer MCP","tool_count":18,"entrypoint":"0.6"}
```

4. Cherry Studio `command` 指向这个 `.exe`，`args` 留空。
5. 导入 `skill/`。

# macOS 手动安装（Apple Silicon，不安装 Python）

先确认：

```bash
uname -m
```

必须是：

```text
arm64
```

复制 VST3：

```bash
mkdir -p "$HOME/Library/Audio/Plug-Ins/VST3"
ditto "./AI Audio Analyzer.vst3" \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

移除 Quarantine 并验证当前 ad-hoc 签名：

```bash
xattr -dr com.apple.quarantine \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"

codesign --verify --deep --strict --verbose=4 \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

如果复制 / Quarantine 处理后验证失败，可以做本地 ad-hoc 重签名：

```bash
codesign --force --deep --sign - --timestamp=none \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

Standalone MCP：

```text
mcp/runtime/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
```

自检：

```bash
xattr -dr com.apple.quarantine ./mcp
chmod +x ./mcp/runtime/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
AI_ANALYZER_SELF_TEST=1 \
  ./mcp/runtime/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
```

Cherry Studio `command` 指向该 executable，`args` 留空。

# Skill

自动安装后导入 `skill/` 目录。

Skill 只负责 MCP 调用与参数语义，不提供固定混音风格。MCP 0.6 当前共 18 个工具，其中包括：

```text
audio_project_status()
audio_mix_overview()
audio_capture_snapshot()
audio_compare_snapshots()
audio_temporal_profile()
audio_temporal_compare()
```

多个 Analyzer 与 FL Mixer Track / Slot 的对应关系仍然使用 V0.4 Identify 机制确定，不靠名字猜。

# 高级 / 开发者：Python 源码模式

只有开发 Bridge、调试 PyInstaller 或特殊 Standalone Runtime 故障时才建议使用 `mcp/source/`。

要求 Python **3.10+**，推荐 Python 3.12。

Windows：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\mcp\source\requirements.txt
$env:AI_ANALYZER_SELF_TEST='1'
python .\mcp\source\server_v06.py
```

macOS：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r ./mcp/source/requirements.txt
AI_ANALYZER_SELF_TEST=1 python ./mcp/source/server_v06.py
```

源码模式下，Cherry Studio 的 `command` 指向 venv Python，`args` 指向 `server_v06.py` 的绝对路径。

## Python 本体和 PyPI 镜像

普通 Standalone 安装不涉及这一节。只有源码模式才需要 pip。

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

不要为了绕过代理 / 证书问题关闭 TLS 验证。

# 常见故障

## FL Studio 扫不到插件

标准路径：

```text
Windows: C:\Program Files\Common Files\VST3\AI Audio Analyzer.vst3\Contents\...
macOS:   ~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3/Contents/...
```

完全退出 FL Studio，重新打开并强制重新扫描插件。

## macOS 无法验证 / 已阻止

优先使用包内 `Install.command`。脚本本身被拦截时右键 → 打开，或运行 `bash ./install.sh`。手动插件安装则按上面执行 `xattr` / `codesign`。当前 Release 没有 Notarize。

## Intel Mac

当前 Release 不包含 x86_64 二进制，安装脚本会拒绝非 arm64 系统。

## Cherry Studio 显示 `Connection closed`

先执行 Packaged MCP Self-test。如果自检成功，再检查 Cherry Studio 是否指向同一个 executable，并确认没有第二个 Bridge 占用 UDP `9855`。

正常 Release Runtime 不涉及 Python / PyPI。

## `No module named mcp.server.fastmcp`

这只应该出现在旧源码环境。Packaged Runtime 已内置 MCP SDK 2.x。主动使用源码模式时，请按 `mcp/source/requirements.txt` 重装，并启动 `server_v06.py`。

## MCP 正常但没有 Analyzer

检查 VST3 是否已经加载、OSC Host/Port 是否都是 `127.0.0.1:9855`，以及需要测量时 FL Studio 是否正在处理音频。多个 Analyzer 共用同一个 UDP 9855。使用 Identify + `audio_instance_map()` 做确定映射。

## Temporal Tool 显示 unsupported / unavailable

V0.6 Temporal Tool 需要 **AI Audio Analyzer VST3 0.6+** 的 Frame。继续检查 `signal_present`、`temporal_supported`、`temporal_valid` 和请求窗口覆盖率。旧版 VST3 仍可以提供旧指标，但不能提供 V0.6 Temporal Descriptor。
