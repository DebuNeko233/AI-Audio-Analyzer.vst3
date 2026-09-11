# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** 是一个面向 AI/LLM 辅助混音的 JUCE VST3 + MCP 音频测量、记忆与验证层。

它在 DAW 内持续测量音频，通过 OSC 输出结构化数据，并把测量结果按 DAW 时间保存在 MCP 中，让 Agent 即使过几秒再思考，也能查询“刚才/之前那一段发生了什么”，而不是假装自己一直实时听着 DAW。

当前产品版本：**1.2.0**。

## 系统边界

```text
AI Audio Analyzer VST3
  -> 实时安全的音频测量 + DAW transport 上下文

AI Audio Analyzer MCP
  -> Observe / Remember / Structure / Compare / Verify
  -> Song Memory / Section Map / Track Story
  -> P4b 历史深度证据回查
  -> 动态 / 单声道兼容 / Reference 对比
  -> 只允许控制 Analyzer 自己的 Analysis Profile

外部 DAW-control MCP
  -> 读取/修改/回读 DAW、工程和插件状态
```

FL Studio 控制层目前推荐配合 `rosasynthesiz/flstudio-mcp`。

Analyzer MCP **不是**通用 DAW 控制服务器。EQ、压缩、增益、Pan、路由、合成器、自动化、工程修改等仍由真正的 DAW-control MCP 完成。

## 当前接口状态

P4b PR #36 分支：

```text
Product version             1.2.0
MCP version                 1.2
OSC analysis protocol       1.2
Analyzer control revision   1
MCP tools                   48
Guide Resources             16
```

P4b 不新增 VST3 DSP 字段，不新增 OSC 字段，也不提升协议版本。

## 主要测量能力

- Sample Peak、RMS、Crest；
- LUFS-S / LUFS-I / True Peak；
- 4096 FFT、32 个对数频带、Centroid/Rolloff/Flatness；
- 全频与分频段 Stereo Correlation；
- Mid/Side、Side 频谱、Side/Mid、negative-cross；
- Spectral Flux、RMS Rise、低频时间变化；
- 12-bin Chroma、调性中心和单 F0 谐波证据；
- DAW 时间、PPQ、BPM、拍号、Loop/播放/录音状态；
- Analyzer 延迟、丢块和 Worker/FIFO 状态；
- 1 秒 Song Memory + 100 ms coverage；
- Section Map、Track Story、Section Relationships；
- P6a 动态分布；
- P7a 近期窗口单声道折叠能量证据；
- P4b 历史 Mid/Side、Stereo、Mono、Masking、Temporal 深度证据；
- P8a Session Reference 对比；
- 近期窗口和同区间 Before/After 验证。

`null` 表示**不可用**，不是 0。缺失 coverage 不能当成静音。

## 工程与实例身份

先调用：

```text
audio_project_identity_status()
```

目前：

```text
stable_project_id                       null
project_identity_confidence             UNRESOLVED
runtime_id scope                        live_plugin_instance
runtime_id persistent                   false
same-project reopen UUID stable         false
binding scope                           mcp_session
cross-project retained-state isolation  not guaranteed
```

重新打开同一个工程也会生成新的 Analyzer runtime UUID。因此 UUID 不是持久工程 ID/轨道 ID。若切换或重开工程后要求严格隔离，在接入权威工程身份之前，应重启 Analyzer MCP。

## Analyzer 与 Mixer 的确定性映射

VST3 暴露：

```text
Parameter ID: identify
Display name: Identify
```

通过 Identify 事件可以把 Analyzer runtime UUID 与真实 FL Mixer Track/Slot 绑定，例如：

```text
mixer:7/slot:9
```

不要在可用 Identify 时靠频谱或轨道名猜实例。

## Analysis Profile

```text
0 Eco       Core
1 Balanced  Core + Loudness + Spectrum + Stereo
2 Mix       Balanced + Temporal
3 Full      Mix + Semantic
```

控制工具：

```text
audio_set_analysis_profile(...)
audio_set_project_analysis_profile(...)
```

它们只改变 Analyzer 的测量计算量，不改变声音。

## Song Memory

```text
基础 bin              1 秒
coverage slot         100 ms
每实例最多            1200 bins
最长约                20 分钟
查询分辨率            1 / 2 / 5 / 10 / 15 / 30 秒
作用域                当前 MCP session
```

`transport_epoch` 是**每个 Analyzer 实例自己的连续播放 pass**。不同轨道不要求 epoch 数字相同，跨轨历史分析按 DAW 时间重叠对齐。

## Section / Track Story / Relationships

```text
audio_section_map(...)
audio_section_profile(...)
audio_track_story(...)
audio_section_relationships(...)
```

