#pragma once

#include <JuceHeader.h>
#include "PluginProcessor.h"
#include "UiLocalization.h"

class AIAnalyzerAudioProcessorEditor final : public juce::AudioProcessorEditor,
                                             private juce::Timer
{
public:
    explicit AIAnalyzerAudioProcessorEditor(AIAnalyzerAudioProcessor&);
    ~AIAnalyzerAudioProcessorEditor() override = default;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    void timerCallback() override;
    void applyConfig();
    void updateLocalizedText();
    void updateProfileButtons();
    void updateSettingsVisibility();
    void setProfileFromUi(int profileIndex);
    void drawSpectrum(juce::Graphics&, juce::Rectangle<float> bounds) const;
    aianalyzer::UiLanguage currentLanguage() const noexcept;

    AIAnalyzerAudioProcessor& ownerProcessor;

    juce::Label instanceLabel;
    juce::Label hostLabel;
    juce::Label portLabel;
    juce::Label profileLabel;
    juce::Label languageLabel;
    juce::TextEditor instanceEditor;
    juce::TextEditor hostEditor;
    juce::TextEditor portEditor;
    juce::ComboBox languageBox;
    juce::TextButton ecoButton { "Eco" };
    juce::TextButton balancedButton { "Balanced" };
    juce::TextButton mixButton { "Mix" };
    juce::TextButton fullButton { "Full" };
    juce::TextButton settingsButton;
    juce::TextButton applyButton;

    aianalyzer::AnalysisFrame latestFrame;
    bool hasFrame = false;
    bool settingsExpanded = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(AIAnalyzerAudioProcessorEditor)
};
