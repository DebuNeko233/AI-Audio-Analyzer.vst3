# AI Audio Analyzer Cherry Studio Skill

这个 Skill 面向：

- Cherry Studio
- AI Audio Analyzer.vst3 0.4+
- AI Audio Analyzer MCP 0.5+
- 可选的 FL Studio MCP

它的目标不是教模型“怎么混音”，而是让模型更可靠地：

- 正确调用 Analyzer MCP；
- 正确发现并区分多个 Analyzer 实例；
- 通过 Identify 建立 Analyzer ↔ FL Mixer Track/Slot 映射；
- 理解 Signal State、窗口有效性和 `null`；
- 理解 Peak、RMS、Crest、LUFS、True Peak、Spectrum、Centroid、Rolloff、Flatness、Stereo Correlation、Stereo Width 等参数；
- 正确使用工程 Overview、轨道比较和 Snapshot A/B；
- 区分“测量事实”和“音乐/风格判断”。

## 不包含什么

本 Skill 不预设：

- 某种风格应该达到多少 LUFS；
- 哪个频率一定要削或加；
- Kick/Bass 一定怎样处理；
- Vocal 一定怎样 EQ；
- 是否必须 Sidechain；
- 某个 Stereo Correlation 数字是否天然“好/坏”；
- Mastering 的固定处理链或目标。

这些属于具体音乐判断，不属于 Analyzer MCP 的技术使用说明。

## 推荐调用入口

工程级任务优先：

```text
audio_project_status()
```

需要最近窗口的工程概览：

```text
audio_mix_overview(10)
```

需要单轨稳定测量：

```text
audio_average("mixer:7/slot:9", 5)
```

需要瞬时状态：

```text
audio_snapshot("mixer:7/slot:9")
```

需要 A/B：

```text
audio_capture_snapshot("before", 5)
audio_capture_snapshot("after", 5)
audio_compare_snapshots("before", "after")
```

## 多实例绑定

V0.4+ 插件提供宿主可见参数：

```text
Identify
```

每次该布尔值翻转，目标实例都会发送一次 `/aianalyzer/identify`。配合 FL Studio MCP，可以把刚刚操作的 Mixer Track/Slot 和该实例 runtime UUID 做确定绑定：

```text
FL Mixer Track / Slot
        ↕
Analyzer runtime UUID
```

绑定流程与 selector 规则详见：

```text
references/analyzer-mcp.md
```

## 参数语义

所有主要返回字段的含义、有效性和常见误读见：

```text
references/parameters.md
```

重点规则：

- `null` 表示当前无有效测量，不是 0；
- `signal_present=false` 时不要解释频谱/立体声字段；
- 窗口结果必须结合 `active_ratio`；
- LUFS-I 是 session 累积量；
- Spectrum 是机器特征，不是校准 SPL；
- Spectral overlap 只是 heuristic，不等于已经发生可听 masking；
- A/B delta 是 `After - Before`。

## 推荐同时启用的 MCP

- `ai-audio-analyzer`
- `fl-studio`（需要读取/控制 FL Studio 时）

AI Audio Analyzer MCP 负责测量和验证；FL Studio MCP 负责 DAW 拓扑和宿主操作。

## 推荐 Agent 提示

```text
使用 ai-analyzer-flstudio Skill 时，只把它当作 AI Audio Analyzer MCP 的调用和参数语义说明。
优先使用 audio_project_status 和 audio_mix_overview 获取工程级状态，再按需要下钻。
多实例必须通过 Identify 和 FL Mixer Track/Slot 做确定绑定，不靠插件显示名猜测。
任何频谱或立体声解释前先检查 signal_present、analysis_valid 和 active_ratio。
null 表示 unavailable，不是 0。
不要从 Skill 中推导固定 LUFS、EQ、压缩、Sidechain、Stereo 或 Mastering 风格规则。
具体音乐处理策略由用户目标、当前工程上下文和模型自身音乐知识决定。
```
