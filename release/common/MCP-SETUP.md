# AI Audio Analyzer — Add MCP to an Agent / 把 MCP 加入 Agent

The installer installs the standalone MCP executable and generates `cherry-studio-mcp.json` with the correct absolute path for your computer.

**Prefer the generated JSON.** The examples below are only for manual configuration or understanding the format.

---

## English

### 1. Run the installer

Windows:

```text
Install.cmd
```

macOS Apple Silicon:

```text
Install.command
```

Installed MCP runtime:

```text
Windows:
%LOCALAPPDATA%\AI Audio Analyzer\mcp\ai-audio-analyzer-mcp.exe

macOS:
~/Library/Application Support/AI Audio Analyzer/mcp/ai-audio-analyzer-mcp
```

The installer also creates `cherry-studio-mcp.json` in the AI Audio Analyzer application-data folder and prints its location.

### 2. Add the MCP server to the Agent/client

Import the generated JSON into Cherry Studio or another MCP-compatible client, then enable/select the `ai-audio-analyzer` server for the Agent that will use the Analyzer.

Manual Windows example:

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

Manual macOS example:

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

Import the packaged `skill` folder into the same Agent/Assistant that has `ai-audio-analyzer` enabled.

The MCP provides tools. The Skill teaches the model how to use deterministic bindings, Analysis Profiles, Song Memory, Section Map, Track Story, Section-aware Relationships, data-quality evidence, and both verification modes safely.

### 4. Verify the tool surface

AI Audio Analyzer MCP 1.2 exposes **41 tools**.

Useful first call:

```text
audio_project_status()
```

Whole-song/structure tools include:

```text
audio_song_status()
audio_section_map()
audio_track_story(...)
audio_section_profile(...)
audio_section_relationships(...)
```

For a real DAW change over a known passage, prefer transport-anchored same-range verification:

```text
audio_begin_range_verification(...)
-> external DAW-control write + actual host readback
-> replay returned effective_range
audio_complete_range_verification(...)
```

For cases where an explicit retained DAW-time range is not practical, the older recent-window verification tools remain available:

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

The Analyzer does not perform the sound-changing DAW write. All EQ, compression, gain, pan, routing, synth, automation and project changes remain the responsibility of the actual DAW-control MCP.

Analyzer-owned profile tools:

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

These may change only the Analyzer's own `Eco / Balanced / Mix / Full` measurement-performance profile. They do not alter audio.

If the Agent cannot see Analyzer tools:

1. confirm installation completed;
2. confirm the JSON `command` points to the installed executable;
3. confirm the MCP server is enabled for the current Agent;
4. refresh/restart the MCP client after configuration changes;
5. make sure another Analyzer MCP process is not already using the same local OSC measurement endpoint.

Do not configure a normal user Release to run repository Python source. The Release uses a standalone one-file executable and does not require Python.

---

## 中文

### 1. 先运行安装器

Windows：

```text
Install.cmd
```

macOS Apple Silicon：

```text
Install.command
```

安装后的 MCP Runtime：

```text
Windows:
%LOCALAPPDATA%\AI Audio Analyzer\mcp\ai-audio-analyzer-mcp.exe

macOS:
~/Library/Application Support/AI Audio Analyzer/mcp/ai-audio-analyzer-mcp
```

安装器会自动生成 `cherry-studio-mcp.json`，并打印文件位置。

### 2. 把 MCP Server 加到 Agent

优先直接导入安装器生成的 JSON，然后把 `ai-audio-analyzer` MCP Server 启用给实际要使用 Analyzer 的 Agent/Assistant。

手动 Windows 示例：

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

手动 macOS 示例：

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

### 3. 给同一个 Agent 导入 Skill

把 Release 里的 `skill` 文件夹导入给同一个已启用 `ai-audio-analyzer` MCP 的 Agent。

Skill 会告诉 LLM 怎样使用确定性 Binding、Analysis Profile、Song Memory、Section Map、Track Story、Section-aware Relationships、数据质量字段和两种 Verification 模式。

### 4. 检查工具是否可见

当前 AI Audio Analyzer MCP 1.2 共 **41 个工具**。

建议先调用：

```text
audio_project_status()
```

整曲/结构工具包括：

```text
audio_song_status()
audio_section_map()
audio_track_story(...)
audio_section_profile(...)
audio_section_relationships(...)
```

如果要验证一个已知歌曲时间范围上的真实 DAW/插件修改，优先使用：

```text
audio_begin_range_verification(...)
-> 外部 DAW-control MCP 修改并回读真实状态
-> 重放返回的 effective_range
audio_complete_range_verification(...)
```

如果不方便指定明确的 Retained DAW-time Range，旧的 Recent-window Verification 仍可使用。

Analyzer MCP 不执行 EQ、Compression、Gain、Pan、Routing、Synth、Automation 或工程修改。这些操作仍属于真正的 DAW-control MCP。

Analyzer 自己只允许修改测量负载：

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

它们只修改 `Eco / Balanced / Mix / Full` Analysis Profile，不改变音频信号。

如果 Agent 看不到工具，请检查安装是否成功、JSON `command` 是否指向已安装的单文件 MCP 程序、MCP Server 是否启用，以及是否有另一个 Analyzer MCP 已占用本机 OSC 端口。

普通 Release 不需要 Python，也不要把配置指向仓库 Python 源码。
