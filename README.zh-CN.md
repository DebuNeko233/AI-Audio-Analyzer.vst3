# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** 是一套面向 AI / LLM 音乐制作工作流的 **VST3 + MCP 音频测量层**。VST3 在 DAW 内部测量真实音频，MCP 把数据结构化提供给模型，配套 Skill 只负责教模型如何正确调用 MCP、理解参数和判断数据有效性，不预设某一种混音风格。

当前产品版本：**0.6.0**。

## 项目结构

```text
AI Audio Analyzer
├─ VST3    在 DAW 内进行实时安全的音频测量
├─ MCP     向模型提供结构化测量、比较与验证工具
└─ Skill   MCP 调用技巧 + 参数技术语义
```

需要控制 FL Studio 时，推荐配合独立的控制 MCP：

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

```text
AI Audio Analyzer MCP   → 观察 / 测量 / 比较 / 验证
FL Studio MCP           → 读取 / 控制 / 修改 FL Studio
```

Analyzer 本身保持测量导向。Skill 不提供固定 LUFS 目标、EQ 配方、强制 Sidechain 规则或其他风格化混音策略。

## 整体架构

```text
FL Studio / DAW
│
├─ Mixer Track A ─ AI Audio Analyzer.vst3
├─ Mixer Track B ─ AI Audio Analyzer.vst3
└─ Master        ─ AI Audio Analyzer.vst3
                      │
                      │ OSC UDP 127.0.0.1:9855
                      ▼
              AI Audio Analyzer MCP
              ├─ Live Instance Registry
              ├─ Signal Validity
              ├─ FL Track/Slot 确定绑定
              ├─ Recent History Window
              ├─ Project Overview / A-B Snapshot
              └─ Temporal Comparison
                      │
                      ▼
               Cherry Studio / LLM
```

Audio Callback 只把 Sample 写入预分配的 SPSC FIFO。FFT、响度、Temporal Analysis、OSC 和 MCP 都不在实时音频线程上执行。

## 当前能力

### 核心测量

- 4096 点 FFT，Hann Window，1024 Sample Hop
- 20 Hz–20 kHz 的 32 个对数频谱 Band
- Sample Peak dBFS / RMS dBFS / Crest Factor
- 基于 `libebur128` 的 LUFS-S / LUFS-I
- 当前 True Peak 与 Session Max True Peak dBTP
- Spectral Centroid / 85% Rolloff / Flatness
- Full-band Stereo Correlation
- Mid/Side Width Ratio
- 8 个分频段 Stereo Correlation

### V0.3 Signal Validity

```text
Gate Close   低于约 -50 dBFS 持续约 0.4 s
Gate Reopen  高于约 -48 dBFS
```

当 `signal_present=false` 时，依赖有效声音内容的 Spectrum / Stereo 指标会返回 unavailable，而不是伪造 0。`null` 的含义始终是“当前没有有效测量”，不是数字 0。

### V0.4 多实例确定映射

每个 Live VST3 实例都有 Session-scoped Runtime UUID，并向宿主公开：

```text
Parameter ID: identify
Display name: Identify
Type: Boolean
```

每次 `Identify` 状态翻转都会发送 `/aianalyzer/identify`。模型知道自己刚操作的是哪个 FL Mixer Track / Slot，因此可以建立：

```text
FL Mixer Track / Slot
        ↕
Analyzer Runtime UUID
```

绑定后优先使用：

```text
mixer:7/slot:9
```

而不是根据重复名称或声音内容猜测实例。

### V0.5 Project Intelligence / A-B

MCP 提供工程准备度、最近窗口 Overview 和 Session 内 Snapshot，使模型不需要每次都串联大量底层调用。

### V0.6 Temporal Analysis

VST3 0.6 在内部 FFT Hop 速率上计算时间特征，并汇总进约 10 Hz 的 OSC 数据：

```text
temporal_window_seconds
spectral_flux_mean
spectral_flux_peak
rms_rise_peak_db
low_band_energy_db   # FFT-derived 40–160 Hz Energy
```

MCP 新增：

```text
audio_temporal_profile(track, seconds=5)
audio_temporal_compare(track_a, track_b, seconds=5,
                       low_hz=40, high_hz=160,
                       alignment_tolerance_ms=80)
```

