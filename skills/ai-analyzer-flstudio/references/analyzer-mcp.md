# AI Audio Analyzer MCP Reference

当前主要工具：

```text
audio_bridge_status()
audio_list_tracks()
audio_snapshot(track)
audio_average(track, seconds=5)
audio_stereo_bands(track)
audio_compare_tracks(track_a, track_b)
audio_detect_masking(track_a, track_b)
audio_master_status(track="Master")
```

## 推荐调用策略

```text
开始任何分析
audio_bridge_status()
→ audio_list_tracks()

单轨快速检查
audio_average(track_or_id, 5)

Master
audio_master_status("Master")
→ audio_average("Master", 10)
→ audio_stereo_bands("Master")

双轨冲突
audio_average(A, 5)
→ audio_average(B, 5)
→ audio_compare_tracks(A, B)
→ audio_detect_masking(A, B)
```

不要用单帧 `audio_snapshot()` 代替稳定的混音判断，除非用户明确要求瞬时状态。

# V0.3 Signal State

插件采用以下 signal detector：

```text
close threshold   ≈ -50 dBFS
reopen threshold  ≈ -48 dBFS
hold              ≈ 0.4 s
```

Bridge 输出时：

- `signal_present=false`：当前没有有效分析输入；
- `spectrum_valid=false`：`bands_db`、centroid、rolloff、flatness 返回 `null`；
- `stereo_valid=false`：full-band / band-limited correlation 和 width 返回 `null`；
- 连续无输入约 3 秒后 `lufs_s=null`；
- `lufs_i` 与 `max_true_peak_dbtp` 保留，因为它们是 session 累计值。

`null` 表示“此指标当前无有效测量”，绝不能按数值 0 解释。

# Window averaging

`audio_average()` 会同时返回：

```text
frames
active_frames
active_ratio
analysis_valid
signal_present
```

频谱、立体声、Crest、LUFS-S 只对 active frames 统计。Peak/RMS 与 session loudness/true-peak 仍可描述完整请求窗口或累计 session。

示例：

```json
{
  "window_seconds": 5,
  "frames": 50,
  "active_frames": 10,
  "active_ratio": 0.2,
  "analysis_valid": true
}
```

这表示 5 秒窗口里约 20% 的 Analyzer 帧存在有效输入。不要把这种结果描述成“整个 5 秒都持续存在”的频谱问题。

如果 `active_frames=0`，频谱/立体声类汇总会返回 `null`，应该要求开始播放、换到有声段落，或选择正确实例。

# 多实例

多个 AI Audio Analyzer 可以同时把 OSC 发到同一个：

```text
127.0.0.1:9855
```

只有 Python Bridge 绑定 UDP 9855；VST3 实例都是 sender，所以无需每实例分配端口。

每个 V0.3 插件实例发送：

```text
track = 用户可编辑的人类名称
id    = 当前 live 实例的 runtime UUID
```

Bridge 以 `id` 为内部 key，所以两个都叫 `Bass` 的实例也不会互相覆盖。

`audio_list_tracks()` 会报告：

```json
{
  "id": "...runtime uuid...",
  "track": "Bass",
  "duplicate_name": true,
  "signal_present": true
}
```

当 `duplicate_name=true` 时，不要使用歧义的人类名称继续调用。使用完整 `id`、唯一的 `id` 前缀，或建议用户重命名为 `Bass Sub` / `Bass Mid` 等唯一名称。

runtime UUID 不保存成永久项目身份。重载/重新实例化插件后 UUID 可以变化，因此跨会话不要记住旧 UUID。

# OSC schema

地址保持：

```text
/aianalyzer/frame
```

这是为了向后兼容，品牌改名不会改变协议地址。

V0.1/V0.2 前缀保持不变，V0.3 只追加：

```text
55 signal_present      int
56 detector_peak_db    float
57 silence_seconds     float
58 runtime_uuid        string
```

环境变量也为兼容性继续保留：

```text
AI_ANALYZER_OSC_HOST
AI_ANALYZER_OSC_PORT
```

# Legacy compatibility

V0.1/V0.2 插件没有 runtime UUID。Bridge 会使用 `legacy:<name>` 作为兼容 key，并从电平近似推断 signal state。因此旧插件仍可使用，但**旧插件的同名多实例无法获得 V0.3 的完整重复实例安全性**。需要同名多实例时应升级到 V0.3 VST3。
