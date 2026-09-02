# AI Audio Analyzer 参数语义参考

本文件只解释测量字段的技术含义、有效性和常见误读，不提供具体混音风格或处理方案。

## Signal / validity

### `signal_present`

布尔值。表示当前 Analyzer 是否检测到有效输入。

当前 detector 约为：

```text
close   < -50 dBFS 持续约 0.4 s
reopen  > -48 dBFS
```

`false` 时，部分依赖有效音频内容的字段会被 Bridge 置为 `null`。

### `detector_peak_db`

用于 Signal Gate 判断的当前检测峰值，单位 dBFS。

它是检测器状态字段，不等于 LUFS、RMS 或 True Peak。

### `silence_seconds`

当前连续低于 Signal Gate 关闭条件的时间累计。

### `analysis_valid`

窗口/汇总结果是否包含可用于内容分析的有效帧。

### `active_frames`

请求窗口内被视为有效输入的分析帧数量。

### `active_ratio`

有效帧占请求窗口帧数的比例：

```text
0.0 → 没有有效输入
1.0 → 窗口内全部帧有效
```

它描述时间覆盖率，不是响度或置信度评分。

## Level / dynamics

### `peak_db`

Sample Peak，单位 dBFS。描述离散采样点的最大幅度。

它不是 True Peak。

### `rms_db`

RMS 电平，单位 dBFS。描述窗口内信号能量的均方根尺度。

它不是 LUFS。

### `crest_db`

近似描述峰值相对平均能量的差异：

```text
Crest ≈ Peak - RMS
```

数值本身不表示“好”或“坏”，需要结合信号类型和上下文解释。

### `true_peak_dbtp`

当前 True Peak，单位 dBTP，用于估计采样点之间的峰值。

### `max_true_peak_dbtp`

当前 Analyzer session 自最近 reset/prepare 以来记录到的最大 True Peak。

它是 session 累积状态，不是只属于最近一个 `audio_average()` 窗口。

## Loudness

### `lufs_s`

Short-Term LUFS，约 3 秒时间尺度。

持续无有效输入后该字段可能变为 `null`。

### `lufs_i`

Integrated LUFS。自 Analyzer 最近一次 reset/prepare 后持续累计，并使用 EBU R128 gating。

如果只播放了某个局部片段，`lufs_i` 只代表该 session 已累计的内容，不能自动当作整首节目的完整 Integrated Loudness。

短时 A/B 时，两个 Snapshot 的 LUFS-I 不是两个独立重置的测量窗口。

## Spectrum

### `bands_db`

32 个 20 Hz–20 kHz 对数分布的 FFT 频谱特征。

这些值用于机器比较频谱形状和相对能量分布，不是经过声压校准的 SPL。

`signal_present=false` 时通常为 `null`。

### `spectral_regions`

V0.5 工程工具将 32-band 数据汇总成几个宽频段：

```text
sub_20_120_db
low_mid_120_500_db
mid_500_2000_db
presence_2000_5000_db
high_5000_20000_db
```

这些名称是便于机器组织数据的频率范围标签，不代表这些区域一定对应某种音色问题。

### `centroid_hz`

Spectral Centroid。可理解为频谱能量分布的“重心频率”。

更高或更低只是描述频谱重心变化，不是质量评分。

### `rolloff_hz`

当前实现约为 85% Spectral Rolloff：累计频谱能量达到约 85% 时对应的频率。

### `flatness`

Spectral Flatness。用于描述频谱更接近窄带/谐波型还是更接近宽带/噪声型分布。

它不是失真度、清晰度或音质评分。

## Stereo

### `stereo_correlation`

全频段左右相关性，通常约位于：

```text
+1  左右高度相似
 0  左右线性相关较弱
-1  左右高度反相关
```

它描述统计相关性，不直接等价于“宽度好坏”或“是否必须处理”。

必须结合有效信号状态与对应频率能量解释。

### `stereo_width`

Analyzer 的 Mid/Side width ratio 测量值，用于描述当前左右声道所形成的侧向能量相对关系。

它是相对测量量，不是百分比意义上的固定“宽度分数”。

### `band_stereo_correlation`

8 个分频段 Stereo Correlation：

```text
20–60 Hz
60–120 Hz
120–250 Hz
250–500 Hz
500 Hz–1 kHz
1–2 kHz
2–5 kHz
5–20 kHz
```

如果某个频段能量很低，即使返回相关性数值，也不应赋予过强语义。Signal State 无效时 Bridge 会返回 unavailable/null。

## V0.6 Temporal

V0.6 的时间特征在 VST3 内部以 1024-sample hop 计算，再汇总到约 10 Hz OSC 帧。它们用于描述**变化和时间共现**，不是音质评分。

### `temporal_supported`

表示当前 frame 是否来自支持 V0.6 temporal tail 的插件版本。

旧版 Analyzer 可以继续被 Bridge 读取，但该字段为 false/缺失时不能假装存在时间特征。

### `temporal_valid`

表示当前 V0.6 时间特征是否有有效输入。通常要求：

```text
signal_present = true
且 temporal_window_seconds > 0
```

### `temporal_window_seconds`

当前 OSC 时间特征汇总覆盖的内部分析时长。通常接近网络更新间隔，但不应硬编码为固定 0.1 s。

### `spectral_flux_mean`

V0.6 使用相邻 FFT 窗口的**归一化频谱分布**计算正向变化量，并在当前 OSC 汇总窗口内取平均。

近似语义：

```text
接近 0 → 相邻频谱分布变化较少
更高     → 频谱分布变化更明显
```