`audio_temporal_profile()` 用于汇总 Spectral Flux、快速 RMS Rise、40–160 Hz 能量变化以及基于显式阈值的 Onset/Change Candidate。

`audio_temporal_compare()` 会对齐两个 Analyzer Stream，并返回所选频段的 Envelope Correlation、Co-active Ratio 和 Normalized Temporal Overlap。这些都是**测量 / 启发式证据**，不是自动混音指令，也不是完整心理声学 Masking 概率。

## MCP 工具

MCP 0.6 当前共 **18 个工具**：

```text
audio_bridge_status()
audio_list_tracks()
audio_last_identify()
audio_bind_last_identified(fl_track_index, fl_track_name, slot)
audio_instance_map()
audio_snapshot(track)
audio_average(track, seconds)
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
audio_temporal_compare(track_a, track_b, seconds=5,
                       low_hz=40, high_hz=160,
                       alignment_tolerance_ms=80)
```

`audio_detect_masking()` 目前仍是启发式频谱重叠证据。V0.6 增加了时间维度，但还不是完整 Bark/ERB 心理声学 Masking Model。

## 推荐安装方式

面向普通用户的 GitHub Release 与开发阶段 Artifact 分开。

当前 Release 平台：

```text
Windows x64
macOS Apple Silicon arm64
```

**不再提供 Intel macOS / x86_64 包。**

Release 懒人包包含：

```text
AI Audio Analyzer.vst3
mcp/
├─ runtime/   PyInstaller Standalone MCP
└─ source/    Python 源码备用
skill/
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
平台自动安装脚本
```

普通用户**不需要自己安装 Python、pip、venv、MCP SDK，也不需要访问 PyPI**。

### Windows

解压后双击：

```text
Install.cmd
```

安装器会复制 VST3、安装 Standalone MCP、执行内建 Self-test、复制 Skill，并生成 `cherry-studio-mcp.json`。

### macOS Apple Silicon

解压后双击：

```text
Install.command
```

如果 Gatekeeper 阻止脚本本身，可右键 → **打开**，或执行：

```bash
bash ./install.sh
```

安装器会安装 arm64 VST3，移除 Quarantine，验证/必要时修复本地 ad-hoc 签名，安装 arm64 Standalone MCP、运行 Self-test、复制 Skill，并生成 Cherry Studio 配置。

当前 GitHub Build 是 **ad-hoc signed，不是 Apple Developer ID Notarized**。

完整中英文教程都随 Release 打包：`INSTALL.zh-CN.md` / `INSTALL.en.md`。

## 开发者：Python 源码模式

正常用户不需要这一节。源码模式主要用于开发 Bridge、调试或 Standalone Runtime 的特殊 fallback。

要求：

- Python 3.10+
- 推荐 Python 3.12
- `bridge/requirements.txt`

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r bridge/requirements.txt
AI_ANALYZER_SELF_TEST=1 python bridge/server_v06.py
```

当前源码入口是：

```text
bridge/server_v06.py
```

`bridge/cherry-studio.example.json` 提供源码模式示例。

## Cherry Studio + FL Studio 工作流

新工程 / 新 Session 推荐：

```text
audio_project_status()
↓
如果需要：逐个 Identify 建立 Track/Slot Mapping
↓
audio_instance_map()
↓
按问题选择 Overview / Average / Temporal Tool
```

修改前后测量：

```text
audio_capture_snapshot("before", 5)
↓
通过 FL Studio MCP 修改工程
↓
audio_capture_snapshot("after", 5)
↓
audio_compare_snapshots("before", "after")
```

Skill 只解释 MCP 用法和参数语义；具体音乐判断由用户目标、音乐上下文和模型自身推理决定。

## OSC 协议

分析帧地址：

```text
/aianalyzer/frame
```

协议保持 Append-only：

```text
0      analyzer_name
1      sample_rate
2      plugin_timestamp
3      peak_db
4      rms_db
5      crest_db
6      centroid_hz
7      rolloff_hz
8      flatness
9      stereo_correlation
10     stereo_width
11..42 32 spectrum bands
43     lufs_s
44     lufs_i
45     true_peak_dbtp
46     max_true_peak_dbtp
47..54 8 band stereo correlations
55     signal_present
56     detector_peak_db
57     silence_seconds
58     runtime_uuid
59     temporal_window_seconds
60     spectral_flux_mean
61     spectral_flux_peak
62     rms_rise_peak_db
63     low_band_energy_db
64     frame_schema_version = "0.6"
```

Identify 地址仍然是：

```text
/aianalyzer/identify
```

V0.6 没有改变 V0.4 Identify Schema。

## Temporal 参数简要语义

- `spectral_flux_*`：相邻归一化频谱分布的正向变化，刻意降低单纯整体 Gain 缩放的影响。
- `rms_rise_peak_db`：当前 Temporal Aggregate 内最大的相邻窗口正向 RMS 增量。
- `low_band_energy_db`：FFT-derived 40–160 Hz 能量特征，不是校准 SPL。
- `band_envelope_correlation`：两个时间对齐所选频段能量包络的 Pearson Correlation。
- `normalized_band_temporal_overlap`：两轨分别按自身窗口峰值归一化后，描述同时占用所选频段的相对程度。
- `onset/change candidate`：基于工具明确返回阈值的启发式候选，不是 Ground-truth Onset Label。

## 从源码构建 VST3

要求：

- CMake 3.22+
- C++20 Compiler
- JUCE 8.0.8 由 CMake FetchContent 获取
- libebur128 1.2.6 由 CMake FetchContent 获取

macOS 当前开发/发布策略为 arm64：

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
  -DCMAKE_OSX_ARCHITECTURES=arm64
cmake --build build --config Release --parallel
```

