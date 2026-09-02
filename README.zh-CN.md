# AI Audio Analyzer

[English](README.md) | [简体中文](README.zh-CN.md)

**AI Audio Analyzer** 是一个基于 JUCE 的 VST3 插件，用于在 **AI / LLM 辅助音乐制作工作流**中提供可被机器直接读取的音频分析数据。

它不是让大模型去“看”频谱分析器界面，而是在 DAW 内部提取紧凑的音频特征，通过 OSC 发送给 Python MCP Bridge。Cherry Studio 或其他 MCP 客户端随后可以结构化读取响度、True Peak、频谱、立体声状态、信号有效性以及轨道之间的频谱重叠。

当前项目版本：**0.4.1**。

## 项目包含什么

整个项目拆成三个部分：

```text
AI Audio Analyzer
├─ VST3       DAW 内部的音频感知探针
├─ MCP        将音频数据结构化提供给 LLM
└─ Skill      告诉 Cherry Studio 如何正确分析和决策
```

GitHub Actions 生成的平台工件也采用相同的三件套结构：

```text
AI-Audio-Analyzer-macOS/
├─ AI Audio Analyzer.vst3
├─ mcp/
└─ skill/

AI-Audio-Analyzer-Windows/
├─ AI Audio Analyzer.vst3
├─ mcp/
└─ skill/
```

在仓库源码中，MCP 位于 `bridge/`，Cherry Studio Skill 位于 `skills/ai-analyzer-flstudio/`。

## 配套 FL Studio MCP

AI Audio Analyzer 负责 **感知**。要让模型真正读取、控制和修改 FL Studio 工程，本项目推荐与当前 Cherry Studio 工作流使用的 FL Studio MCP 配合：

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

两个 MCP 的职责是分开的：

```text
AI Audio Analyzer MCP   → 观察 / 测量 / 验证
FL Studio MCP           → 读取 / 控制 / 修改 FL Studio
```

组合后形成完整闭环：

```text
OBSERVE → DIAGNOSE → PLAN → CHANGE → READBACK → A/B
观察       诊断        计划      修改       回读       对比
```

## 整体架构

```text
FL Studio / DAW
│
├─ Mixer 4  Kick
│   └─ AI Audio Analyzer.vst3
├─ Mixer 7  Bass
│   └─ AI Audio Analyzer.vst3
├─ Mixer 12 Lead Vocal
│   └─ AI Audio Analyzer.vst3
└─ Master
    └─ AI Audio Analyzer.vst3
             │
             │ OSC UDP
             │ 默认 127.0.0.1:9855
             ▼
        Python Analyzer MCP
        ├─ 实时实例注册表
        ├─ 短时间历史缓存
        ├─ Signal State 过滤
        ├─ FL Mixer 实例映射
        ├─ 轨道间比较
        └─ MCP stdio Server
             │
             ▼
      Cherry Studio / LLM
        │               │
        │ 感知          │ 执行
        │               ▼
        │      rosasynthesiz/flstudio-mcp
        │               │
        └───────────────┴──> FL Studio
```

## 当前功能

### 音频分析

- 4096 点 FFT，Hann Window
- 1024 Sample Analysis Hop
- 20 Hz–20 kHz 的 32 个对数频谱特征
- Sample Peak dBFS / RMS dBFS / Crest Factor
- LUFS-S 短期响度
- 带 EBU R128 Gating 的 LUFS-I 综合响度
- True Peak dBTP 和 Session 最大 True Peak
- Spectral Centroid / 85% Spectral Rolloff / Spectral Flatness
- 全频段 Stereo Correlation
- Mid/Side Width Ratio
- 8 个分频段 Stereo Correlation：
  - 20–60 Hz
  - 60–120 Hz
  - 120–250 Hz
  - 250–500 Hz
  - 500 Hz–1 kHz
  - 1–2 kHz
  - 2–5 kHz
  - 5–20 kHz

响度和 True Peak 使用 `libebur128` 1.2.6。

### Signal State：区分“有声音”和“无有效输入”

AI Audio Analyzer 不会让很低的尾音无限参与频谱和立体声判断。

```text
关闭 Gate：低于约 -50 dBFS 持续约 0.4 秒
重新打开：高于约 -48 dBFS
```

2 dB 的迟滞用于避免信号在阈值附近反复跳变。

