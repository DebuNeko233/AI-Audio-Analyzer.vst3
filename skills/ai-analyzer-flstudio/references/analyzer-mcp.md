# AI Audio Analyzer MCP 调用参考

本文件只描述工具选择、调用顺序、实例定位和结果有效性，不提供具体混音风格或处理方案。

## 当前工具

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
```

共 16 个工具。

## 调用层级

优先从高层工具开始，信息不够时再下钻。

### 工程准备度

```text
audio_project_status()
```

优先用于判断：

- 是否存在 live Analyzer；
- 是否全部绑定；
- 是否有 stale stream；
- 当前是否有有效音频输入；
- 是否存在重复名称；
- Master 是否能确定。

不要为了得到同样的信息无条件先调用多个底层工具。

### 工程窗口概览

```text
audio_mix_overview(10)
```

一次获取多个实例最近窗口的核心测量值和潜在 spectral overlap candidates。

`potential_spectral_conflicts` 是 heuristic candidate list，不代表听觉问题已经被证明。

### 单实例稳定窗口

```text
audio_average(track, 5)
```

适合查询最近一个时间窗口的稳定统计。

### 单实例瞬时状态

```text
audio_snapshot(track)
```

只表示最新安全快照，不应自动扩展成长期趋势。

## V0.4 Identify：FL Mixer ↔ Analyzer 确定绑定

插件向宿主公开：

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

每次布尔值翻转都会发送一个 `/aianalyzer/identify` 事件，包含目标 live VST3 实例的 runtime UUID。

对每个 AI Audio Analyzer 实例：

1. 用 FL Studio MCP 找到真实 Mixer Track / Slot；
2. 扫描该插件真实公开参数；
3. 找到 `Identify`；
4. 读取当前值；
5. 将值设为相反值；
6. 立即调用 `audio_last_identify()`；
7. 确认事件新鲜且 `consumed=false`；
8. 立即调用 `audio_bind_last_identified(fl_track_index, fl_track_name, slot)`；
9. 最后调用 `audio_instance_map()` 验证所有绑定。

不要假设 FL Studio MCP 的参数读取/设置工具名称；使用当前实际暴露的工具。

### Identify 事件只能消费一次

绑定成功后该事件会被标记 consumed。如果再次绑定同一个事件，Bridge 应拒绝。

如果最新事件已 consumed：

```text
重新翻转目标实例 Identify
→ 读取新的 audio_last_identify()
→ 再绑定
```

### 为什么不能只靠名称

插件显示名可能重复，例如多个实例都叫：

```text
Track
```

runtime UUID 才是 live 实例身份，而 FL Mixer Track/Slot 是宿主位置身份。Identify 用于把二者确定关联。

## Selector

绑定后支持的常用 selector：

```text
mixer:<track_index>/slot:<slot>
mixer:<track_index>
fl:<track_index>/slot:<slot>
fl:<track_index>
唯一 FL Mixer Track 名称
runtime UUID
唯一 runtime UUID 前缀
唯一 Analyzer 显示名
```

推荐优先级：

```text
mixer:index/slot:slot
→ 唯一 FL Mixer Track 名称
→ runtime UUID
→ 唯一 Analyzer 显示名
```

同一 Mixer Track 上存在多个 Analyzer 时必须包含 `slot`。

## `audio_instance_map()`

用于查看当前 Analyzer 与 FL Mixer 的绑定拓扑。

关注：

```text
bound_count
unbound_count
discovery_complete
instances[].runtime_id
instances[].binding
instances[].selector
```

`discovery_complete=false` 时，如果任务依赖确定轨道身份，应优先完成 Identify，而不是靠名称或音频内容猜测。

runtime UUID / binding 都是 session-scoped。

## Signal State 与有效性

Signal detector 当前约为：

```text
close threshold   -50 dBFS
reopen threshold  -48 dBFS
hold              0.4 s
```

内容相关字段读取前检查：

```text
signal_present
analysis_valid
active_ratio
```

当无有效信号时，Bridge 会将不适合解释的频谱和立体声字段返回为 `null` / unavailable。

统一规则：

```text
null = 当前无有效测量
null ≠ 0
```

详细字段语义见 `parameters.md`。

## `audio_average()`

常见返回：

```text
window_seconds
frames
active_frames
active_seconds
active_ratio
signal_present
analysis_valid
binding
```

内容相关的频谱、立体声、Crest、LUFS-S 等统计只使用 active frames。

例如：

```json
{
  "window_seconds": 5,
  "frames": 50,
  "active_frames": 10,
  "active_ratio": 0.2,
  "analysis_valid": true
}
```

这只表示该窗口约 20% 的帧有有效输入。

## `audio_compare_tracks()`

用于比较两个实例的相对频谱特征。调用前确保两个实例都能被唯一解析并有有效 `bands_db`。

如果任一实例没有有效频谱，工具可能返回 unavailable，而不是伪造比较结果。

## `audio_detect_masking()`

这是当前项目对频谱重叠的启发式工具。不要因为函数名包含 `masking` 就把结果写成心理声学遮蔽的确定事实。

适合用途：

```text
定位值得继续查看的频谱重叠候选
```

不适合直接推导：

```text
必须采取某种处理动作
```

## `audio_stereo_bands()`

返回 8 段 Stereo Correlation。

如果当前无有效信号或立体声数据不可用，应接受 unavailable/null，不要用默认 0 替代。

## `audio_master_status()`

提供指定 Master/目标实例的常用技术字段汇总。它只是数据入口，不编码任何固定 mastering target。

## V0.5 Snapshot A/B

### Capture

```text
audio_capture_snapshot("before", 5)
```

Snapshot 保存当前 Bridge session 内的项目级窗口测量。

### List

```text
audio_list_snapshots()
```

用于确认当前保存了哪些 Snapshot。

### Compare

```text
audio_compare_snapshots("before", "after")
```

Delta 定义：

```text
After - Before
```

A/B 时尽量保持：

- 相同音乐片段；
- 相近窗口长度；
- 可比的 `active_ratio`；
- 实例 binding 没有发生变化。

LUFS-I 是 session 累积量，因此短窗口 A/B 时不要误认为它是两个独立 Integrated 测量。

## V0.5 Project Overview

`audio_mix_overview()` 返回的 `spectral_regions` 是频率范围聚合字段，`potential_spectral_conflicts` 是 heuristic overlap 排序。

这些结果适合作为下一步工具调用的导航信息。例如先 Overview，再选择某两个 selector 做 `audio_compare_tracks()`。

不要把 Overview 的候选列表自动转换成具体音乐处理建议。

## 多实例与 OSC

多个 VST3 实例都可以发送到：

```text
127.0.0.1:9855
```

VST3 是 sender，Python MCP Bridge 是 UDP listener，因此不需要为每个 Analyzer 分配不同端口。

如果 Cherry Studio 启动了 Bridge，不要同时在终端再启动第二个 Bridge 占用同一个 UDP 端口。

## 推荐技术调用模式

工程未知：

```text
audio_project_status()
→ 必要时 Identify mapping
→ audio_mix_overview()
→ 按问题下钻
```

单实例：

```text
audio_average(selector, seconds)
```

瞬时排查：

```text
audio_snapshot(selector)
```

A/B 测量：

```text
audio_capture_snapshot("before")
→ 外部状态发生变化
→ audio_capture_snapshot("after")
→ audio_compare_snapshots("before", "after")
```

整个过程中，工具返回的数据只作为测量事实。具体音乐风格判断不由本 Reference 规定。