Windows：

```powershell
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --parallel
```

## CI 与 Release

开发 CI 按路径增量执行：

```text
Source/** / CMakeLists.txt
→ Windows + macOS arm64 重新构建 VST3

bridge/**
→ 验证 / 打包 MCP + Skill

skills/**
→ 验证 / 打包 MCP + Skill

release/** / release workflow
→ 验证安装器和 Release 逻辑

纯文档改动
→ 不重新构建 VST3
```

面向用户的手动 Release Workflow：

```text
.github/workflows/release.yml
```

它负责构建 Standalone MCP、运行 Self-test、重新构建平台 VST3、组装懒人包、生成 SHA256 并发布 / 更新 GitHub Release。

## 当前限制

- 暂无 LUFS-M；
- 暂无 Mid/Side Spectrum；
- 暂无 Chroma / Key / Pitch-class；
- Masking 仍是启发式证据，不是完整 Bark/ERB 心理声学模型；
- V0.6 时间比较受约 10 Hz OSC 更新频率和对齐容差限制；
- Onset Candidate 是 Frame-level Change Candidate，不是 Sample-accurate 标注；
- Runtime UUID 和 FL Binding 是 Session-scoped；
- macOS Release 仅 arm64，且尚未 Notarize；
- 插件只观察音频，不主动改变音频信号。

## 仓库结构

```text
.
├─ Source/                          VST3 源码
├─ bridge/
│  ├─ server.py                     稳定 Core Bridge
│  ├─ server_v05.py                 Project Intelligence Layer
│  ├─ project_tools.py
│  ├─ server_v06.py                 当前 MCP Entry Point
│  └─ temporal_tools.py
├─ skills/ai-analyzer-flstudio/     中立的 MCP Usage Skill
├─ release/                         懒人包安装器与教程
├─ .github/workflows/build.yml      开发 CI
├─ .github/workflows/release.yml    手动 Release Workflow
├─ CMakeLists.txt
├─ AGENT.md                         Agent / Maintainer 规约与路线图
├─ README.md
└─ README.zh-CN.md
```

## 版本演进 / 路线图

```text
0.2   LUFS / True Peak / 8-band Stereo Correlation
0.3   Signal Validity + Runtime UUID
0.4   Identify + FL Mixer Track/Slot 确定映射
0.4.1 Packaging / Installer Foundation
0.5   Project Overview + Snapshot A/B
0.6   Temporal Descriptors + Time-aligned Band Envelope Comparison

下一阶段：
0.7   更强 Masking Evidence（Bark/ERB + Level + Temporal Weighting）
0.8   更深入 Mid/Side Analysis
0.9   适合由音频推断的 Music-semantic Measurements
1.0   Reliable Closed-loop Measurement System
```
