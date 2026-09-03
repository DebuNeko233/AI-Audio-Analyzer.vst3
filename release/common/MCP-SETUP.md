# AI Audio Analyzer — Add MCP to an Agent / 把 MCP 加入 Agent

The installer already installs the standalone MCP executable and generates a ready-to-use `cherry-studio-mcp.json` with the correct absolute path for your computer.

**Prefer the generated JSON.** The examples below are mainly for understanding the format or configuring another MCP-compatible Agent/client manually.

---

## English

### 1. Run the installer first

Windows:

```text
Install.cmd
```

macOS Apple Silicon:

```text
Install.command
```

After installation, the Analyzer MCP runtime is located under:

Windows:

```text
%LOCALAPPDATA%\AI Audio Analyzer\mcp\ai-audio-analyzer-mcp.exe
```

macOS:

```text
~/Library/Application Support/AI Audio Analyzer/mcp/ai-audio-analyzer-mcp
```

The installer also creates:

```text
cherry-studio-mcp.json
```

in the AI Audio Analyzer application-data folder and prints its exact location when installation finishes.

### 2. Add the MCP server to your Agent/client

Open the MCP server settings of Cherry Studio or another MCP-compatible Agent/client. Import the generated `cherry-studio-mcp.json`, or add an MCP server named `ai-audio-analyzer` using the same `command`, `args`, and `env` fields.

Then enable/select this MCP server for the Assistant/Agent that will use AI Audio Analyzer. The exact button names can vary by client version, but the resulting configuration must contain an `mcpServers` entry like the examples below.

### Windows JSON example

Replace `YOUR_NAME` if you are writing the configuration manually. The installer-generated JSON already contains the real absolute path, so no replacement is needed when you use that file.

```json
{
  "mcpServers": {
    "ai-audio-analyzer": {
      "command": "C:\\Users\\YOUR_NAME\\AppData\\Local\\AI Audio Analyzer\\mcp\\ai-audio-analyzer-mcp.exe",
      "args": [],
      "env": {
        "AI_ANALYZER_OSC_HOST": "127.0.0.1",
        "AI_ANALYZER_OSC_PORT": "9855"
      }
    }
  }
}
```

### macOS JSON example

Replace `YOUR_NAME` if you are writing the configuration manually.

```json
{
  "mcpServers": {
    "ai-audio-analyzer": {
      "command": "/Users/YOUR_NAME/Library/Application Support/AI Audio Analyzer/mcp/ai-audio-analyzer-mcp",
      "args": [],
      "env": {
        "AI_ANALYZER_OSC_HOST": "127.0.0.1",
        "AI_ANALYZER_OSC_PORT": "9855"
      }
    }
  }
}
```

### 3. Add the Skill to the same Agent

The installer also installs the `skill` folder. Import that folder into Cherry Studio or make its instructions available to the same Agent that has the `ai-audio-analyzer` MCP server enabled.

The MCP provides the tools. The Skill teaches the LLM how to call those tools, interpret measurement validity, choose the minimum Analysis Profile needed, and perform controlled Before/After verification.

### 4. Verify the Agent can see the tools

After enabling the MCP server, start or refresh the Agent session. The AI Audio Analyzer MCP currently exposes 29 tools. A useful first call is:

```text
audio_project_status()
```

If the Agent cannot see the Analyzer tools:

1. confirm the installer completed successfully;
2. confirm the `command` path points to the installed `ai-audio-analyzer-mcp` executable;
3. confirm the MCP server is enabled for the current Agent/Assistant;
4. restart or refresh the MCP client after changing its configuration;
5. make sure another AI Audio Analyzer MCP process is not already occupying the same local OSC endpoint.

Do not point a normal Release configuration at Python source files. The Release contains a standalone one-file MCP executable and does not require Python.

---

## 中文

### 1. 先运行安装器

Windows：双击：

```text
Install.cmd
```

macOS Apple Silicon：双击：

```text
Install.command
```

安装后 MCP 程序位于：

Windows：

```text
%LOCALAPPDATA%\AI Audio Analyzer\mcp\ai-audio-analyzer-mcp.exe
```

macOS：

```text
~/Library/Application Support/AI Audio Analyzer/mcp/ai-audio-analyzer-mcp
```

安装器还会在 AI Audio Analyzer 的应用数据目录中自动生成：

```text
cherry-studio-mcp.json
```

并在安装完成时打印它的准确位置。

### 2. 把 MCP 加到 Agent / MCP 客户端

打开 Cherry Studio 或其他支持 MCP 的 Agent/客户端的 MCP Server 设置。优先直接导入安装器生成的 `cherry-studio-mcp.json`；也可以手动新建一个名为 `ai-audio-analyzer` 的 MCP Server，并填写相同的 `command`、`args` 和 `env`。

然后把这个 MCP Server **启用/分配给实际要使用 AI Audio Analyzer 的 Assistant/Agent**。不同版本客户端的按钮名称可能不同，但最终配置结构应包含下面这样的 `mcpServers` 项。

### Windows JSON 示例

如果手动填写，把 `YOUR_NAME` 换成你的 Windows 用户名。直接使用安装器生成的 JSON 时不需要修改，它已经写入真实绝对路径。

```json
{
  "mcpServers": {
    "ai-audio-analyzer": {
      "command": "C:\\Users\\YOUR_NAME\\AppData\\Local\\AI Audio Analyzer\\mcp\\ai-audio-analyzer-mcp.exe",
      "args": [],
      "env": {
        "AI_ANALYZER_OSC_HOST": "127.0.0.1",
        "AI_ANALYZER_OSC_PORT": "9855"
      }
    }
  }
}
```

### macOS JSON 示例

手动填写时把 `YOUR_NAME` 换成你的 macOS 用户名。

```json
{
  "mcpServers": {
    "ai-audio-analyzer": {
      "command": "/Users/YOUR_NAME/Library/Application Support/AI Audio Analyzer/mcp/ai-audio-analyzer-mcp",
      "args": [],
      "env": {
        "AI_ANALYZER_OSC_HOST": "127.0.0.1",
        "AI_ANALYZER_OSC_PORT": "9855"
      }
    }
  }
}
```

### 3. 把 Skill 加给同一个 Agent

安装器也会安装 `skill` 文件夹。把这个 Skill 导入 Cherry Studio，或让同一个已经启用 `ai-audio-analyzer` MCP 的 Agent 可以读取它。

MCP 提供工具；Skill 告诉 LLM 应该怎样调用工具、怎样判断测量是否有效、怎样选择最低需要的 Analysis Profile，以及怎样做 Before/After 闭环验证。

### 4. 检查 Agent 是否已经看到工具

启用 MCP 后，重新打开或刷新 Agent 会话。当前 AI Audio Analyzer MCP 共提供 29 个工具，建议先尝试：

```text
audio_project_status()
```

如果 Agent 看不到 Analyzer 工具：

1. 确认安装器确实显示安装成功；
2. 确认 JSON 的 `command` 指向安装后的 `ai-audio-analyzer-mcp` 可执行文件；
3. 确认这个 MCP Server 已经启用给当前 Agent/Assistant；
4. 修改 MCP 配置后重启或刷新客户端；
5. 确认电脑上没有另一个 AI Audio Analyzer MCP 进程正在占用同一个本地 OSC 端点。

普通 Release 不需要 Python，也不要把 Agent 配置指向仓库里的 Python 源码。懒人包使用的是已经打包好的单文件 MCP 程序。
