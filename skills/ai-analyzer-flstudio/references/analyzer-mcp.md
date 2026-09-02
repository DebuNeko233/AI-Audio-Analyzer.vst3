# AI Audio Analyzer MCP Reference

当前主要工具：

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
```

## 推荐调用策略

```text
开始任何分析
audio_bridge_status()
→ audio_list_tracks()
→ audio_instance_map()
```

如果 `audio_instance_map().unbound_count > 0`，且 FL Studio MCP 可访问插件参数，优先先完成 V0.4 Identify 绑定，再做轨道级分析。

单轨快速检查：

```text
audio_average(track_selector, 5)
```

绑定完成后 `track_selector` 优先使用：

```text
mixer:7/slot:9
```

也可以使用唯一的 FL Mixer 轨道名，例如：

```text
Bass Sub
Lead Vocal
Master
```

runtime UUID 只作为机器级 fallback，不应成为跨工程会话的永久名称。

# V0.4 FL Studio <-> Analyzer Identify

V0.4 插件向宿主公开一个稳定参数：

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

这个参数不是传统的一次性按钮。**每次布尔值发生翻转都会发送一次 Identify 事件**。因此自动化流程应：

1. 用 FL Studio MCP 找到目标 Mixer Track 上的 `AI Audio Analyzer` 插件槽位；
2. 扫描该插件真实暴露的参数，找到显示名为 `Identify` 的参数；
3. 读取 `Identify` 当前值；
4. 将它设置为相反值；
5. 立即调用 `audio_last_identify()` 确认收到新的事件；
6. 立即调用 `audio_bind_last_identified(fl_track_index, fl_track_name, slot)`；
7. 对下一个 Analyzer 重复上述过程；
8. 最后调用 `audio_instance_map()` 验证 `discovery_complete=true` 或确认哪些实例仍未绑定。

不要假设 FL Studio MCP 的插件参数工具名称。先读取/扫描真实可用工具与参数，再执行。

## 为什么不能靠名字猜

一个工程可能存在：

```text
Mixer 4  Kick
Mixer 7  Bass Sub
Mixer 8  Bass Mid
Mixer 12 Lead Vocal
Mixer 20 Vocal Bus
```

而插件内部的人类名称可能仍然都是：

```text
Track
Track
Track
Track
Track
```

V0.4 的 Identify 事件直接携带该 live VST3 实例的 `runtime_uuid`。模型刚刚操作哪个 FL Mixer Track / Slot 是已知的，因此 Bridge 可以建立确定关系：

```text
FL Mixer 7 / Slot 9
        ↕
runtime_uuid = 64cd7181...
```

这不是字符串相似度匹配，也不是音频特征猜测。

## Identify 事件只能消费一次

`audio_bind_last_identified()` 会把最新 Identify 事件标记为已消费。

如果模型没有先翻转下一个插件的 `Identify`，却再次调用绑定工具，Bridge 会拒绝并提示：

```text
Latest Identify event was already consumed
```

这样可以避免同一个 runtime UUID 被误绑到两个 Mixer Track。

## 推荐完整自动发现流程

```text
FL Studio MCP: 枚举 Mixer Tracks
        ↓
找到每条轨道中的 AI Audio Analyzer slot
        ↓
Track A: Identify 当前 0 → 设置 1
        ↓
audio_last_identify()
        ↓
audio_bind_last_identified(A.index, A.name, slot)
        ↓
Track B: Identify 当前 1 → 设置 0（或按它自己的当前值取反）
        ↓
audio_last_identify()
        ↓
audio_bind_last_identified(B.index, B.name, slot)
        ↓
...
        ↓
audio_instance_map()
```

注意：每个插件实例的 `Identify` 当前值是独立的，所以应读取目标插件自己的当前参数值后取反，不要假设所有实例当前值相同。

# V0.4 selectors

绑定后 Bridge 支持：

```text
mixer:<track_index>
mixer:<track_index>/slot:<slot>
fl:<track_index>
fl:<track_index>/slot:<slot>
唯一的 FL Mixer track name
runtime UUID
唯一 runtime UUID 前缀
唯一 Analyzer 人类名称
```

推荐优先级：

```text
mixer:index/slot:slot
→ 唯一 FL Mixer track name
→ runtime UUID
→ Analyzer 人类名称
```

如果一个 Mixer Track 上放了多个 AI Audio Analyzer，必须使用包含 `slot` 的 selector。

# V0.4 instance map

`audio_instance_map()` 用来得到工程中的 Analyzer 拓扑，例如：

```json
{
  "instances": [
    {
      "runtime_id": "64cd7181...",
      "analyzer_name": "Track",
      "bound": true,
      "binding": {
        "fl_track_index": 7,
        "fl_track_name": "Bass Sub",
        "slot": 9
      },
      "selector": "mixer:7/slot:9"
    }
  ],
  "bound_count": 1,
  "unbound_count": 0,
  "discovery_complete": true
}
```

进行多轨混音分析前，如果 `discovery_complete=false`，优先解决未绑定实例，而不是靠名字猜它们对应哪条轨道。

绑定是 session-scoped。关闭/重新打开 DAW 或重新实例化插件后 runtime UUID 可以变化，需要重新执行 Identify discovery。

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
binding
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

# 多实例与共享 OSC

多个 AI Audio Analyzer 可以同时把 OSC 发到同一个：

```text
127.0.0.1:9855
```

只有 Python Bridge 绑定 UDP 9855；VST3 实例都是 sender，所以无需每实例分配端口。

每个 V0.3+ 插件实例发送：

```text
track = 用户可编辑的人类名称
id    = 当前 live 实例的 runtime UUID
```

Bridge 以 `id` 为内部 key，所以两个都叫 `Bass` 或 `Track` 的实例也不会互相覆盖。

# OSC schema

分析帧地址保持：

```text
/aianalyzer/frame
```

V0.4 新增独立 Identify 地址：

```text
/aianalyzer/identify
```

Identify 参数：

```text
0 runtime_uuid      string
1 analyzer_name     string
2 plugin_timestamp  float
3 schema_version    string
```

分析帧 V0.1/V0.2 前缀保持不变，V0.3 追加：

```text
55 signal_present      int
56 detector_peak_db    float
57 silence_seconds     float
58 runtime_uuid        string
```

环境变量继续保持：

```text
AI_ANALYZER_OSC_HOST
AI_ANALYZER_OSC_PORT
```

# Legacy compatibility

V0.1/V0.2 插件没有 runtime UUID，也没有 Identify 参数。Bridge 会使用 `legacy:<name>` 作为兼容 key，并从电平近似推断 signal state。因此旧插件仍可用于基础分析，但无法获得 V0.4 的确定性 Mixer Track / Slot 绑定。
