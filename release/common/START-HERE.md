# AI Audio Analyzer 1.2 — Start Here / 从这里开始

[English guide](INSTALL.en.md) | [中文教程](INSTALL.zh-CN.md) | [Agent / MCP setup](MCP-SETUP.md)

This Release is designed for users with no Python or programming experience. **Unzip the downloaded package once**, then run the installer inside.

## Windows

1. Download the file ending in `Windows.zip`.
2. Right-click it and choose **Extract All**.
3. Open the extracted folder.
4. Double-click `Install.cmd`.
5. Approve the permission prompt if Windows shows one.
6. Wait for **Installation completed successfully**.
7. Restart FL Studio and rescan plugins if needed.
8. Follow `MCP-SETUP.md` to add the generated MCP configuration to the Agent/Assistant that will use Analyzer.
9. Optional: import the packaged `skill` folder if the client supports Skills or does not expose MCP Resources.

## macOS Apple Silicon

1. Download the file ending in `macOS.zip`.
2. Double-click it to extract it.
3. Open the extracted folder.
4. Double-click `Install.command`.
5. If macOS blocks it, right-click `Install.command` and choose **Open**.
6. Wait for the installer to report success.
7. Restart FL Studio and rescan plugins if needed.
8. Follow `MCP-SETUP.md` to add Analyzer MCP to the Agent.
9. Optional: import the packaged `skill` folder if the client benefits from client-side Skill loading.

Current macOS Release supports **Apple Silicon arm64 only**. It is ad-hoc signed, not Apple Developer ID notarized.

## What is inside

```text
AI Audio Analyzer.vst3
mcp/                         standalone one-file MCP executable
skill/                       canonical long-form MCP guides + optional client Skill
Install.cmd / Install.ps1    Windows installer
Install.command / install.sh macOS installer
START-HERE.md
MCP-SETUP.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
LICENSE
```

The user Release contains **no MCP Python source**, `requirements.txt`, venv, PyInstaller `_internal`, developer source config, or nested Release ZIP.

The installer generates `cherry-studio-mcp.json` with the correct absolute path to the installed MCP executable.

## The MCP can explain itself

AI Audio Analyzer MCP does not require a client-imported Skill for basic correct use.

It exposes:

```text
Server instructions
42 Tool descriptions
MCP Resources under aianalyzer://guide/*
```

If the client supports MCP Resources, it can read `aianalyzer://guide/index` and then only the guide needed for the current task.

The packaged `skill/` directory remains the canonical Markdown source for those detailed Resources. Importing it directly into a Skill-capable client is optional and is especially useful when that client does not expose MCP Resources.

## What the Agent can do

MCP 1.2 exposes **42 tools** for measurement and evidence workflows, including:

```text
project/runtime identity-scope disclosure
Song Memory
explainable Section Map
Track Story
Section-aware Mix Relationships
Analysis Profile control
recent-window verification
transport-anchored same-range verification
```

At the beginning of a new session, and whenever you may have switched or reopened an FL Studio project, the Agent should first call:

```text
audio_project_identity_status()
```

Current limitation: Analyzer runtime UUIDs identify live plugin instances only. They are not saved as persistent project/track IDs, and reopening the **same** project creates new runtime UUIDs. The MCP also does not yet have a stable FL Studio Project ID, so retained Song Memory, Section Maps, snapshots, relationships and verification sessions are not guaranteed to be isolated across project switches while MCP keeps running.

Until exact project identity is integrated, **restart Analyzer MCP after changing or reopening projects when strict state isolation is required**. A new runtime UUID alone does not prove that a different project was opened.

When verifying a real DAW/plugin change over a known musical passage, the Agent can use:

```text
audio_begin_range_verification(...)
-> external DAW-control write + actual host readback
-> replay returned effective_range
audio_complete_range_verification(...)
```

This compares the same retained DAW-time range before and after. The range is normalized to one-second Song Memory bins, different Analyzer instances may use different local transport epochs, and pre-change memory cannot silently be reused as the After pass.

`controlled_comparison=true` means only that technical comparability checks passed. `closed_loop_complete=true` additionally requires actual caller-supplied host readback. Neither means the change sounds better or establishes persistent project identity.

