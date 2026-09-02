# AI Audio Analyzer Cherry Studio Skill

这个 Skill 用于：

- Cherry Studio
- AI Audio Analyzer.vst3 0.4+
- AI Audio Analyzer MCP v2 Bridge
- FL Studio MCP

它让模型正确读取 Spectrum、LUFS-S / LUFS-I、True Peak、RMS / Crest、Spectral Centroid / Rolloff / Flatness、Stereo Correlation、8-band Stereo Correlation、Signal State、Active Ratio 和轨道间 Spectrum Overlap，并用于混音诊断、Kick/Bass 冲突、Vocal masking、Mono compatibility、Mastering 和修改后的 A/B 验证。

## V0.4：Analyzer 与 FL Mixer 的确定对应

V0.4 向宿主公开一个布尔参数：

```text
Identify
```

每次这个参数从 `0→1` 或 `1→0`，该插件实例都会发送一次 `/aianalyzer/identify`，其中包含它自己的 runtime UUID。

模型已知自己刚刚通过 FL Studio MCP 操作的是哪一个 Mixer Track / Slot，因此可以立即调用：

```text
audio_bind_last_identified(fl_track_index, fl_track_name, slot)
```

建立：

```text
FL Mixer Track / Slot
        ↕
Analyzer runtime UUID
```

这个对应关系不是靠名字猜出来的。

推荐第一次分析工程时：

```text
扫描 FL Mixer
→ 找到所有 AI Audio Analyzer 插件槽
→ 逐个读取 Identify 当前值并取反
→ 每触发一个就立即 audio_bind_last_identified(...)
→ audio_instance_map()
→ 确认 discovery_complete
```

绑定完成后，优先使用：

```text
mixer:7/slot:9
```

或唯一的 FL Mixer Track 名称访问 Analyzer。一个 Mixer Track 中存在多个 Analyzer 时必须带 `slot`。

绑定和 runtime UUID 都是 session-scoped。重新打开工程或插件实例被重建后，应重新执行 Identify discovery。

## V0.3 Signal State

Analyzer 低于约 `-50 dBFS` 持续约 0.4 秒后进入无有效输入状态，重新高于约 `-48 dBFS` 才打开。此时 Bridge 会把无效的频谱与立体声指标返回为 `null`，而不是伪造 0；LUFS-I 和 session max True Peak 继续保留，LUFS-S 在连续静音约 3 秒后无效。

一个工程可以同时放很多实例，它们都发送到同一个 `127.0.0.1:9855`。每个实例有用户名称和 runtime UUID；Bridge 以 runtime UUID 为内部身份，所以同名实例不会互相覆盖。

## 安装

将整个 `ai-analyzer-flstudio` Skill 导入 Cherry Studio 的技能功能。如果当前版本支持 ZIP 导入可以直接导入 ZIP；如果要求文件夹形式，则使用：

```text
ai-analyzer-flstudio/
├── SKILL.md
└── references/
```

## 推荐同时启用的 MCP

- `ai-audio-analyzer`
- `fl-studio`

AI Audio Analyzer 负责读取声音结果，FL Studio MCP 负责读取/修改工程。

## 推荐 Agent 提示

```text
音乐制作与混音任务优先使用 ai-analyzer-flstudio Skill。
分析前先调用 audio_bridge_status、audio_list_tracks 和 audio_instance_map。
如果存在未绑定 Analyzer，并且 FL Studio MCP 能访问插件参数，先逐个翻转目标插件的 Identify 参数并立即调用 audio_bind_last_identified 建立 Mixer Track/Slot 映射。
绑定后优先用 mixer:index/slot:slot 或唯一 FL Mixer 名称选择 Analyzer，不靠插件显示名猜测。
无有效输入或 null 指标时不要进行频谱/立体声推断。
需要改变 FL Studio 工程时使用 fl-studio MCP；修改后用 Analyzer 做 Before/After 验证。
不要编造插件参数名或不存在的 MCP 工具。
```

## 测试提示词

```text
检查当前 Analyzer instance map。如果存在未绑定实例，告诉我哪些还没有和 FL Mixer 对应。
```

```text
扫描工程中的 AI Audio Analyzer，并通过 Identify 参数给每个实例建立 FL Mixer Track/Slot 映射。完成后输出 topology，不做混音修改。
```

```text
读取 Master 最近 10 秒数据。先确认绑定关系和 active_ratio，再分析 LUFS、True Peak、动态和立体声，只诊断。
```

```text
分析 Kick 和 Bass 最近 5 秒的频谱重叠。如果任一轨道没有有效输入，就不要给 EQ/sidechain 结论。
```
