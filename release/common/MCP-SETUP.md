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

Import the generated JSON into Cherry Studio or another MCP-compatible client, then enable/select the `ai-audio-analyzer` server for the Agent that will use Analyzer.

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

AI Audio Analyzer MCP is self-describing. A client does **not** have to import the packaged Skill for the basic server contract.

The MCP exposes:

```text
Server instructions
47 Tool descriptions
16 MCP Resources under aianalyzer://guide/*
```

The packaged `skill` folder remains the canonical long-form guide content used by those MCP Resources.

If the client supports Resources, read:

```text
aianalyzer://guide/index
```

and then only the relevant guide. Useful specialized Resources include:

```text
aianalyzer://guide/dynamics-evidence
aianalyzer://guide/mono-compatibility
aianalyzer://guide/reference-comparison
aianalyzer://guide/verification-evidence
```

If the client does not expose MCP Resources, importing the packaged `skill` folder into the Agent/Assistant is the preferred way to provide the same long-form guidance.

### 4. Verify identity scope and tool surface

AI Audio Analyzer MCP 1.2 exposes **47 tools**.

First call at a new session or after a possible project switch/reopen:

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

Reopening the same FL Studio project recreates Analyzer runtime UUIDs. A new UUID therefore does not prove that another project was opened.

If Analyzer MCP keeps running through a project switch/reopen, old Song Memory, Section Maps, snapshots, relationships, P8a references or verification sessions may remain in RAM and are not partitioned by a stable Project ID.

Until exact DAW project identity is integrated, restart Analyzer MCP after changing/reopening projects when strict state isolation is required.

Then inspect current readiness:

```text
audio_project_status()
audio_song_status()
```

High-level whole-song/structure tools include:

```text
audio_section_map()
audio_track_story(...)
audio_section_profile(...)
audio_section_relationships(...)
```

### 5. Dynamics, mono and reference evidence

Retained dynamics:

```text
audio_dynamics_distribution(...)
```

Do not interpret `lufs_s_interpercentile_range_lu` as EBU Loudness Range. P6a leaves standardized EBU LRA, arbitrary-range Integrated LUFS and arbitrary-range PLR unavailable.

Recent mono compatibility:

```text
audio_mono_compatibility(track, seconds=5.0)
```

`inspection_priority` is an energy-aware shortlist aid, not a quality score, audibility probability, pass/fail result, or processing instruction. Historical arbitrary Section 32-band mono evidence and direct mono-fold Sample Peak/True Peak are unavailable in P7a.

Session reference comparison:

```text
audio_capture_reference(track, label="", seconds=10.0)
audio_list_references()
audio_compare_reference(reference_id, target, seconds=None)
```

P8a references are frozen compact measurement profiles only. No source audio is stored.

Current scope:

```text
recent receive-time window
MCP-session scoped
not persistent
not a whole-song claim
```

Comparison direction is `target - reference`. The spectral result also includes an explicit RMS-level-normalized shape view. That normalization is only a comparison view and does not change the audio.

Do not convert reference deltas directly into inverse EQ/master-matching commands. A difference from the reference is context, not automatically a defect.

### 6. Verify real DAW changes

For a real DAW change over a known passage, prefer transport-anchored same-range verification:

```text
audio_begin_range_verification(...)
-> external DAW-control write + actual host readback
-> replay returned effective_range
audio_complete_range_verification(...)
```

When explicit retained range anchoring is impractical, recent-window verification remains available:

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

Neither verification path establishes persistent project identity.

The Analyzer does not perform sound-changing DAW writes. EQ, compression, gain, pan, routing, synth, automation and project changes remain the responsibility of the actual DAW-control MCP.

Analyzer-owned profile tools:

```text
audio_set_analysis_profile(track, profile)
audio_set_project_analysis_profile(profile, tracks=None)
```

These may change only Analyzer's own `Eco / Balanced / Mix / Full` measurement-performance profile and do not alter audio.

### 7. Troubleshooting

If the Agent cannot see Analyzer tools:

1. confirm installation completed;
2. confirm the generated JSON `command` points to the installed executable;
3. confirm the MCP server is enabled for the current Agent;
4. refresh/restart the MCP client after configuration changes;
5. make sure another Analyzer MCP process is not already using the same local OSC endpoint.

Do not configure a normal user Release to run repository Python source. The Release uses a standalone PyInstaller `-F` one-file executable and does not require Python.

---

## 中文

### 1. 运行安装程序

Windows：双击 `Install.cmd`。

macOS Apple Silicon：双击 `Install.command`。

安装程序会安装单文件 MCP 运行时，并生成带正确绝对路径的 `cherry-studio-mcp.json`。

### 2. 把 MCP 加入 Agent

优先把安装程序生成的 JSON 导入 Cherry Studio 或其他 MCP 客户端，并为需要使用 Analyzer 的 Agent 启用 `ai-audio-analyzer`。

普通用户不需要 Python、pip、venv 或仓库源码。

### 3. Skill 不是基本使用的前置条件

MCP 自带 Server Instructions、47 个 Tool Description 和 16 个 `aianalyzer://guide/*` Resources。

如果客户端支持 Resource，可以先读 `aianalyzer://guide/index`，然后只加载当前任务需要的 Guide。Reference Comparison 的专用 Guide 是：

```text
aianalyzer://guide/reference-comparison
```

如果客户端不支持 Resource，可以导入安装包里的 `skill` 目录。

### 4. 新 Session 先检查 Identity

```text
audio_project_identity_status()
```

当前没有可信的稳定 Project ID。Runtime UUID 是当前插件实例身份，不是持久 Project/Track ID。

如果切换或重新打开工程并需要严格隔离历史状态，应重启 Analyzer MCP。

### 5. P8a Reference Comparison

```text
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
```

当前 Reference 是冻结的 Recent-window 测量 Profile，只存在于当前 MCP Session 中，不保存原始音频，也不能声称 Whole-song Coverage。

Reference 差异只是上下文，不是自动 EQ / Master Match 配方。

### 6. 真实声音修改仍由 DAW-control MCP 执行

Analyzer MCP 只允许修改自己的 `Analysis Profile`。真实 EQ、Compression、Gain、Pan、Routing、Synth、Automation 和工程修改必须由外部 DAW-control MCP 完成，并在需要时用 Analyzer 做 Before/After 验证。