当 `signal_present=false` 时，MCP Bridge 会把频谱、Centroid、Rolloff、Flatness、Stereo Correlation、Width 和分频段 Correlation 视为“无有效测量”，而不是返回误导性的 0。

需要特别注意：

- LUFS-I 保留本次 Session 的累计值；
- Session Max True Peak 继续保留；
- 持续静音后 LUFS-S 会变为不可用；
- `audio_average()` 会返回 `active_ratio`，并且只使用有效 Active Frames 计算与音乐内容相关的平均结果。

### 多 Analyzer 实例

一个工程可以放任意多个 AI Audio Analyzer，并且所有实例共享同一个 OSC 端口：

```text
Kick ───┐
Bass ───┤
Vocal ──┼─> UDP 127.0.0.1:9855 ─> 一个 Analyzer MCP Bridge
Master ─┘
```

每个运行中的插件实例都有一个人类可读名称和一个当前 Live Instance 自动生成的 Runtime UUID。允许多个实例使用相同的人类名称，但发生歧义时 MCP Bridge 不会偷偷选择其中一个。

### 与 FL Studio Mixer Track 的确定性映射

0.4 版本加入宿主可见参数：

```text
Parameter ID: identify
Name: Identify
```

每次 `Identify` 参数发生变化，该插件实例都会发送一个 OSC Identify Event，其中包含当前实例的 Runtime UUID。

Identify 不依赖音频播放，因此即使 FL Studio 处于停止状态，也可以完成 Analyzer 实例发现。

与 [rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp) 配合时，推荐自动发现流程：

```text
FL Studio MCP
  ↓
选择 Mixer Track / Plugin Slot
  ↓
翻转 AI Audio Analyzer 的 Identify
  ↓
/aianalyzer/identify
  ↓
audio_last_identify()
  ↓
audio_bind_last_identified(Track Index, Track Name, Slot)
  ↓
audio_instance_map()
```

绑定完成后，模型可以直接使用：

```text
mixer:7/slot:9
```

确定访问某一个 Analyzer，而不是依赖 `Bass`、`Track` 等可能重复的名称。

## MCP 工具

当前 Analyzer Bridge 提供：

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
```

`audio_detect_masking()` 目前是**启发式频谱重叠检测**，不是完整心理声学 Masking 模型。真正判断是否存在听觉遮蔽仍要结合时间关系、编曲、瞬态、电平和音乐意图。

## 快速开始

### 1. 下载平台工件

进入最新成功的 GitHub Actions Build，下载：

```text
AI-Audio-Analyzer-macOS
```

或：

```text
AI-Audio-Analyzer-Windows
```

解压后顶层应该正好看到：

```text
AI Audio Analyzer.vst3
mcp/
skill/
```

### 2. 安装 VST3

macOS 用户级目录：

```text
~/Library/Audio/Plug-Ins/VST3/
```

macOS 系统级目录：

```text
/Library/Audio/Plug-Ins/VST3/
```

Windows 常用目录：

```text
C:\Program Files\Common Files\VST3
```

复制完成后，在 FL Studio 中重新扫描插件。

### 3. 安装 Analyzer MCP Python 环境

进入下载工件中的 `mcp/`：

```bash
cd mcp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

当前 Bridge 使用 **MCP Python SDK 2.x**，通过 **stdio** 与 Cherry Studio 通信。

### 4. 配置 Cherry Studio MCP

`command` 必须使用已经安装 `mcp` 和 `python-osc` 的 Python 环境。

```json
{
  "mcpServers": {
    "ai-audio-analyzer": {
      "command": "/absolute/path/to/mcp/.venv/bin/python",
      "args": [
        "/absolute/path/to/mcp/server.py"
      ],
      "env": {
        "AI_ANALYZER_OSC_HOST": "127.0.0.1",
        "AI_ANALYZER_OSC_PORT": "9855"
      }
    }
  }
}
```

下载工件中可以参考 `mcp/cherry-studio.example.json`；源码仓库中对应 `bridge/cherry-studio.example.json`。

不要在终端里长期运行一个 `server.py`，同时又让 Cherry Studio 再启动一个。UDP `9855` 应只由一个 Bridge Process 绑定。

### 5. 添加 FL Studio 控制 MCP