A/B/C 只是中性重复结构标签，不自动等于 Intro / Verse / Chorus / Drop。

`shortlist_priority` 只是“优先检查哪里”，不是 masking 概率、问题概率、质量分数或处理指令。

## P4b 历史深度回查 — PR #36

核心工具：

```text
audio_historical_detail(
  track,
  start_seconds=None,
  end_seconds=None,
  map_id=None,
  section_id=None,
  compare_track=None,
  minimum_coverage=0.8,
  max_masking_regions=8,
  temporal_low_hz=40,
  temporal_high_hz=160
)
```

它直接复用现有 1 秒 Song Memory 和 P4a range resolver，不再建立第二套历史系统，也**不保存 raw audio**。

只要当时对应 Analysis Profile 确实计算过这些特征，就可以回查：

- 32-band Mid/Side 历史频谱；
- 全频和分频段 Stereo；
- negative-cross / 低频 Stereo；
- 基于 Mid/Side 能量的历史 Mono fold-down；
- 1 秒级 Temporal 摘要；
- 可选 `compare_track` 的同区间 ERB Masking、Stereo、Mono、Temporal pair evidence。

边界必须明确：

```text
历史分辨率                     1 秒
亚秒历史对齐                   不支持
Raw audio                      不保存
历史缺失特征                   unavailable，不是 silence
跨轨 epoch 数字一致            不要求
历史 mono Sample Peak          不可用
历史 mono True Peak            不可用
quality score                  无
processing recommendation      无
```

专门的 `audio_masking_evidence()`、`audio_stereo_profile()`、`audio_temporal_*()` 仍是近期窗口工具，可以提供更细的当前帧上下文，不能把它们冒充成历史 Section 结果。

P4b 回归在 Python 3.12 CI 上对新增深度数据给出的浅层容器/数组估算约 **1918 B/bin**，按 1200 bins 约 **2.20 MiB/轨**。这只是内存上界的实现守卫，不是精确进程 RSS。

## P6a 动态分布

```text
audio_dynamics_distribution(...)
```

提供 coverage-aware 的 RMS、LUFS-S、Crest、观测 Sample Peak / True Peak 分布。

LUFS-S P90-P10 只是描述性 spread，**不是标准 EBU LRA**。任意区间 Integrated LUFS 和 PLR 仍明确不可用，不能从 pass 累计状态硬凑。

## P7a 单声道兼容

```text
audio_mono_compatibility(track, seconds=5.0)
```

P7a 本身仍是**近期窗口**工具。

历史区间/Section 的 1 秒级 Mono 能量证据由 P4b `audio_historical_detail()` 单独提供。直接 Mono Sample Peak / True Peak 仍未实现，属于可选 P7b。

## P8a Reference Engine

P8a 已合并，提供：

```text
audio_capture_reference(...)
audio_list_references()
audio_compare_reference(...)
```

Reference 是冻结的**近期窗口测量 profile**，不是复制的音频；只在当前 MCP session 中有效，也不代表整首歌。

P4b 有历史深度数据，并不意味着 P8a 自动获得“历史 Reference capture”。后续若要做，应显式设计新的 P8 层能力。

Reference 差异只是上下文，不是自动 EQ / Master Match 指令。

## 验证

近期窗口：

```text
audio_begin_verification(...)
audio_complete_verification(...)
audio_verification_status(...)
```

同 DAW 区间：

```text
audio_begin_range_verification(...)
audio_complete_range_verification(...)
audio_range_verification_status(...)
```

同区间模式按 coverage 选 pass，After 必须来自 baseline fence 之后的新测量，并且 `closed_loop_complete=true` 还要求外部 DAW-control MCP 的真实 host readback。

`controlled_comparison=true` 只表示技术上可比较，不表示声音更好。

## MCP 自描述

MCP 提供：

```text
Server instructions
Tool descriptions
aianalyzer://guide/* Resources
```

仓库/安装包里的 `skill/` 仍是长期指导文档的唯一源，MCP Resources 只是按需读取同一份 Markdown。

P4b PR #36 当前为 **48 tools / 16 Guide Resources**。不要机械调用全部工具，应先用高层工具缩小问题再深入。

## 安装包原则

支持：

```text
Windows x64
macOS Apple Silicon arm64
```

每个平台只生成一个最终 ZIP。面向普通用户的 Release 不包含 MCP Python 源码、`requirements.txt`、venv、PyInstaller `_internal`、开发配置或嵌套 ZIP。

Windows：解压一次后运行 `Install.cmd`。

macOS Apple Silicon：解压一次后运行 `Install.command`。当前为 ad-hoc 签名，不是 Apple notarized。

## License

MIT License，见 [LICENSE](LICENSE)。
