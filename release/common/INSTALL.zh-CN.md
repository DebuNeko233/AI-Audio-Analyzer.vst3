# AI Audio Analyzer — 中文安装教程

[English manual](INSTALL.en.md)

这个“懒人包”面向 **Cherry Studio + FL Studio** 工作流，已经把 VST3、Analyzer MCP 和 Cherry Studio Skill 放在同一个平台安装包中。

## 包内结构

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
Install.cmd / Install.ps1        Windows 包
Install.command / install.sh     macOS 包
```

配套 FL Studio 控制 MCP：

https://github.com/rosasynthesiz/flstudio-mcp

## 推荐：自动安装

### Windows

直接双击：

```text
Install.cmd
```

如果弹出 UAC 管理员确认，请允许。因为标准 VST3 安装目录位于 `Program Files`，复制插件需要管理员权限。

也可以在 PowerShell 中运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\Install.ps1
```

如果网络环境访问 PyPI 不稳定，可以手动指定镜像：

```powershell
.\Install.ps1 -PyPI official
.\Install.ps1 -PyPI tsinghua
.\Install.ps1 -PyPI aliyun
```

默认 `auto` 模式按以下顺序尝试：官方 PyPI → 清华 TUNA → 阿里云。

### macOS

双击：

```text
Install.command
```

或者终端执行：

```bash
bash ./install.sh
```

手动指定 PyPI：

```bash
AI_ANALYZER_PYPI=official bash ./install.sh
AI_ANALYZER_PYPI=tsinghua bash ./install.sh
AI_ANALYZER_PYPI=aliyun bash ./install.sh
```

默认同样自动回退镜像。

## 自动安装脚本会做什么

自动脚本不会修改你的 FL Studio 工程，只处理运行环境：

- 安装 `AI Audio Analyzer.vst3`；
- 把 `mcp/` 和 `skill/` 复制到稳定的用户应用数据目录；
- 检测 Python 3.10+，优先使用 Python 3.12；
- 创建 Analyzer MCP 专用虚拟环境；
- 从 `requirements.txt` 安装 `mcp>=2,<3`、`python-osc` 等依赖；
- 自动尝试多个 PyPI 源；
- 验证 MCP Python 导入并检查 `server.py`；
- 自动生成绝对路径版 `cherry-studio-mcp.json`；
- 输出 Cherry Studio Skill 所在目录。

脚本**不会直接修改 Cherry Studio 自己的配置文件**，因为 Cherry Studio 不同版本的配置位置和格式可能变化。它会生成一个已经填好绝对路径的配置片段，你复制或在界面中填写即可。

## Python 安装问题

Analyzer MCP 需要 **Python 3.10 或更高版本**。懒人安装器推荐 Python 3.12，兼容性更稳。

### Windows

脚本依次检测：

```text
py -3.12
py -3
python
python3
```

如果没有兼容 Python，并且系统有 `winget`，脚本会自动执行：

```powershell
winget install -e --id Python.Python.3.12 --scope user
```

手动安装可选：

- Python 官方：https://www.python.org/downloads/windows/
- winget：`winget install -e --id Python.Python.3.12 --scope user`

手动安装 Python 时，建议保留 Python Launcher（`py`）。

### macOS

脚本检测 `python3.12`、`python3`、`python`。

如果没有合适 Python，但已经安装 Homebrew，则自动使用：

```bash
brew install python@3.12
```

如果 Python 和 Homebrew 都没有，交互式安装器会询问是否安装 Homebrew；你也可以拒绝，改为手动从 Python 官网安装。

手动安装：

- Python 官方：https://www.python.org/downloads/macos/
- Homebrew：https://brew.sh/

## Python 本体和 PyPI 镜像不是一回事

这是最容易混淆的地方：

- **Python 本体**：运行 `server.py` 的解释器；
- **PyPI**：pip 下载 `mcp`、`python-osc` 等第三方包的服务器。

懒人包不会直接内置一个 Python 二进制，避免安装包过大、Python 安全更新滞后和平台签名问题。Windows 优先通过 winget 安装 Python 3.12；macOS 优先复用现有 Python 或 Homebrew Python。

pip 支持：

```text
官方      https://pypi.org/simple
清华 TUNA https://pypi.tuna.tsinghua.edu.cn/simple
阿里云    https://mirrors.aliyun.com/pypi/simple/
```

手动测试官方源：

```bash
python -m pip install -r requirements.txt -i https://pypi.org/simple
```

清华源：

```bash
python -m pip install -r requirements.txt \
  -i https://pypi.tuna.tsinghua.edu.cn/simple
```

阿里云：

```bash
python -m pip install -r requirements.txt \
  -i https://mirrors.aliyun.com/pypi/simple/
```

不建议为了这个项目直接永久修改全局 pip 镜像，否则会影响你电脑上的其他 Python 工程。

