#pragma once

#include <JuceHeader.h>

namespace aianalyzer
{
enum class UiLanguage : int
{
    English = 0,
    Chinese = 1
};

enum class UiText
{
    Instance,
    OscHost,
    Port,
    Profile,
    Apply,
    Settings,
    HideSettings,
    Language,
    English,
    Chinese,
    Subtitle,
    WaitingForAudio,
    SampleTruePeak,
    RmsCrest,
    LufsShortIntegrated,
    CorrWidth,
    Signal,
    NoSignal,
    Detector,
    Silence,
    SpectrumUnavailable,
    SessionMaxTp,
    SpectrumWaiting,
    SpectrumDisabled,
    NoActiveInput,
    Transport,
    Playing,
    Stopped,
    Recording,
    Loop,
    Pass,
    Unsupported,
    AnalysisHealth,
    Healthy,
    HighLatency,
    FifoPressure,
    DroppedAudio,
    Worker,
    Fifo,
    Lag,
    Drops,
    OscTx,
    Pending
};

inline juce::String uiText(UiLanguage language, UiText key)
{
    const bool zh = language == UiLanguage::Chinese;

    switch (key)
    {
        case UiText::Instance: return zh ? juce::String(L"实例") : "Instance";
        case UiText::OscHost: return zh ? juce::String(L"OSC 主机") : "OSC Host";
        case UiText::Port: return zh ? juce::String(L"端口") : "Port";
        case UiText::Profile: return zh ? juce::String(L"分析档位") : "Profile";
        case UiText::Apply: return zh ? juce::String(L"应用") : "Apply";
        case UiText::Settings: return zh ? juce::String(L"设置") : "Settings";
        case UiText::HideSettings: return zh ? juce::String(L"收起设置") : "Hide settings";
        case UiText::Language: return zh ? juce::String(L"语言") : "Language";
        case UiText::English: return "English";
        case UiText::Chinese: return juce::String(L"中文");
        case UiText::Subtitle: return zh ? juce::String(L"自适应音频分析 → OSC → MCP") : "Adaptive audio analysis → OSC → MCP";
        case UiText::WaitingForAudio: return zh ? juce::String(L"等待音频输入...") : "Waiting for audio...";
        case UiText::SampleTruePeak: return zh ? juce::String(L"采样峰值 / 真峰值") : "Sample / True Peak";
        case UiText::RmsCrest: return zh ? juce::String(L"RMS / 峰均比") : "RMS / Crest";
        case UiText::LufsShortIntegrated: return "LUFS-S / LUFS-I";
        case UiText::CorrWidth: return zh ? juce::String(L"相关度 / 宽度") : "Corr / Width";
        case UiText::Signal: return zh ? juce::String(L"有信号") : "SIGNAL";
        case UiText::NoSignal: return zh ? juce::String(L"无输入") : "NO INPUT";
        case UiText::Detector: return zh ? juce::String(L"检测器") : "Detector";
        case UiText::Silence: return zh ? juce::String(L"静音") : "Silence";
        case UiText::SpectrumUnavailable: return zh ? juce::String(L"频谱不可用") : "Spectrum unavailable";
        case UiText::SessionMaxTp: return zh ? juce::String(L"本次播放最大真峰值") : "Session max TP";
        case UiText::SpectrumWaiting: return zh ? juce::String(L"等待分析档位启用频谱") : "Spectrum waiting for active Analysis Profile";
        case UiText::SpectrumDisabled: return zh ? juce::String(L"当前分析档位已关闭频谱") : "Spectrum disabled by Analysis Profile";
        case UiText::NoActiveInput: return zh ? juce::String(L"无有效输入") : "No active input";
        case UiText::Transport: return zh ? juce::String(L"走带") : "TRANSPORT";
        case UiText::Playing: return zh ? juce::String(L"播放") : "PLAYING";
        case UiText::Stopped: return zh ? juce::String(L"停止") : "STOPPED";
        case UiText::Recording: return zh ? juce::String(L"录音") : "RECORDING";
        case UiText::Loop: return zh ? juce::String(L"循环") : "LOOP";
        case UiText::Pass: return zh ? juce::String(L"播放轮次") : "PASS";
        case UiText::Unsupported: return zh ? juce::String(L"宿主未提供") : "UNSUPPORTED";
        case UiText::AnalysisHealth: return zh ? juce::String(L"分析状态") : "ANALYSIS HEALTH";
        case UiText::Healthy: return zh ? juce::String(L"正常") : "HEALTHY";
        case UiText::HighLatency: return zh ? juce::String(L"分析延迟较高") : "HIGH LATENCY";
        case UiText::FifoPressure: return zh ? juce::String(L"FIFO 压力较高") : "FIFO PRESSURE";
        case UiText::DroppedAudio: return zh ? juce::String(L"发生音频丢块") : "DROPPED AUDIO";
        case UiText::Worker: return zh ? juce::String(L"工作线程") : "Worker";
        case UiText::Fifo: return "FIFO";
        case UiText::Lag: return zh ? juce::String(L"延迟") : "Lag";
        case UiText::Drops: return zh ? juce::String(L"丢块") : "Drops";
        case UiText::OscTx: return "OSC TX";
        case UiText::Pending: return zh ? juce::String(L"切换中") : "pending";
    }

    return {};
}
} // namespace aianalyzer
