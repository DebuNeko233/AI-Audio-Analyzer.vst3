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

### 3. Skill import is optional

AI Audio Analyzer MCP is self-describing. A client does **not** have to import the packaged Skill in order to understand the basic server contract.

The MCP exposes:

```text
Server instructions
42 Tool descriptions
MCP Resources under aianalyzer://guide/*
```

The packaged `skill` folder remains important because its `SKILL.md` and `references/*.md` are the canonical long-form guide content used by those MCP Resources.

If the client supports MCP Resources, it can read:

```text
aianalyzer://guide/index
```

and then load only the relevant guide for the current task. Do not load every guide mechanically.

If the client does not expose MCP Resources, importing the packaged `skill` folder into that Agent/Assistant is the preferred way to provide the same long-form professional guidance.

If the physical `skill` directory is missing, Server instructions and Tool descriptions still provide the minimum self-description, but detailed guide Resources are unavailable.

### 4. Verify the tool surface and identity scope

AI Audio Analyzer MCP 1.2 exposes **42 tools**.

First call at a new session or after a possible DAW project switch/reopen:

```text
audio_project_identity_status()
```

Current expected identity scope:

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id scope                        live_plugin_instance
runtime_id persistent                   false
same-project reopen UUID stable         false
binding scope                           mcp_session
cross-project retained-state isolation  not guaranteed
```

Important: reopening the same FL Studio project recreates Analyzer runtime UUIDs. A new UUID therefore does not prove that a different project was opened. If Analyzer MCP keeps running while the user switches/reopens projects, old Song Memory, Section Maps, snapshots, relationships or verification sessions may still exist in MCP RAM and are not yet partitioned by a stable Project ID.

Until exact DAW project identity is integrated, restart Analyzer MCP after changing/reopening projects when strict state isolation is required.

Then inspect current-session readiness:

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

Neither verification path establishes persistent project identity. Do not continue an old verification across a suspected project switch/reopen without authoritative external identity or a clean MCP restart.

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

### 3. Skill 导入现在是可选增强

AI Audio Analyzer MCP 本身具备 Self-Describing API。即使没有把 `skill` 手动导入客户端，调用方仍可以通过：

```text
Server instructions
42 个 Tool description
MCP Resources: aianalyzer://guide/*
```

理解 MCP 的基本调用顺序和关键限制。

Release 里的 `skill` 文件夹仍然会保留，因为它有两个用途：

1. 给支持 Skill 的客户端做可选导入；
2. 作为 MCP Guide Resources 的 canonical Markdown 内容源。

如果客户端支持 MCP Resources，可以先读：

```text
aianalyzer://guide/index
```

再按当前任务只读取需要的 Guide，不要一次性加载全部 Guide。

如果客户端不支持 MCP Resources，则建议把 Release 里的 `skill` 文件夹导入给同一个 Agent，以获得完整的长篇专业说明。

如果物理 `skill` 目录缺失，Server instructions 与 Tool descriptions 仍可以提供最低限度的自解释能力，但详细 Guide Resources 不可用。

### 4. 检查工具和工程身份范围

当前 AI Audio Analyzer MCP 1.2 共 **42 个工具**。

新会话开始时，或用户可能切换/重新打开了工程时，先调用：

```text
audio_project_identity_status()
```

当前会明确告诉调用方：

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id scope                        live_plugin_instance
runtime_id persistent                   false
same-project reopen UUID stable         false
binding scope                           mcp_session
cross-project retained-state isolation  not guaranteed
```

重新打开**同一个 FL Studio 工程**也会重新生成 Analyzer Runtime UUID，所以新的 UUID 不能证明“工程已经变了”。如果 MCP 一直运行，上一个工程的 Song Memory、Section Map、Snapshot、Relationship、Verification 等状态也可能继续存在于 MCP RAM 中，目前还没有 Stable Project ID 自动分区。

在后续接入可信 Project Identity 之前，如果需要严格隔离，切换或重新打开工程后请重启 Analyzer MCP。

然后再检查当前 Session：

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

两种 Verification 都不能证明 Persistent Project Identity；怀疑已经切换/重开工程时，不要把旧 Verification Session 直接续用到新状态。

Analyzer MCP 不执行 EQ、Compression、Gain、Pan、Routing、Synth、Automation 或工程修改。这些操作仍属于真正的 DAW-control MCP。

Analyzer 自己只允许修改测量负载：

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

它们只修改 `Eco / Balanced / Mix / Full` Analysis Profile，不改变音频信号。

如果 Agent 看不到工具，请检查安装是否成功、JSON `command` 是否指向已安装的单文件 MCP 程序、MCP Server 是否启用，以及是否有另一个 Analyzer MCP 已占用本机 OSC 端口。

普通 Release 不需要 Python，也不要把配置指向仓库 Python 源码。