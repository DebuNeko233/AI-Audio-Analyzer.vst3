# AI Analyzer Cherry Studio Skill

这个 Skill 用于：

- Cherry Studio
- AI Analyzer.vst3
- AI Analyzer MCP v2 Bridge
- FL Studio MCP

它让模型学会正确读取：

- Spectrum
- LUFS-S / LUFS-I
- True Peak
- RMS / Crest Factor
- Spectral Centroid / Rolloff / Flatness
- Stereo Correlation
- 8-band Stereo Correlation
- Track-to-track Spectrum Overlap

并将这些数据用于：

- 混音诊断
- Kick / Bass 冲突
- Vocal masking
- 立体声 / Mono compatibility
- Mastering 诊断
- FL Studio MCP 修改后的 A/B 验证

## 安装

将整个 `ai-analyzer-flstudio` Skill 导入 Cherry Studio 的技能功能。

如果当前 Cherry Studio 版本支持 ZIP 导入，可以直接选择 ZIP。

如果要求文件夹形式，则解压后导入：

```text
ai-analyzer-flstudio/
├── SKILL.md
└── references/
```

## 推荐同时启用的 MCP

- `ai-analyzer`
- `fl-studio`

AI Analyzer 负责读取声音结果，FL Studio MCP 负责修改工程。

## 推荐 Agent 提示

```text
音乐制作与混音任务优先使用 ai-analyzer-flstudio Skill。
分析前先读取 AI Analyzer 数据，不根据主观描述直接修改。
需要改变 FL Studio 工程时使用 fl-studio MCP。
所有重要修改尽量做 Before/After Analyzer 对比。
不要编造插件参数名或不存在的 MCP 工具。
```

## 测试提示词

```text
列出 AI Analyzer 当前能看到的所有轨道，不要修改工程。
```

```text
读取 Master 最近 10 秒数据，分析 LUFS、True Peak、动态和立体声，只诊断。
```

```text
分析 Kick 和 Bass 最近 5 秒的频谱重叠，告诉我真正值得处理的问题。
```

```text
检查 Master 20–120 Hz 的 stereo correlation，判断是否有 mono compatibility 风险。
```

```text
先分析 Vocal 与 Synth 的遮蔽，再决定是否需要 EQ，不要直接修改。
```
