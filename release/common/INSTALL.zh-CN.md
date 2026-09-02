# AI Audio Analyzer 0.7 — 中文安装教程

[English manual](INSTALL.en.md)

Release 懒人包包含 VST3、**PyInstaller 打包好的 Analyzer MCP 0.7 Standalone Runtime**、Cherry Studio Skill 和自动安装脚本。普通用户不需要安装 Python、pip、venv，也不需要访问 PyPI。

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
平台安装脚本
```

打包后的可执行文件仍叫 `ai-audio-analyzer-mcp`（Windows 为 `.exe`）。源码与 PyInstaller 的唯一启动入口始终是 `server.py`，以后不再使用 `server_vXX.py`。

# 推荐：自动安装

## Windows

直接双击 `Install.cmd`。

标准 VST3 目录位于 `Program Files`，所以只有复制插件时需要 UAC。MCP、Skill 和生成的 Cherry Studio 配置仍保存在当前用户目录：

```text
%LOCALAPPDATA%\AI Audio Analyzer\
```

安装器会复制 VST3、安装 Standalone MCP Runtime、运行内建 self-test、复制 Skill，并生成包含绝对 executable 路径的 `cherry-studio-mcp.json`。

## macOS Apple Silicon

安装器要求：

```bash
uname -m
```

返回 `arm64`。

双击 `Install.command`。如果 macOS 阻止脚本本身启动，可以右键 → **打开**，或执行：

```bash
bash ./install.sh
```

安装位置：

```text
VST3  ~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3
MCP   ~/Library/Application Support/AI Audio Analyzer/mcp/
Skill ~/Library/Application Support/AI Audio Analyzer/skill/
```

安装器会处理可移除的 Quarantine，验证安装后的 VST3 签名；必要时做本地 ad-hoc 重签名，然后运行 Standalone MCP Self-test 并生成 `cherry-studio-mcp.json`。

当前 GitHub Build 是 **ad-hoc signed，并没有 Apple Developer ID Notarization**。

# Cherry Studio 配置

自动安装后生成：

```text
Windows: %LOCALAPPDATA%\AI Audio Analyzer\cherry-studio-mcp.json
macOS:   ~/Library/Application Support/AI Audio Analyzer/cherry-studio-mcp.json
```

Packaged Runtime 的核心形式：

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

不要自己常驻运行另一个 Analyzer MCP，同时又让 Cherry Studio 再启动一个。默认 UDP `9855` 只应由一个 Bridge Process 绑定。

# Standalone MCP 自检

Windows：

```powershell
$env:AI_ANALYZER_SELF_TEST='1'
& "$env:LOCALAPPDATA\AI Audio Analyzer\mcp\runtime\ai-audio-analyzer-mcp\ai-audio-analyzer-mcp.exe"
Remove-Item Env:AI_ANALYZER_SELF_TEST
```

macOS：

```bash
AI_ANALYZER_SELF_TEST=1 \
  ./mcp/runtime/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp
```

健康的 0.7 Runtime 应返回类似：

```json
{
  "ok": true,
  "entrypoint": "server.py",
  "mcp_version": "0.7",
  "osc_protocol_version": "0.6",
  "tool_count": 20
}
```

# Skill

自动安装后导入 `skill/` 目录。LLM-facing Skill 按项目规则统一使用英文，只负责 MCP 调用、映射、有效性、参数语义、Temporal Evidence 和 Masking Evidence 限制，不提供固定混音风格。

MCP 0.7 当前共 20 个工具，其中包括：

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
python .\mcp\source\server.py
```

macOS：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r ./mcp/source/requirements.txt
AI_ANALYZER_SELF_TEST=1 python ./mcp/source/server.py
```

源码模式下，Cherry Studio 的 `command` 指向 venv Python，`args` 指向 `server.py` 的绝对路径。

## Python 本体和 PyPI 镜像

普通 Standalone 安装不涉及这一节。只有源码模式才需要 pip。

```text
官方      https://pypi.org/simple
清华 TUNA https://pypi.tuna.tsinghua.edu.cn/simple
阿里云    https://mirrors.aliyun.com/pypi/simple/
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

优先使用包内 `Install.command`。脚本本身被拦截时右键 → 打开，或运行 `bash ./install.sh`。当前 Release 没有 Notarize。

## Intel Mac

当前 Release 不包含 x86_64 二进制，安装脚本会拒绝非 arm64 系统。

## Cherry Studio 显示 `Connection closed`

先执行 Packaged MCP Self-test。如果自检成功，再检查 Cherry Studio 是否指向同一个 executable，并确认没有第二个 Bridge 占用 UDP `9855`。

## `No module named mcp.server.fastmcp`

这只应该出现在旧源码环境。Packaged Runtime 已内置 MCP SDK 2.x。主动使用源码模式时，请按 `mcp/source/requirements.txt` 重装，并启动 `server.py`。

## MCP 正常但没有 Analyzer

检查 VST3 是否已经加载、OSC Host/Port 是否都是 `127.0.0.1:9855`，以及需要测量时 FL Studio 是否正在处理音频。多个 Analyzer 共用同一个 UDP 9855。使用 Identify + `audio_instance_map()` 做确定映射。

## Temporal Tool 显示 unsupported / unavailable

V0.6 Temporal Tool 需要 **AI Audio Analyzer VST3 0.6+** 的 Frame。继续检查 `signal_present`、`temporal_supported`、`temporal_valid` 和请求窗口覆盖率。

## Masking Evidence unavailable

V0.7 Masking Evidence 要求两个轨道都存在有效频谱历史；时间加权部分还依赖可用的 V0.6 对齐帧。返回分数是 heuristic evidence，不是可听遮蔽概率。
