---
name: ai-analyzer-flstudio
description: 面向 Cherry Studio + AI Audio Analyzer MCP 的技术使用技能。用于正确发现和绑定多个 Analyzer 实例、选择合适的 MCP 工具、理解 signal state、时间窗口、频谱、响度、True Peak、RMS、Crest、Spectral Centroid、Rolloff、Flatness、Stereo Correlation、Stereo Width、分频段相关性、频谱重叠、工程 Overview 与 A/B Snapshot 等返回值。该 Skill 不预设音乐风格、LUFS 目标、EQ/压缩/Sidechain 策略或具体混音审美。
---

# AI Audio Analyzer MCP Usage Skill

这个 Skill 的职责只有两类：

1. 帮助模型**正确调用 AI Audio Analyzer MCP**；
2. 帮助模型**正确理解 MCP 返回参数的技术含义和有效性**。

本 Skill **不提供具体的风格化混音指导**。不要因为 Skill 中出现某个频率、响度、相关性或频谱重叠数值，就自动推出某种 EQ、压缩、限幅、Sidechain、声像或母带处理方案。具体音乐判断应由用户目标、音乐上下文、参考作品和模型自身知识决定，而不是由本 Skill 预设。

## 1. 首先确认 MCP 和工程状态

工程级任务优先：

```text
audio_project_status()
```

它用于快速检查：

- Bridge/OSC 是否正常；
- 当前有多少 Analyzer 实例；
- 是否全部完成 FL Mixer Track/Slot 绑定；
- 哪些实例有有效信号；
- 是否有 stale stream；
- 是否存在重复 Analyzer 名称；
- 是否能识别 Master candidate。

需要查看底层实例时再调用：

```text
audio_bridge_status()
audio_list_tracks()
audio_instance_map()
```

不要为了获得一个简单工程状态而无条件连续调用所有工具。优先使用最高层、信息足够的工具，再按需要下钻。

## 2. 多实例：先建立确定映射，不靠名字猜

AI Audio Analyzer v0.4+ 每个 live 实例都有 runtime UUID，并公开宿主参数：

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

当 `audio_instance_map()` 显示存在未绑定实例，并且 FL Studio MCP 能访问插件参数时，对每个 AI Audio Analyzer：

1. 用 FL Studio MCP 找到真实 Mixer Track / Slot；
2. 读取该实例 `Identify` 当前值；
3. 将值翻转；
4. 立即调用 `audio_last_identify()`；
5. 确认事件是新的且未消费；
6. 立即调用 `audio_bind_last_identified(fl_track_index, fl_track_name, slot)`；
7. 最后用 `audio_instance_map()` 验证结果。

每个 Identify 事件只能消费一次。不要重复使用旧 Identify 事件绑定另一个轨道。

绑定完成后 selector 优先级：

```text
mixer:<index>/slot:<slot>
→ 唯一 FL Mixer Track 名称
→ runtime UUID
→ 唯一 Analyzer 显示名
```

同一个 Mixer Track 上有多个 Analyzer 时必须带 `slot`。

runtime UUID 和 binding 是 session-scoped；插件重新实例化或工程重新打开后可能需要重新 discovery。

## 3. 先判断数据是否有效，再解释参数

任何内容相关分析都先检查：

```text
signal_present
analysis_valid
active_ratio
```

Signal detector 当前语义：

```text
关闭阈值   约 -50 dBFS
重新打开   约 -48 dBFS
hold       约 0.4 s
```

当 `signal_present=false` 时，Bridge 会把没有意义的频谱/立体声字段设为 `null` 或 unavailable。`null` 的含义是**当前没有有效测量**，不是数值 0。

例如：

```text
stereo_correlation = null
```

不能解释成：

```text
stereo_correlation = 0
```

窗口工具还要结合 `active_ratio`。例如：

```json
{
  "window_seconds": 5,
  "active_ratio": 0.2,
  "analysis_valid": true
}
```

表示这个窗口只有约 20% 的采样帧存在有效输入。描述结果时必须保留这个时间覆盖范围，不要把局部有效数据写成整个窗口持续存在。

## 4. 工具选择策略

### 工程状态

```text
audio_project_status()
```

用于准备度、绑定完整性、实例状态和信号状态。

### 工程级最近窗口概览

```text
audio_mix_overview(seconds=10, max_tracks=32)
```

用于一次读取多个 Analyzer 的窗口平均值以及 heuristic spectral overlap candidates。`potential_spectral_conflicts` 只是相对频谱重叠候选，不等于可听遮蔽，也不表示必须处理。

### 单实例稳定窗口

```text
audio_average(track, seconds)
```