执行 / 控制 FL Studio 的一侧使用：

**[rosasynthesiz/flstudio-mcp](https://github.com/rosasynthesiz/flstudio-mcp)**

当你希望模型既能**分析声音**又能**操作 FL Studio**时，在 Cherry Studio 中同时启用 Analyzer MCP 和 FL Studio MCP。

### 6. 导入 Cherry Studio Skill

将下载工件中的 `skill/` 导入 Cherry Studio。

Skill 会告诉模型：

- 分析前先检查 Bridge 和 Signal State；
- 区分“测量事实、诊断推断、处理建议”；
- 不把 `null` 当成 0；
- 使用有效帧做窗口平均；
- 正确处理多个 Analyzer 实例和 FL Mixer 映射；
- 不编造不存在的插件参数；
- 修改后使用 Analyzer 做 Before / After 回读验证。

## 推荐的 FL Studio 工作流

1. 在所有希望 AI 观察的 Mixer Track 上插入 `AI Audio Analyzer`。
2. 所有 Analyzer 默认保持同一个 OSC Host/Port。
3. 在 Cherry Studio 中同时启用 Analyzer MCP 和 [FL Studio MCP](https://github.com/rosasynthesiz/flstudio-mcp)。
4. 让 Agent 扫描当前所有 Analyzer 实例。
5. 让 Agent 通过 `Identify` 自动建立 Mixer Track/Slot 映射。
6. 真正需要音频测量时再播放工程。
7. 混音判断优先使用 3–10 秒的 `audio_average()`，而不是单帧 Snapshot。

推荐初始化提示词：

```text
扫描当前 FL Studio 工程中的所有 AI Audio Analyzer，通过 Identify 建立与 Mixer Track/Slot 的映射，然后输出完整 Analyzer Topology，不要修改工程。
```

分析 Master：

```text
读取 Master 最近 10 秒的数据，分析 LUFS-S、LUFS-I、True Peak、动态和立体声，只诊断，不修改。
```

分析 Kick / Bass：

```text
比较 Kick 和 Bass 最近 5 秒的数据，重点检查 40–160 Hz 最值得处理的冲突，但不要因为有频谱重叠就默认必须 Sidechain。
```

检查低频 Mono Compatibility：

```text
检查 Master 20–120 Hz 的 Stereo Correlation，并判断是否存在真正值得处理的 Mono Compatibility 风险。
```

## OSC 协议

### Analysis Frame

地址：

```text
/aianalyzer/frame
```

协议保留旧版本前缀，以保证向后兼容。

```text
0      analyzer_name                 string
1      sample_rate                   float
2      plugin_timestamp              float
3      peak_db                       float
4      rms_db                        float
5      crest_db                      float
6      centroid_hz                   float
7      rolloff_hz                    float
8      flatness                      float
9      stereo_correlation            float
10     stereo_width                  float
11..42 spectrum bands               32 floats
43     lufs_s                        float
44     lufs_i                        float
45     true_peak_dbtp                float
46     max_true_peak_dbtp            float
47..54 band_stereo_correlation       8 floats
55     signal_present                int
56     detector_peak_db              float
57     silence_seconds               float
58     runtime_uuid                  string
```

### Identify Event

地址：

```text
/aianalyzer/identify
```

Identify Event 包含 Runtime UUID、Analyzer Name、时间戳以及供 Bridge 使用的协议 / Schema 标记，用于把某个 Live Plugin Instance 与 FL Studio Mixer Track/Slot 绑定。

## LUFS 与 True Peak

`libebur128` 提供面向 EBU R128 / ITU-R BS.1770 的响度和 True Peak 测量。

AI Audio Analyzer 维护持续存在的 Stereo Loudness State，并启用 Short-Term Loudness、Integrated Loudness、True Peak 和 Histogram-backed Integrated Loudness。

`LUFS-I` 从 Analyzer 最近一次 Reset/Prepare 开始累计。如果只循环播放了副歌，那么这个 LUFS-I 代表当前累计测量范围，而不是整首歌曲。

## Stereo Correlation

插件针对每个 4096 Sample FFT Window 计算复数 L/R Spectrum。每个分频段相关性使用归一化 Cross-Spectrum Energy：

```text
corr_band = Σ Re(XL · conj(XR)) / sqrt(Σ|XL|² · Σ|XR|²)
```

大致解释：

```text
+1     高度相关 / 接近 Mono
 0     左右弱相关 / 可能比较宽
<0     可能存在相位抵消风险
```

Correlation 必须结合对应频段实际能量判断。如果某个频段几乎没有声音，那么这个频段的 Correlation 没有足够分析价值。

## 实时安全设计

```text
Audio Thread
  └─ 把 L/R Sample 拷贝进预分配 SPSC FIFO

Analysis Thread
  ├─ 消费 Analysis Hop
  ├─ 更新 EBU R128 / True Peak
  ├─ 维护 FFT Window
  ├─ 计算 Spectrum / Stereo Features
  └─ 约 10 Hz 发送 OSC
```

Audio Callback 不执行 FFT、网络 IO 或 MCP 工作。如果分析线程跟不上，系统会丢弃分析输入，而不是阻塞 DAW 实时音频线程。

## macOS Gatekeeper

当前 CI 的 macOS Build 使用 ad-hoc 签名，并不是 Apple Developer ID + Notarization 的正式发行包。因此从 GitHub 下载后，macOS Gatekeeper 可能会阻止 FL Studio 加载插件。

开发阶段，把插件复制进 VST3 目录后可以移除 Quarantine：

```bash
xattr -dr com.apple.quarantine \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

然后验证 Bundle 签名：

```bash
codesign --verify --deep --strict --verbose=4 \
  "$HOME/Library/Audio/Plug-Ins/VST3/AI Audio Analyzer.vst3"
```

如果以后要面向普通用户无障碍分发，应增加 Developer ID 签名和 Apple Notarization。

## 从源码构建

环境要求：

- CMake 3.22+
- C++20 Compiler
- macOS：Xcode / Command Line Tools
- Windows：推荐 Visual Studio 2022
- CMake Configure 时需要网络访问

FetchContent 会自动下载 JUCE 8.0.8 和 libebur128 1.2.6。

### macOS Universal Build

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
  "-DCMAKE_OSX_ARCHITECTURES=arm64;x86_64"

cmake --build build --config Release --parallel
```

### Windows

```powershell
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release --parallel
```

生成的 VST3 位于 `build/AIAnalyzer_artefacts/` 下。

## CI 与打包逻辑

GitHub Actions 使用按路径判断的增量构建：

```text
Source/** / CMakeLists.txt / Plugin Resources
  → 重新构建 macOS + Windows VST3
  → 打包 VST3 + mcp/ + skill/

bridge/**
  → 验证 MCP
  → 重新打包 MCP + Skill Components
  → 不重新构建 VST3

skills/ai-analyzer-flstudio/**
  → 重新打包 MCP + Skill Components
  → 不重新构建 VST3

README / 普通文档
  → 不重新构建 VST3
```

## 当前限制

- 暂无 LUFS-M 输出；
- 暂无 Mid/Side Spectrum；
- 暂无 Chroma、Key、Pitch-Class 分析；
- Spectrum 是紧凑 FFT 机器特征，不是校准 SPL；
- Masking Detection 仍是相对频谱重叠，不是 Bark/ERB 心理声学模型；
- 分频段 Stereo Correlation 基于 FFT Window，需要结合频段能量解释；
- Runtime UUID 有意设计为 Session Scope，重新加载插件后可能变化；
- FL Mixer Track/Slot 映射需要 FL Studio 控制 MCP 或其他可以修改 Host Plugin Parameter 的控制通道配合；
- 插件用于观察音频，不主动修改音频信号。

## 仓库结构

```text
.
├─ Source/                         VST3 源码
├─ bridge/                         MCP v2 Bridge 源码
├─ skills/
│  └─ ai-analyzer-flstudio/        Cherry Studio Skill
├─ .github/workflows/build.yml     CI / Packaging
├─ CMakeLists.txt
├─ README.md
└─ README.zh-CN.md
```

## 版本演进

```text
0.2   LUFS-S / LUFS-I / True Peak / 8-band Stereo Correlation
0.3   Signal Gate、有效/无效测量状态、Runtime UUID、安全多实例
0.4   Host-visible Identify 参数、确定性 FL Mixer Track/Slot Mapping
0.4.1 平台工件统一为三件套：VST3 + mcp/ + skill/
```
