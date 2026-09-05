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
44 Tool descriptions
15 MCP Resources under aianalyzer://guide/*
```

If the client supports MCP Resources, it can read `aianalyzer://guide/index` and then only the guide needed for the current task.

The packaged `skill/` directory remains the canonical Markdown source for those detailed Resources. Importing it directly into a Skill-capable client is optional and is especially useful when that client does not expose MCP Resources.

## What the Agent can do

MCP 1.2 exposes **44 tools** on the stacked P7a branch for measurement and evidence workflows, including:

```text
project/runtime identity-scope disclosure
Song Memory
explainable Section Map
Track Story
Section-aware Mix Relationships
coverage-aware retained Dynamics Distribution
direct recent-window Mono-fold Compatibility evidence
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

For retained dynamics across a selected pass, explicit DAW-time range, or cached section, the Agent can use:

```text
audio_dynamics_distribution(...)
```

P6a reports coverage-weighted RMS / LUFS-S / Crest / observed Sample-Peak / observed True-Peak distributions. Missing bins stay missing. `lufs_s_interpercentile_range_lu` is descriptive P90-P10 LUFS-S spread, **not EBU Loudness Range**. Standardized EBU LRA, arbitrary-range Integrated LUFS and arbitrary-range PLR remain unavailable rather than being fabricated from incompatible retained state.

For direct current mono translation evidence, the Agent can use:

```text
audio_mono_compatibility(track, seconds=5.0)
```

P7a reuses the Analyzer's existing Mid/Side measurements to report mono-fold RMS change and energy-aware 32 band-center loss evidence. It adds no realtime DSP or OSC fields. `inspection_priority` is only a shortlist aid, not a quality/pass-fail score. If Mid reaches the `-120 dB` measurement floor, `floor_censored=true` means the cancellation depth is floor-limited rather than precisely known below that floor.

P7a is **recent-window only**. It does not claim arbitrary historical/Section 32-band mono-fold evidence, and it does not directly measure mono-fold Sample Peak or True Peak. Those peak values must not be inferred from stereo metrics.

When verifying a real DAW/plugin change over a known musical passage, the Agent can use:

```text
audio_begin_range_verification(...)
-> external DAW-control write + actual host readback
-> replay returned effective_range
audio_complete_range_verification(...)
```

This compares the same retained DAW-time range before and after. The range is normalized to one-second Song Memory bins, different Analyzer instances may use different local transport epochs, and pre-change memory cannot silently be reused as the After pass.

`controlled_comparison=true` means only that technical comparability checks passed. `closed_loop_complete=true` additionally requires actual caller-supplied host readback. Neither means the change sounds better or establishes persistent project identity.

A/B/C section families are not automatic Verse/Chorus/Drop labels. Track Story does not infer Bass/Vocal/Drums roles. Relationship `shortlist_priority` is not a masking/mix-problem probability or processing instruction. Mono-fold `inspection_priority` is likewise not a stereo-quality score or mandatory processing rule.

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
44 个 Tool description
15 个 MCP Resources: aianalyzer://guide/*
```

提供基本调用顺序和关键限制。

如果客户端支持 MCP Resources，可以先读 `aianalyzer://guide/index`，再按任务读取需要的详细 Guide。Release 中的 `skill/` 仍然保留，因为它是这些 Guide Resources 的 canonical Markdown 内容源，同时也可以被支持 Skill 的客户端直接导入。

当前 MCP 1.2 在 Stacked P7a 分支共 **44 个工具**，包括 Project/Runtime Identity Scope、Song Memory、Section Map、Track Story、Section-aware Relationships、Coverage-aware Dynamics Distribution、Direct Recent-window Mono-fold Compatibility、Analysis Profile Control，以及 Recent-window / Transport-anchored Same-range 两种验证路径。

新会话开始时，或者用户可能切换/重新打开了 FL Studio 工程时，Agent 应先调用：

```text
audio_project_identity_status()
```

当前 `runtime_id` 只是一次 Live Plugin Instance 的 UUID，不是永久工程/轨道身份；即使重新打开**同一个工程** UUID 也会变化。MCP 当前也没有可信 Stable Project ID，因此 MCP 一直运行时，上一个工程的 Song Memory、Section Map、Snapshot、Relationship、Verification 等状态还不能保证与新工程完全隔离。

在后续接入精确 Project Identity 之前，如果需要严格隔离，**切换或重新打开工程后重启 Analyzer MCP**。新的 Runtime UUID 本身不能证明工程已经切换。

要查看 Retained Dynamics，可以调用：

```text
audio_dynamics_distribution(...)
```

P6a 会按 Coverage 过滤/加权 1 秒 Retained Bin，输出 RMS、LUFS-S、Crest、Observed Sample Peak、Observed True Peak 的描述性分布。Missing Bin 不会补成 0 或静音；`lufs_s_interpercentile_range_lu` 也不是标准 EBU LRA。任意范围 Integrated LUFS / PLR 目前明确不可用，不会伪造。

要检查当前 Mono Translation，可以调用：

```text
audio_mono_compatibility(track, seconds=5.0)
```

P7a 直接复用现有 Mid/Side 测量，输出 Mono-fold RMS 变化和 Energy-aware 32 Band-center Loss Evidence，不增加新的 Realtime DSP/OSC 字段。`inspection_priority` 只是检查优先级，不是质量分数或 Pass/Fail。Mid 到达 `-120 dB` 测量地板时会标记 `floor_censored=true`，表示低于测量地板的抵消深度不能再精确断言。

P7a 当前只分析 Recent Window，不会把结果冒充任意 Historical/Section 32-band Mono Fold，也不直接测量 Mono-fold Sample Peak / True Peak，不能从 Stereo 指标推算这两个 Peak 值。

对于已知的歌曲时间范围，优先使用：

```text
audio_begin_range_verification(...)
-> 外部 DAW-control MCP 修改并回读真实宿主状态
-> 重放返回的 effective_range
audio_complete_range_verification(...)
```

它会按同一个 DAW 时间范围比较 Before/After，并阻止把修改前旧 Song Memory 偷偷当成 After。

`controlled_comparison=true` 只表示技术可比性通过；`closed_loop_complete=true` 还要求真实 Host Readback。两者都不表示 After 在艺术上更好，也不证明 Persistent Project Identity。

A/B/C 不是自动 Verse/Chorus/Drop；Track Story 不自动判断轨道角色；Relationship Shortlist 也不是 Masking/Mix Problem 概率；Mono-fold `inspection_priority` 也不是 Stereo Quality Score。

`Eco / Balanced / Mix / Full` 只改变 Analyzer 测量计算量，不改变声音。所有真正改变声音或工程的参数仍由 DAW-control MCP 负责。