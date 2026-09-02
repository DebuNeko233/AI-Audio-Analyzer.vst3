# AI Audio Analyzer Cherry Studio Skill

这个 Skill 面向：

- Cherry Studio
- AI Audio Analyzer.vst3 0.6+
- AI Audio Analyzer MCP 0.6
- 可选的 FL Studio 控制 MCP：https://github.com/rosasynthesiz/flstudio-mcp

Skill 的职责是让模型**正确调用 Analyzer MCP、理解返回参数、处理多实例映射和数据有效性**。它不提供固定混音风格、LUFS 目标、EQ/压缩/Sidechain 配方。

## 当前主要能力

```text
V0.3  Signal State / runtime UUID
V0.4  Identify → FL Mixer Track/Slot deterministic mapping
V0.5  Project Status / Mix Overview / Snapshot A-B
V0.6  Spectral Flux / RMS Rise / temporal profile / band-envelope comparison
```

## 推荐初始化顺序

```text
audio_project_status()
```

如果存在未绑定 Analyzer：

```text
FL Studio MCP 找到真实 Mixer Track / Slot
→ 读取目标 Analyzer 的 Identify 当前值
→ 翻转 Identify
→ audio_last_identify()
→ audio_bind_last_identified(...)
→ audio_instance_map()
```

绑定后优先使用：

```text
mixer:<index>/slot:<slot>
```

## 工具选择

```text
工程状态             audio_project_status()
工程窗口概览         audio_mix_overview()
单轨稳定窗口         audio_average()
单轨当前帧           audio_snapshot()
单轨时间变化         audio_temporal_profile()
两轨频谱关系         audio_compare_tracks()
两轨时间关系         audio_temporal_compare()
立体声分频           audio_stereo_bands()
Snapshot 管理        audio_capture_snapshot() / audio_list_snapshots()
Before/After         audio_compare_snapshots()
```

MCP 0.6 当前共 18 个工具，完整列表见 `references/analyzer-mcp.md`。

## V0.6 时间分析

VST3 0.6 在原 OSC frame 尾部 append：

```text
temporal_window_seconds
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_energy_db   # 40-160 Hz FFT-derived energy
frame_schema_version
```

单轨：

```text
audio_temporal_profile("mixer:7/slot:9", 5)
```

两轨：

```text
audio_temporal_compare(
  "mixer:4/slot:9",
  "mixer:7/slot:9",
  5,
  40,
  160,
  80
)
```

`band_envelope_correlation` 描述两条所选频段包络的共变；`normalized_band_temporal_overlap` 描述它们是否经常同时处在各自较强状态。两者都是测量证据，不是“必须处理”的结论。

`onset_candidate_*` 使用返回值里明确给出的 threshold，是压缩后的 change-event heuristic，不是人工标注意义上的真实 onset label。

## Signal State

Analyzer 低于约 `-50 dBFS` 持续约 0.4 秒后关闭 Gate，重新高于约 `-48 dBFS` 才打开。

无有效输入时：

- Spectrum / Stereo 相关字段为 `null` / unavailable；
- V0.6 temporal 字段 `temporal_valid=false`；
- `null` 不等于 0；
- LUFS-I 和 session max True Peak 可以继续保留。

窗口结果必须结合 `active_ratio`。

## Snapshot A/B

```text
audio_capture_snapshot("before", 5)
# 外部控制 MCP 修改工程
audio_capture_snapshot("after", 5)
audio_compare_snapshots("before", "after")
```

尽量使用同一音乐片段、相同窗口长度和接近的 `active_ratio`。Snapshot 只存在于当前 Bridge session。

## 推荐 Agent 提示

```text
优先使用 ai-analyzer-flstudio Skill。
先用 audio_project_status 检查工程准备度；未绑定实例通过 Identify 建立 FL Mixer Track/Slot 映射。
内容分析前检查 signal_present、analysis_valid、active_ratio；temporal 分析额外检查 temporal_supported/temporal_valid。
需要稳定统计时用 audio_average；需要单轨时间变化时用 audio_temporal_profile；需要比较两个轨道是否在时间上共同占用某频段时用 audio_temporal_compare。
不要把 null 当 0，不要把 spectral overlap、temporal overlap、correlation 或 onset candidate 自动解释成具体混音处理指令。
如果通过 FL Studio MCP 修改工程，修改后用 Analyzer/Snapshot 做测量回读。
```

## 参数参考

```text
references/analyzer-mcp.md   MCP 调用与 selector
references/parameters.md     参数技术语义与有效性
```