如果报错是 SSL / Certificate / Proxy，尤其是公司或学校网络，那么可能是 HTTPS 代理证书问题，不一定是 PyPI 访问速度问题。不要用关闭 TLS 验证的方式硬绕过，应使用网络环境要求的 CA / Proxy 配置。

# Windows 手动安装

## 1. 安装 VST3

把：

```text
AI Audio Analyzer.vst3
```

复制到：

```text
C:\Program Files\Common Files\VST3\
```

然后**完全退出并重新打开 FL Studio**，再进行插件重新扫描。

## 2. 安装 / 检查 Python

检查：

```powershell
py -3.12 --version
```

或者：

```powershell
python --version
```

必须是 Python 3.10+。

## 3. 创建 MCP 虚拟环境

在懒人包目录中：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\mcp\requirements.txt
```

官方 PyPI 慢时：

```powershell
python -m pip install -r .\mcp\requirements.txt `
  -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 4. 配置 Cherry Studio

`command` 指向虚拟环境里的 `python.exe`，`args` 第一项指向 `mcp/server.py` 的绝对路径。

例如：

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

## 5. 导入 Skill

把包内的 `skill/` 文件夹导入 Cherry Studio。

# macOS 手动安装

## 1. 安装 VST3

推荐用户级目录：

```text
~/Library/Audio/Plug-Ins/VST3/
```

如果目录不存在：

```bash
mkdir -p "$HOME/Library/Audio/Plug-Ins/VST3"
```

然后把 `AI Audio Analyzer.vst3` 复制进去。

## 2. 解决 Gatekeeper / Quarantine

当前 GitHub Actions 生成的是 **ad-hoc 签名开发包，不是 Apple Developer ID + Notarization 正式公证包**。浏览器 / GitHub 下载后，macOS 可能给文件加上 `com.apple.quarantine`，FL Studio 会因此拒绝加载。

执行：

```bash
xattr -dr com.apple.quarantine \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

检查签名：

```bash
codesign --verify --deep --strict --verbose=4 \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

如果你在本地修改 / 解压过程中破坏了 ad-hoc 签名，可重新签一次：

```bash
codesign --force --deep --sign - --timestamp=none \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

然后再次执行 `xattr -dr`，完全退出 FL Studio，重新打开后强制扫描插件。

## 3. 安装 Python / MCP

Homebrew 方案：

```bash
brew install python@3.12
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r ./mcp/requirements.txt
```

清华镜像：

```bash
python -m pip install -r ./mcp/requirements.txt \
  -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 4. 配置 Cherry Studio

例如：

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

## 5. 导入 Skill

把 `skill/` 导入 Cherry Studio。

# 常见故障

## FL Studio 扫不到插件

确认 VST3 Bundle 本体直接放在扫描目录，而不是外面又多套了一层 ZIP 解压目录。

macOS 正确结构：

```text
~/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3/Contents/...
```

Windows 正确结构：

```text
C:\Program Files\Common Files\VST3\AI Audio Analyzer.vst3\Contents\...
```

之后完全重启 FL Studio 并强制重新扫描。

## Cherry Studio 显示 `Connection closed`

先把 Cherry Studio 中的同一条 MCP 命令复制到终端运行，查看真实 traceback。

常见原因：

- Cherry Studio 指向了错误 Python；
- 依赖装到了另一个 Python 环境；
- 已经有另一个 Analyzer Bridge 占用了 UDP `9855`；
- 使用了旧版 MCP v1 `server.py`。

当前 Bridge 要求 MCP Python SDK 2.x，可修复：

```bash
python -m pip install -U "mcp>=2,<3" python-osc
```

不要终端里手动常驻一个 `server.py`，同时又让 Cherry Studio 再启动一个。

## 报 `No module named mcp.server.fastmcp`

这是旧 MCP v1 Bridge / Import。请换成当前 Release 的 `mcp/` 文件夹，并重新安装：

```bash
python -m pip install -U "mcp>=2,<3" python-osc
```

## MCP 正常，但 `audio_list_tracks()` 为空

检查：

- FL Mixer Track 上是否确实插入 `AI Audio Analyzer`；
- 需要测量时 FL Studio 是否正在处理音频；
- 插件 OSC Host 是否是 `127.0.0.1`；
- 插件和 Bridge 是否都使用 UDP `9855`；
- 是否有第二个 Bridge 进程抢占端口。

## 一个工程有很多 Analyzer

所有实例共用同一个 UDP `9855` 是正常设计，不需要每个插件单独开端口。

使用 0.4 的 `Identify` 流程，让 FL Studio MCP 把 Runtime UUID 确定绑定到 Mixer Track/Slot。

配套项目：

https://github.com/rosasynthesiz/flstudio-mcp