当问题关心“最近几秒的稳定状态”时优先使用它。通常比单帧 `audio_snapshot()` 更适合描述一个时间区间。

### 单实例当前帧

```text
audio_snapshot(track)
```

只在需要最近一次状态、排查连接/实例或明确需要瞬时读数时使用。不要把单帧当作长期统计。

### 两实例比较

```text
audio_compare_tracks(track_a, track_b)
```

用于比较两个有效实例的相对频谱数据。

```text
audio_detect_masking(track_a, track_b)
```

名称中包含 masking，但当前实现是**启发式频谱重叠检测**，不是 Bark/ERB 心理声学模型，也没有证明真正发生了可听遮蔽。

### 立体声分频数据

```text
audio_stereo_bands(track)
```

返回 8 个频段的左右相关性。必须同时确认该轨道有有效信号；低能量频段的相关性不应被过度解释。

### Master 汇总

```text
audio_master_status(track="Master")
```

是 Master 常用指标的技术汇总，不代表任何固定母带标准或目标值。

## 5. V0.5 工程 Snapshot / A-B

需要记录两个时间点或两种状态的测量差异时：

```text
audio_capture_snapshot("before", seconds=5)
```

之后再：

```text
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

可用：

```text
audio_list_snapshots()
```

查看当前 Bridge session 保存的 Snapshot。

Snapshot 仅存在于当前 Bridge session 内，不是工程持久化数据。

A/B 调用技巧：

- 尽量让 before / after 使用同一音乐片段；
- 尽量使用接近的窗口长度；
- 比较 `active_ratio`，避免一边大部分静音、一边持续有声；
- delta 定义为 `After - Before`；
- `LUFS-I` 是 session 累积量，短时 A/B 时不能把它当成独立重置后的两个窗口值。

## 6. 工程 Overview 的正确理解

`audio_mix_overview()` 中：

```text
spectral_regions
potential_spectral_conflicts
spectral_overlap_score
```

是为了让模型更快定位值得继续查询的数据区域。

其中 `spectral_overlap_score` 是相对频谱形状重叠的 heuristic score。它没有包含完整的听觉掩蔽、时间关系、编曲、声源角色或用户意图。因此：

```text
高 overlap ≠ 一定有问题
低 overlap ≠ 一定没有问题
```

它应该用于决定“是否需要进一步读取/比较”，而不是直接生成具体处理动作。

## 7. 参数解释规则

详细参数语义见：

```text
references/parameters.md
```

工具和 selector 细节见：

```text
references/analyzer-mcp.md
```

解释任何指标时遵守：

- 区分 sample peak 与 true peak；
- 区分 RMS 与 LUFS；
- 区分 LUFS-S 与 session 累积 LUFS-I；
- Spectrum dB 是 Analyzer 的机器特征，不是校准 SPL；
- Centroid、Rolloff、Flatness 是描述性统计，不是质量评分；
- Stereo Correlation 描述左右相似/反相关程度，不是“好/坏”分数；
- Stereo Width 是测量量，不应脱离信号有效性直接评价；
- `null` 是 unavailable，不是 0；
- 所有窗口统计都要结合 `window_seconds`、`active_frames`、`active_ratio`。

## 8. 与 FL Studio MCP 协作时的边界

AI Audio Analyzer MCP 负责：

```text
测量 / 读取 / 比较 / 验证
```

FL Studio MCP 负责：

```text
读取 DAW 拓扑 / 访问插件 / 修改宿主状态
```

本 Skill 可以指导模型用 FL Studio MCP 完成 Identify 映射，也可以要求修改后再次读取 Analyzer 数据进行测量对比，但**不规定模型应该修改什么参数、修改多少、采用哪种混音风格**。

如果用户要求修改工程：

- 先读取真实的轨道、Slot、插件和参数；
- 不编造不存在的插件参数；
- 修改后读回宿主实际状态；
- 如需验证测量变化，可使用 Snapshot A/B；
- 技术测量结论与音乐审美判断要分开表达。

## 9. 输出纪律

模型引用 Analyzer 数据时，应尽量包含必要上下文，例如：

```text
实例 / selector
窗口长度
signal_present
active_ratio
关键测量值
测量是否有效
```

不要把以下内容写成 Analyzer 已测得的事实：

- “这个声音应该更暖/更亮/更现代”；
- “这个风格必须达到某个 LUFS”；
- “这个频段必须削多少 dB”；
- “出现频谱重叠就必须 EQ / Sidechain”；
- “某个 correlation 值天然就是好或坏”。

这些属于音乐判断或处理策略，不属于本 MCP 的测量事实，也不属于本 Skill 的职责。