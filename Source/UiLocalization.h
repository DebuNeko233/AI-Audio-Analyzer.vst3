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

    // Keep localized wide-string payloads in universal character escapes.
    // This makes the compiled UI independent of the source-file/system code page;
    // MSVC is additionally built with /utf-8 as a repository-wide safeguard.
    switch (key)
    {
        case UiText::Instance: return zh ? juce::String(L"\u5b9e\u4f8b") : "Instance";
        case UiText::OscHost: return zh ? juce::String(L"OSC \u4e3b\u673a") : "OSC Host";
        case UiText::Port: return zh ? juce::String(L"\u7aef\u53e3") : "Port";
        case UiText::Profile: return zh ? juce::String(L"\u5206\u6790\u6863\u4f4d") : "Profile";
        case UiText::Apply: return zh ? juce::String(L"\u5e94\u7528") : "Apply";
        case UiText::Settings: return zh ? juce::String(L"\u8bbe\u7f6e") : "Settings";
        case UiText::HideSettings: return zh ? juce::String(L"\u6536\u8d77\u8bbe\u7f6e") : "Hide settings";
        case UiText::Language: return zh ? juce::String(L"\u8bed\u8a00") : "Language";
        case UiText::English: return "English";
        case UiText::Chinese: return juce::String(L"\u4e2d\u6587");
        case UiText::Subtitle: return zh ? juce::String(L"\u81ea\u9002\u5e94\u97f3\u9891\u5206\u6790 \u2192 OSC \u2192 MCP") : "Adaptive audio analysis \xe2\x86\x92 OSC \xe2\x86\x92 MCP";
        case UiText::WaitingForAudio: return zh ? juce::String(L"\u7b49\u5f85\u97f3\u9891\u8f93\u5165...") : "Waiting for audio...";
        case UiText::SampleTruePeak: return zh ? juce::String(L"\u91c7\u6837\u5cf0\u503c / \u771f\u5cf0\u503c") : "Sample / True Peak";
        case UiText::RmsCrest: return zh ? juce::String(L"RMS / \u5cf0\u5747\u6bd4") : "RMS / Crest";
        case UiText::LufsShortIntegrated: return "LUFS-S / LUFS-I";
        case UiText::CorrWidth: return zh ? juce::String(L"\u76f8\u5173\u5ea6 / \u5bbd\u5ea6") : "Corr / Width";
        case UiText::Signal: return zh ? juce::String(L"\u6709\u4fe1\u53f7") : "SIGNAL";
        case UiText::NoSignal: return zh ? juce::String(L"\u65e0\u8f93\u5165") : "NO INPUT";
        case UiText::Detector: return zh ? juce::String(L"\u68c0\u6d4b\u5668") : "Detector";
        case UiText::Silence: return zh ? juce::String(L"\u9759\u97f3") : "Silence";
        case UiText::SpectrumUnavailable: return zh ? juce::String(L"\u9891\u8c31\u4e0d\u53ef\u7528") : "Spectrum unavailable";
        case UiText::SessionMaxTp: return zh ? juce::String(L"\u672c\u6b21\u64ad\u653e\u6700\u5927\u771f\u5cf0\u503c") : "Session max TP";
        case UiText::SpectrumWaiting: return zh ? juce::String(L"\u7b49\u5f85\u5206\u6790\u6863\u4f4d\u542f\u7528\u9891\u8c31") : "Spectrum waiting for active Analysis Profile";
        case UiText::SpectrumDisabled: return zh ? juce::String(L"\u5f53\u524d\u5206\u6790\u6863\u4f4d\u5df2\u5173\u95ed\u9891\u8c31") : "Spectrum disabled by Analysis Profile";
        case UiText::NoActiveInput: return zh ? juce::String(L"\u65e0\u6709\u6548\u8f93\u5165") : "No active input";
        case UiText::Transport: return zh ? juce::String(L"\u8d70\u5e26") : "TRANSPORT";
        case UiText::Playing: return zh ? juce::String(L"\u64ad\u653e") : "PLAYING";
        case UiText::Stopped: return zh ? juce::String(L"\u505c\u6b62") : "STOPPED";
        case UiText::Recording: return zh ? juce::String(L"\u5f55\u97f3") : "RECORDING";
        case UiText::Loop: return zh ? juce::String(L"\u5faa\u73af") : "LOOP";
        case UiText::Pass: return zh ? juce::String(L"\u64ad\u653e\u8f6e\u6b21") : "PASS";
        case UiText::Unsupported: return zh ? juce::String(L"\u5bbf\u4e3b\u672a\u63d0\u4f9b") : "UNSUPPORTED";
        case UiText::AnalysisHealth: return zh ? juce::String(L"\u5206\u6790\u72b6\u6001") : "ANALYSIS HEALTH";
        case UiText::Healthy: return zh ? juce::String(L"\u6b63\u5e38") : "HEALTHY";
        case UiText::HighLatency: return zh ? juce::String(L"\u5206\u6790\u5ef6\u8fdf\u8f83\u9ad8") : "HIGH LATENCY";
        case UiText::FifoPressure: return zh ? juce::String(L"FIFO \u538b\u529b\u8f83\u9ad8") : "FIFO PRESSURE";
        case UiText::DroppedAudio: return zh ? juce::String(L"\u53d1\u751f\u97f3\u9891\u4e22\u5757") : "DROPPED AUDIO";
        case UiText::Worker: return zh ? juce::String(L"\u5de5\u4f5c\u7ebf\u7a0b") : "Worker";
        case UiText::Fifo: return "FIFO";
        case UiText::Lag: return zh ? juce::String(L"\u5ef6\u8fdf") : "Lag";
        case UiText::Drops: return zh ? juce::String(L"\u4e22\u5757") : "Drops";
        case UiText::OscTx: return "OSC TX";
        case UiText::Pending: return zh ? juce::String(L"\u5207\u6362\u4e2d") : "pending";
    }

    return {};
}
} // namespace aianalyzer