它刻意对整体电平缩放较不敏感，因此不能代替 RMS 电平变化。

### `spectral_flux_peak`

当前 OSC 汇总窗口内最大的 normalized spectral flux。

它比 `spectral_flux_mean` 更强调短时变化峰值，但仍不是“检测到一次真实 musical onset”的绝对证明。

### `rms_rise_peak_db`

当前 OSC 汇总窗口内，相邻内部 FFT 窗口之间最大的**正向 RMS 增量**，单位 dB。

它描述快速电平上升证据，不等于 Crest Factor，也不等于攻击时间常数。

### `low_band_energy_db` / `low_band_40_160_energy_db`

VST3 temporal tail 中的 `low_band_energy_db` 是 FFT-derived **40–160 Hz** 能量特征；`audio_temporal_profile()` 会把近期有效 frame 汇总为 `low_band_40_160_energy_db`、min 和 max。

它用于构建低频能量包络，不是校准 SPL，也不代表某种乐器一定存在于该频段。

### `onset_candidate_frames`

`audio_temporal_profile()` 使用显式阈值，把 OSC frame 标记成“onset/change candidate”。当前默认阈值会随结果一起返回：

```text
rms_rise_peak_db >= 3.0
OR
spectral_flux_peak >= 0.18
```

这是压缩后的启发式事件候选，不是带人工标注验证的 onset ground truth。

### `onset_candidate_density_hz`

候选 frame 数量除以有效 temporal 覆盖秒数。它描述“变化候选出现密度”，不是 BPM、节拍或音符密度。

### `band_envelope_correlation`

`audio_temporal_compare()` 将两个 Analyzer 的同一频段能量包络按时间对齐后计算 Pearson correlation：

```text
接近 +1 → 两条包络倾向同向变化
接近  0 → 线性共变较弱
接近 -1 → 两条包络倾向反向变化
```

它描述共变关系，不说明哪条轨道“应该让位”。

### `normalized_band_temporal_overlap`

把两个轨道在所选频段的包络分别相对各自窗口峰值归一化后，对每个对齐点取 `min()` 再平均。

范围通常约 0–1：

```text
更高 → 两条轨道更常同时处在各自较强的该频段状态
更低 → 该频段强能量更少同时出现
```

它是时间占用的 heuristic score，不是完整听觉 masking 概率。

### `coactive_ratio`

时间对齐 frame 中，两边同时 `signal_present=true` 的比例。

### `candidate_coincidence_ratio`

两边 onset/change candidate 在对齐 frame 中同时出现的比例摘要。它依赖上述阈值和 OSC 时间分辨率，不能解释为样本级精确瞬态同步率。

### `alignment_tolerance_ms` / `mean_abs_alignment_offset_ms`

`audio_temporal_compare()` 对两个独立 Analyzer stream 做时间对齐时使用的容差和实际平均绝对时间偏差。对齐质量差时，不应过度解释包络相关性。

## Track comparison

### `spectral_overlap_score`

用于两个轨道相对频谱形状的 heuristic overlap score。

它基于频谱相对形状重叠，不是完整心理声学 Masking 测量，也没有编码完整时间关系、编曲关系或感知阈值。

因此：

```text
高 overlap 只能说明频谱形状重叠较明显
不能直接推出“存在可听遮蔽”
```

V0.6 的 `audio_temporal_compare()` 可补充“是否在时间上共同变化/共同占用该频段”的证据，但两类指标都不等于最终听觉结论。

### `audio_detect_masking()`

尽管工具名包含 masking，目前仍应理解为“潜在频谱重叠候选检测”。不要把返回值描述成已经通过心理声学模型证明的遮蔽事实。

## Identity / topology

### `id` / `runtime_id`

Live VST3 实例运行时 UUID。用于机器区分同名 Analyzer。

它是 session-scoped，不应作为跨工程长期永久 ID。

### `track` / `analyzer_name`

插件内部的人类可读名称。可能重复，因此不能作为唯一身份。

### `binding`

V0.4 Identify 后建立的 FL Studio 宿主关系，包含：

```text
fl_track_index
fl_track_name
slot
runtime_id
```

### `selector`

绑定后推荐机器使用：

```text
mixer:<track_index>/slot:<slot>
```

它比 Analyzer 显示名更适合精确选中实例。

## Freshness / connection

### `age_seconds`

Bridge 距离收到该实例最近一次 OSC frame 的时间。

### `stale`

表示该实例数据是否超过 Bridge 设定的新鲜度阈值。Stale 数据不应被描述成当前实时状态。

### `duplicate_name`

表示当前存在另一个相同 Analyzer 显示名的实例。发生重复时应使用 binding selector 或 runtime UUID。

## Snapshot A/B

### `audio_capture_snapshot(name, seconds)`

保存当前 Bridge session 中一个项目级窗口状态。Snapshot 不写入 FL Studio 工程，也不会跨 Bridge 重启持久化。

### `audio_compare_snapshots(before, after)`

Delta 定义：

```text
Delta = After - Before
```

因此对 dB 类字段：

```text
positive → After 数值更高
negative → After 数值更低
```

Stereo Correlation delta：

```text
positive → After 更偏向正相关
negative → After 更偏向低相关/反相关方向
```

比较前应确认两边使用可比的音乐片段、窗口长度和 `active_ratio`。

## `null` 的统一规则

任何参数返回 `null` 时统一理解为：

```text
当前没有有效/可用的该项测量
```

不要把 `null` 替换成 0，也不要由 `null` 推导音频内容特征。
