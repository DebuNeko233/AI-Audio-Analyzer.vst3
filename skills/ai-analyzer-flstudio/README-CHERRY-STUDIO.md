# AI Audio Analyzer Cherry Studio Skill

这个 Skill 用于：

- Cherry Studio
- AI Audio Analyzer.vst3 0.3+
- AI Audio Analyzer MCP v2 Bridge
- FL Studio MCP

它让模型正确读取 Spectrum、LUFS-S / LUFS-I、True Peak、RMS / Crest、Spectral Centroid / Rolloff / Flatness、Stereo Correlation、8-band Stereo Correlation、Signal State、Active Ratio 和轨道间 Spectrum Overlap，并用于混音诊断、Kick/Bass 冲突、Vocal masking、Mono compatibility、Mastering 和修改后的 A/B 验证。

## V0.3 关键行为

Analyzer 低于约 `-50 dBFS` 持续约 0.4 秒后进入无有效输入状态，重新高于约 `-48 dBFS` 才打开。此时 Bridge 会把无效的频谱与立体声指标返回为 `null`，而不是伪造 0；LUFS-I 和 session max True Peak 继续保留，LUFS-S 在连续静音约 3 秒后无效。

一个工程可以同时放很多实例，它们都发送到同一个 `127.0.0.1:9855`。每个实例有用户名称和 runtime UUID；如果两个实例同名，Bridge 不会覆盖，而会要求使用 runtime ID 或给实例改成唯一名称。

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

AI Audio Analyzer 负责读取声音结果，FL Studio MCP 负责修改工程。

## 推荐 Agent 提示

```text
音乐制作与混音任务优先使用 ai-analyzer-flstudio Skill。
分析前先调用 audio_bridge_status 和 audio_list_tracks，确认 signal_present、active_ratio、数据新鲜度和实例唯一性。
无有效输入或 null 指标时不要进行频谱/立体声推断。
如果 Analyzer 实例重名，使用 runtime id 或要求重命名，不要任意选择一个。
需要改变 FL Studio 工程时使用 fl-studio MCP；修改后用 Analyzer 做 Before/After 验证。
不要编造插件参数名或不存在的 MCP 工具。
```

## 测试提示词

```text
检查 AI Audio Analyzer Bridge 状态，并列出当前所有 Analyzer 实例、runtime id、signal state 和是否重名，不要修改工程。
```

```text
读取 Master 最近 10 秒数据。先确认 active_ratio，再分析 LUFS、True Peak、动态和立体声，只诊断。
```

```text
分析 Kick 和 Bass 最近 5 秒的频谱重叠。如果任一轨道没有有效输入，就不要给 EQ/sidechain 结论。
```

```text
检查 Master 20–120 Hz 的 stereo correlation，只有在该轨道 signal_present=true 时才判断 mono compatibility。
```
