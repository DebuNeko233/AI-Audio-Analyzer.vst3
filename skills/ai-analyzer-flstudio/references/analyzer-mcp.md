# AI Audio Analyzer MCP Reference

本文件只描述 MCP 工具、selector、调用顺序和数据有效性。参数的技术语义见 `parameters.md`。

当前 MCP 0.6 共 18 个工具：

```text
audio_bridge_status()
audio_list_tracks()
audio_last_identify(max_age_seconds=10)
audio_bind_last_identified(fl_track_index, fl_track_name, slot, max_age_seconds=5)
audio_instance_map()
audio_snapshot(track)
audio_average(track, seconds=5)
audio_stereo_bands(track)
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
audio_master_status(track="Master")
audio_project_status()
audio_mix_overview(seconds=10, max_tracks=32)
audio_capture_snapshot(name, seconds=5)
audio_list_snapshots()
audio_compare_snapshots(before, after)
audio_temporal_profile(track, seconds=5)
audio_temporal_compare(track_a, track_b, seconds=5, low_hz=40, high_hz=160, alignment_tolerance_ms=80)
```

## 推荐调用层级

不要无条件把 18 个工具全部调用一遍。优先使用最高层、信息足够的工具，再按问题下钻。

```text
工程准备度
→ audio_project_status()

工程最近窗口
→ audio_mix_overview()

单轨稳定窗口
→ audio_average()

单轨时间变化
→ audio_temporal_profile()

两轨频谱关系
→ audio_compare_tracks()

两轨时间关系
→ audio_temporal_compare()

修改前后测量
→ audio_capture_snapshot() / audio_compare_snapshots()
```

## V0.4 FL Studio ↔ Analyzer Identify

AI Audio Analyzer 向宿主公开：

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

每次布尔值发生翻转都会发送一次 `/aianalyzer/identify`。推荐流程：

1. 用 FL Studio MCP 找到目标 Mixer Track / Plugin Slot；
2. 扫描插件真实公开参数，找到 `Identify`；
3. 读取该实例当前值；
4. 设置为相反值；
5. 立即调用 `audio_last_identify()`；
6. 确认事件 fresh 且未 consumed；
7. 立即调用 `audio_bind_last_identified(fl_track_index, fl_track_name, slot)`；
8. 对下一实例重复；
9. 最后调用 `audio_instance_map()` 检查 `discovery_complete`。

不要假设 FL Studio MCP 的工具名称；使用它实际暴露的工具和参数。

每个 Identify 事件只能消费一次。绑定和 runtime UUID 都是 session-scoped。

## Selector

推荐优先级：

```text
mixer:<track_index>/slot:<slot>
→ 唯一 FL Mixer track name
→ runtime UUID
→ 唯一 Analyzer 人类名称
```

支持：

```text
mixer:7
mixer:7/slot:9
fl:7
fl:7/slot:9
```

同一 Mixer Track 上存在多个 Analyzer 时必须带 `slot`。

## Signal / validity

V0.3 Signal Gate：

```text
close threshold   ≈ -50 dBFS
reopen threshold  ≈ -48 dBFS
hold              ≈ 0.4 s
```

必须遵守：

- `signal_present=false` 时不要使用频谱/立体声内容做推断；
- `null` 表示 unavailable，不是 0；
- `audio_average()` 要结合 `active_frames`、`active_ratio` 和 `analysis_valid`；
- stale stream 不应被描述成当前实时状态。

## `audio_project_status()`

优先用于工程级准备度检查。重点字段：

```text
project_ready
audio_ready
live_count
bound_count
unbound_count
active_count
stale_count
instances
warnings
```

如果存在未绑定实例，先做 Identify，而不是靠名称或音频内容猜映射。

## `audio_mix_overview()`

用于一次读取多个 Analyzer 最近窗口状态。它会返回：

```text
tracks
master / master_candidates
potential_spectral_conflicts
```

`potential_spectral_conflicts` 只是 heuristic relative spectral overlap，用来决定是否值得进一步查询。

如果要知道两个轨道是否**在时间上**共同占用某频段，不要只看 overview overlap，继续使用 `audio_temporal_compare()`。

## `audio_snapshot()` 与 `audio_average()`

```text
audio_snapshot(track)
```

读取最新一帧，适合连接/当前状态排查。

```text
audio_average(track, seconds)
```

读取稳定窗口，适合需要几秒统计的任务。频谱、立体声和内容相关统计只对 active frames 计算。

## `audio_compare_tracks()` / `audio_detect_masking()`

`audio_compare_tracks()` 比较两个实例的相对频谱形状。

`audio_detect_masking()` 目前仍是频谱重叠候选工具，不是 Bark/ERB 完整心理声学模型。不要把其返回值写成“已经证明可听遮蔽”。

## V0.6 `audio_temporal_profile()`

用于读取一个 Analyzer 在最近窗口内的时间变化描述：

```text
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_40_160_energy_db
low_band_40_160_min_db
low_band_40_160_max_db
onset_candidate_frames
onset_candidate_density_hz
```

调用前提：VST3 必须是 0.6+，并且窗口内有 `temporal_valid` frame。

`onset_candidate_*` 是阈值化 change candidate，不是 ground-truth onset label。实际阈值会在返回值的 `onset_candidate_thresholds` 中明确给出。

## V0.6 `audio_temporal_compare()`

用于比较两个 Analyzer 的时间对齐包络：

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

重点字段：

```text
aligned_pairs
usable_band_pairs
mean_abs_alignment_offset_ms
coactive_ratio
band_envelope_correlation
normalized_band_temporal_overlap
temporal_descriptor_pairs
onset_candidate_frames_a
onset_candidate_frames_b
coincident_onset_candidate_frames
candidate_coincidence_ratio
```

用途区别：

```text
band_envelope_correlation
→ 两条所选频段包络是否同向变化

normalized_band_temporal_overlap
→ 两条轨道是否经常同时处在各自较强的该频段状态

candidate_coincidence_ratio
→ V0.6 change/onset candidate 是否在对齐的 OSC frame 中同时出现
```

它们都是时间关系证据，不是处理指令，也不是完整 masking 概率。

如果 `mean_abs_alignment_offset_ms` 接近或超过允许容差，降低对相关性结果的解释强度。

## Snapshot / A-B

```text
audio_capture_snapshot("before", seconds=5)
audio_capture_snapshot("after", seconds=5)
audio_compare_snapshots("before", "after")
```

Snapshot 存在于当前 Bridge session 内。

为了可比：

- before / after 尽量使用同一音乐片段；
- 窗口长度尽量相同；
- 检查 `active_ratio`；
- delta 定义为 `After - Before`；
- LUFS-I 是 session 累积值，短时 A/B 时不要当成两个独立重置窗口。

## 多实例与 OSC

所有 VST3 实例默认都向：

```text
127.0.0.1:9855
```

发送 OSC。只有 Bridge 绑定 UDP 9855；VST3 都是 sender，因此不需要每个实例一个端口。

## V0.6 OSC append-only tail

`/aianalyzer/frame` 保留 0..58 的旧字段不变，在 runtime UUID 之后新增：

```text
59  temporal_window_seconds
60  spectral_flux_mean
61  spectral_flux_peak
62  rms_rise_peak_db
63  low_band_energy_db      # FFT-derived 40-160 Hz
64  frame_schema_version    # "0.6"
```

旧 Bridge 可以忽略这些尾字段；0.6 Bridge 先调用稳定旧 parser，再附加解析这些字段。
