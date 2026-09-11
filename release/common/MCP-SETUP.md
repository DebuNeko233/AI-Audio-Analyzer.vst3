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

### 2. Add the MCP server

Import the generated JSON into Cherry Studio or another MCP-compatible client, then enable the `ai-audio-analyzer` server for the Agent that will use Analyzer.

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

AI Audio Analyzer MCP is self-describing through:

```text
Server instructions
48 Tool descriptions
16 MCP Resources under aianalyzer://guide/*
```

The packaged `skill/` directory remains the canonical long-form Markdown source used by those Resources.

If your client supports Resources, start with:

```text
aianalyzer://guide/index
```

and load only the guide needed for the task.

### 4. Start with identity scope

At a new session, or after a possible project switch/reopen, first call:

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

Reopening the same project recreates Analyzer runtime UUIDs. A new UUID does not prove another project opened.

If strict retained-state isolation matters after changing/reopening a project, restart Analyzer MCP until authoritative project identity is integrated.

Then inspect:

```text
audio_project_status()
audio_song_status()
```

### 5. Whole-song and historical evidence

High-level tools include:

```text
audio_song_overview()
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
audio_historical_detail(...)
audio_dynamics_distribution(...)
audio_mono_compatibility(...)
```

Use `audio_historical_detail()` for a retained past DAW range or cached Section when replay should be avoided.

P4b historical detail can expose one-second retained Mid/Side, stereo, historical mono energy, masking and temporal-pair evidence when those features were measured during capture.

Important limits:

```text
historical resolution        1 second
subsecond historical align   unsupported
raw audio retained           no
missing detail               unavailable, not silence
mono Sample Peak/True Peak   unavailable
```

Dedicated masking/stereo/temporal tools remain recent-window APIs with potentially finer current-frame context.

### 6. Dynamics, mono and references

Retained dynamics:

```text
audio_dynamics_distribution(...)
```

P6a is descriptive. LUFS-S P90-P10 is not standardized EBU LRA. Arbitrary-range Integrated LUFS and PLR remain unavailable.

Recent mono compatibility:

```text
audio_mono_compatibility(track, seconds=5.0)
```

Historical one-second mono energy is available separately through `audio_historical_detail()` when retained Mid/Side detail exists. Direct mono-fold Sample Peak/True Peak remain unavailable.

Session reference comparison:

```text
audio_capture_reference(track, label="", seconds=10.0)
audio_list_references()
audio_compare_reference(reference_id, target, seconds=None)
```

P8a references are frozen compact **recent-window** measurement profiles. No source audio is stored. They are MCP-session scoped, not persistent and not whole-song truth.

P4b does not silently convert P8a references into historical reference captures.

Reference differences are context, not automatic EQ/master-match commands.

### 7. Verify real DAW changes

For a real change over a known passage, prefer:

```text
audio_begin_range_verification(...)
-> external DAW-control write
-> actual host readback
-> replay returned effective_range
-> audio_complete_range_verification(...)
```

When explicit retained range anchoring is unnecessary, recent-window verification remains available.

`controlled_comparison=true` means technical comparability only. `closed_loop_complete=true` additionally requires actual host readback. Neither means the result sounds better.

Analyzer-owned profile tools may change only Analyzer's own `Eco / Balanced / Mix / Full` measurement profile. All sound/project writes remain external.

### 8. Troubleshooting

If the Agent cannot see Analyzer tools:

1. confirm installation completed;
2. confirm generated JSON points to the installed executable;
3. confirm the MCP server is enabled for the current Agent;
4. refresh/restart the MCP client after configuration changes;
5. make sure another Analyzer MCP process is not already using `127.0.0.1:9855`.

Normal user Releases run the standalone PyInstaller `-F` executable and do not require Python.

---

## 中文

### 1. 运行安装程序

Windows：双击 `Install.cmd`。

macOS Apple Silicon：双击 `Install.command`。

安装程序会安装单文件 MCP Runtime，并生成带正确绝对路径的 `cherry-studio-mcp.json`。

### 2. 把 MCP 加入 Agent

优先导入安装程序生成的 JSON，并为需要使用 Analyzer 的 Agent 启用 `ai-audio-analyzer`。

普通用户不需要 Python、pip、venv 或仓库源码。

### 3. MCP 可以自解释

当前 P4b PR #36 的 MCP 1.2 提供：

```text
Server Instructions
48 个 Tool Descriptions
16 个 aianalyzer://guide/* Resources
```

如果客户端支持 Resource，先读取 `aianalyzer://guide/index`，然后只加载当前任务需要的 Guide。`skill/` 目录仍是长篇指导文档的规范来源。

### 4. 新 Session 先检查 Identity

```text
audio_project_identity_status()
```

当前没有可信的稳定 Project ID。Runtime UUID 是当前插件实例身份，不是持久 Project/Track ID。

如果切换或重新打开工程后需要严格隔离历史状态，应重启 Analyzer MCP。

### 5. 历史 Section / DAW 区间

```text
audio_historical_detail(...)
```

P4b 可以在不重播的情况下查询已经保留下来的 1 秒级 Mid/Side、Stereo、历史 Mono 能量、Masking 和 Temporal pair 证据。

必须明确：历史分辨率只有 1 秒；不支持亚秒历史对齐；缺失数据不是静音；Mono Sample Peak / True Peak 仍不可用。

近期窗口 `audio_masking_evidence()`、`audio_stereo_profile()`、`audio_temporal_*()` 仍是另一类更细的当前帧工具，不能冒充历史 Section 结果。

### 6. Reference 仍是 Recent-window

P8a：

```text
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
```

Reference 是冻结的近期窗口测量 Profile，只存在于当前 MCP Session 中，不保存源音频，也不能代表整首歌。

P4b 有历史深度数据，并不表示 P8a 已经支持历史 Reference Capture。

### 7. 真实声音修改仍由 DAW-control MCP 执行

Analyzer MCP 只允许修改自己的 `Analysis Profile`。真实 EQ、Compression、Gain、Pan、Routing、Synth、Automation 和工程修改必须由外部 DAW-control MCP 完成，并在需要时用 Analyzer 做 Before/After 验证。
