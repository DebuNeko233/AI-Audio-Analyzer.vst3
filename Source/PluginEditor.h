#pragma once

#include <JuceHeader.h>
#include "PluginProcessor.h"

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
    void drawSpectrum(juce::Graphics&, juce::Rectangle<float> bounds) const;

    AIAnalyzerAudioProcessor& ownerProcessor;

    juce::Label instanceLabel;
    juce::Label hostLabel;
    juce::Label portLabel;
    juce::Label profileLabel;
    juce::TextEditor instanceEditor;
    juce::TextEditor hostEditor;
    juce::TextEditor portEditor;
    juce::ComboBox profileBox;
    juce::TextButton applyButton { "Apply" };

    aianalyzer::AnalysisFrame latestFrame;
    bool hasFrame = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(AIAnalyzerAudioProcessorEditor)
};