A/B/C section families are not automatic Verse/Chorus/Drop labels. Track Story does not infer Bass/Vocal/Drums roles. Relationship `shortlist_priority` is not a masking/mix-problem probability or processing instruction.

Analysis Profiles (`Eco`, `Balanced`, `Mix`, `Full`) affect Analyzer computation only. All sound-changing DAW/plugin writes still belong to the actual DAW-control MCP.

---

# 中文快速说明

这个 Release 按“**完全没接触过编程也能安装**”设计。你不需要安装 Python、pip 或开发环境。

## Windows

1. 下载 `Windows.zip`；
2. 右键 → **全部解压缩**；
3. 打开解压后的文件夹；
4. 双击 `Install.cmd`；
5. 等待显示 **Installation completed successfully**；
6. 重启 FL Studio，需要时重新扫描插件；
7. 按 `MCP-SETUP.md` 把安装器生成的 MCP 配置加入实际使用 Analyzer 的 Agent；
8. 可选：如果客户端支持 Skill，或者不支持 MCP Resources，再把 `skill` 文件夹导入给同一个 Agent。

## macOS Apple Silicon

1. 下载 `macOS.zip`；
2. 双击 ZIP 解压；
3. 打开文件夹并双击 `Install.command`；
4. 若 macOS 阻止运行，右键 `Install.command` → **打开**；
5. 等待安装成功；
6. 重启 FL Studio，需要时重新扫描插件；
7. 按 `MCP-SETUP.md` 配置 MCP；
8. 可选：按客户端能力决定是否导入同一个 `skill` 文件夹。

当前 macOS Release **只支持 Apple Silicon / arm64**。

安装器会生成包含真实 MCP 可执行文件绝对路径的 `cherry-studio-mcp.json`。

## MCP 本身可以告诉调用方怎么用

即使客户端没有手动导入 Skill，Analyzer MCP 仍会通过：

```text
Server instructions
42 个 Tool description
MCP Resources: aianalyzer://guide/*
```

提供基本调用顺序和关键限制。

如果客户端支持 MCP Resources，可以先读 `aianalyzer://guide/index`，再按任务读取需要的详细 Guide。Release 中的 `skill/` 仍然保留，因为它是这些 Guide Resources 的 canonical Markdown 内容源，同时也可以被支持 Skill 的客户端直接导入。

当前 MCP 1.2 共 **42 个工具**，包括 Project/Runtime Identity Scope、Song Memory、Section Map、Track Story、Section-aware Relationships、Analysis Profile Control，以及 Recent-window / Transport-anchored Same-range 两种验证路径。

新会话开始时，或者用户可能切换/重新打开了 FL Studio 工程时，Agent 应先调用：

```text
audio_project_identity_status()
```

当前 `runtime_id` 只是一次 Live Plugin Instance 的 UUID，不是永久工程/轨道身份；即使重新打开**同一个工程** UUID 也会变化。MCP 当前也没有可信 Stable Project ID，因此 MCP 一直运行时，上一个工程的 Song Memory、Section Map、Snapshot、Relationship、Verification 等状态还不能保证与新工程完全隔离。

在后续接入精确 Project Identity 之前，如果需要严格隔离，**切换或重新打开工程后重启 Analyzer MCP**。新的 Runtime UUID 本身不能证明工程已经切换。

对于已知的歌曲时间范围，优先使用：

```text
audio_begin_range_verification(...)
-> 外部 DAW-control MCP 修改并回读真实宿主状态
-> 重放返回的 effective_range
audio_complete_range_verification(...)
```

它会按同一个 DAW 时间范围比较 Before/After，并阻止把修改前旧 Song Memory 偷偷当成 After。

`controlled_comparison=true` 只表示技术可比性通过；`closed_loop_complete=true` 还要求真实 Host Readback。两者都不表示 After 在艺术上更好，也不证明 Persistent Project Identity。

A/B/C 不是自动 Verse/Chorus/Drop；Track Story 不自动判断轨道角色；Relationship Shortlist 也不是 Masking/Mix Problem 概率。

`Eco / Balanced / Mix / Full` 只改变 Analyzer 测量计算量，不改变声音。所有真正改变声音或工程的参数仍由 DAW-control MCP 负责。