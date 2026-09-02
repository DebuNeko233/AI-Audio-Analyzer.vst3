---
name: ai-analyzer-flstudio
description: 面向 Cherry Studio + AI Audio Analyzer MCP 的技术使用技能。用于正确发现和绑定多个 Analyzer 实例、选择合适的 MCP 工具、理解 signal state、时间窗口、频谱、响度、True Peak、RMS、Crest、Spectral Centroid、Rolloff、Flatness、Stereo Correlation、Stereo Width、分频段相关性、频谱重叠、V0.6 temporal descriptors、工程 Overview 与 A/B Snapshot 等返回值。该 Skill 不预设音乐风格、LUFS 目标、EQ/压缩/Sidechain 策略或具体混音审美。
---

# AI Audio Analyzer MCP Usage Skill

这个 Skill 的职责只有两类：

1. 帮助模型**正确调用 AI Audio Analyzer MCP**；
2. 帮助模型**正确理解 MCP 返回参数的技术含义和有效性**。

本 Skill **不提供具体的风格化混音指导**。不要因为 Skill 中出现某个频率、响度、相关性、频谱重叠或时间重叠数值，就自动推出某种 EQ、压缩、限幅、Sidechain、声像或母带处理方案。具体音乐判断应由用户目标、音乐上下文、参考作品和模型自身知识决定，而不是由本 Skill 预设。

## 1. 首先确认 MCP 和工程状态

工程级任务优先：

```text
audio_project_status()
```

它用于快速检查：Bridge/OSC、Analyzer 数量、绑定完整性、有效信号、stale stream、重复名称和 Master candidate。

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

同一个 Mixer Track 上有多个 Analyzer 时必须带 `slot`。runtime UUID 和 binding 是 session-scoped。

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

V0.6 时间分析还要检查：

```text
temporal_supported
temporal_valid
temporal_window_seconds
```

旧插件仍可读取基础指标，但 `temporal_supported=false`/缺失时不能假装有 V0.6 时间特征。

窗口工具必须结合 `active_ratio`。例如 5 秒窗口 `active_ratio=0.2` 表示只有约 20% 的 frame 有有效输入；不要把局部有效结果描述成整个 5 秒持续存在。

## 4. 工具选择策略

### 工程准备度

```text
audio_project_status()
```

### 工程级最近窗口概览

```text
audio_mix_overview(seconds=10, max_tracks=32)
```

`potential_spectral_conflicts` 只是相对频谱重叠候选，不等于可听遮蔽。

### 单实例稳定窗口

```text
audio_average(track, seconds)
```

### 单实例当前帧

```text
audio_snapshot(track)
```

### 单实例时间变化

```text
audio_temporal_profile(track, seconds=5)
```

用于读取：

```text
spectral_flux_mean / peak
rms_rise_peak_db
40-160 Hz temporal energy
onset/change candidate density
```

候选事件来自返回值中明确给出的阈值，不是 ground-truth onset label。

### 两实例频谱比较

```text
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
```

当前 masking 工具仍是 heuristic spectral overlap。

### 两实例时间比较

```text
audio_temporal_compare(
  track_a,
  track_b,
  seconds=5,
  low_hz=40,
  high_hz=160,
  alignment_tolerance_ms=80
)
```

用于读取所选频段的：

```text
coactive_ratio
band_envelope_correlation
normalized_band_temporal_overlap
candidate_coincidence_ratio
```

如果用户的问题是“两个轨道是否**同时**占用某频段”，应优先补充这个工具，而不是只看静态 `spectral_overlap_score`。

### 立体声分频数据

```text
audio_stereo_bands(track)
```

### Master 技术汇总

```text
audio_master_status(track="Master")
```

它是测量汇总，不代表固定母带标准。

## 5. V0.5 工程 Snapshot / A-B

需要记录两个状态的测量差异时：

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

可用 `audio_list_snapshots()` 查看当前 Bridge session 保存的 Snapshot。

A/B 调用技巧：

- 尽量让 before / after 使用同一音乐片段；
- 尽量使用接近的窗口长度；
- 比较 `active_ratio`；
- delta 定义为 `After - Before`；
- `LUFS-I` 是 session 累积量，短时 A/B 时不能当作独立重置后的两个窗口值。

## 6. V0.6 时间证据怎么与频谱证据配合

静态频谱回答的是：

```text
两个轨道在某些频率是否都有较强能量
```

V0.6 temporal tools 补充的是：

```text
这些能量是否在时间上共同出现/共同变化
```

因此：

```text
spectral_overlap_score 高
+
normalized_band_temporal_overlap 高
```

只表示“频谱和时间共现证据都较强”，仍然不能自动推出某种处理动作。

同样：

```text
band_envelope_correlation 高
```

表示两条所选频段包络倾向同向变化，不表示哪条轨道应该被修改。

解释 `audio_temporal_compare()` 时同时报告：

```text
window_seconds
band_hz
aligned_pairs
usable_band_pairs
alignment_tolerance_ms
mean_abs_alignment_offset_ms
```

对齐数据太少或偏差太大时，不要过度解释 correlation/overlap。

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

- Sample Peak ≠ True Peak；
- RMS ≠ LUFS；
- LUFS-S ≠ session 累积 LUFS-I；
- Spectrum dB 不是校准 SPL；
- Centroid、Rolloff、Flatness 是描述性统计，不是质量评分；
- Stereo Correlation / Width 是测量量，不是“好坏分数”；
- Spectral Flux 描述归一化频谱变化，不等于整体电平变化；
- RMS Rise 描述快速电平上升，不等于 Crest Factor；
- Temporal overlap/correlation 是时间关系证据，不是 masking 概率；
- `null` 是 unavailable，不是 0；
- 窗口统计都要结合覆盖时长、active ratio 和有效 frame 数。

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

如果用户要求修改工程：先读取真实轨道/Slot/插件/参数，不编造参数，修改后读回宿主状态；需要验证时使用 Analyzer 和 Snapshot/A-B；技术测量与音乐审美判断分开表达。

## 9. 输出纪律

模型引用 Analyzer 数据时，应尽量包含：

```text
实例 / selector
窗口长度
signal_present / active_ratio
若使用 temporal：band_hz / temporal coverage / alignment quality
关键测量值
测量是否有效
```

不要把以下内容写成 Analyzer 已测得的事实：

- “这个声音应该更暖/更亮/更现代”；
- “这个风格必须达到某个 LUFS”；
- “这个频段必须削多少 dB”；
- “出现频谱重叠就必须 EQ / Sidechain”；
- “某个 correlation / temporal overlap 值天然就是好或坏”。

这些属于音乐判断或处理策略，不属于本 MCP 的测量事实，也不属于本 Skill 的职责。
