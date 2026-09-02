#include "PluginEditor.h"

namespace
{
juce::String formatDb(float value)
{
    return juce::String(value, 1) + " dB";
}

juce::String formatLufs(float value)
{
    return juce::String(value, 1) + " LUFS";
}

juce::String formatDbtp(float value)
{
    return juce::String(value, 1) + " dBTP";
}
} // namespace

AIAnalyzerAudioProcessorEditor::AIAnalyzerAudioProcessorEditor(AIAnalyzerAudioProcessor& p)
    : AudioProcessorEditor(&p), processor(p)
{
    setSize(760, 500);

    instanceLabel.setText("Instance", juce::dontSendNotification);
    hostLabel.setText("OSC Host", juce::dontSendNotification);
    portLabel.setText("Port", juce::dontSendNotification);

    addAndMakeVisible(instanceLabel);
    addAndMakeVisible(hostLabel);
    addAndMakeVisible(portLabel);
    addAndMakeVisible(instanceEditor);
    addAndMakeVisible(hostEditor);
    addAndMakeVisible(portEditor);
    addAndMakeVisible(applyButton);

    juce::String instance;
    juce::String host;
    int port = 9855;
    processor.getAnalyzerConfig(instance, host, port);

    instanceEditor.setText(instance, false);
    hostEditor.setText(host, false);
    portEditor.setText(juce::String(port), false);
    portEditor.setInputRestrictions(5, "0123456789");

    applyButton.onClick = [this] { applyConfig(); };
    instanceEditor.onReturnKey = [this] { applyConfig(); };
    hostEditor.onReturnKey = [this] { applyConfig(); };
    portEditor.onReturnKey = [this] { applyConfig(); };

    startTimerHz(30);
}

void AIAnalyzerAudioProcessorEditor::applyConfig()
{
    processor.setAnalyzerConfig(instanceEditor.getText(),
                                hostEditor.getText(),
                                portEditor.getText().getIntValue());
}

void AIAnalyzerAudioProcessorEditor::timerCallback()
{
    hasFrame = processor.getLatestAnalysis(latestFrame);
    repaint();
}

void AIAnalyzerAudioProcessorEditor::paint(juce::Graphics& g)
{
    g.fillAll(juce::Colour::fromRGB(19, 21, 26));

    g.setColour(juce::Colours::white);
    g.setFont(juce::FontOptions(22.0f, juce::Font::bold));
    g.drawText("AI Audio Analyzer", 18, 12, 260, 32, juce::Justification::centredLeft);

    g.setFont(juce::FontOptions(12.0f));
    g.setColour(juce::Colours::lightgrey);
    g.drawText("Spectrum / EBU R128 loudness / true peak / stereo analysis → OSC → MCP",
               18, 42, getWidth() - 36, 22, juce::Justification::centredLeft);

    auto analysisArea = getLocalBounds().toFloat().reduced(18.0f);
    analysisArea.removeFromTop(112.0f);

    auto metrics = analysisArea.removeFromTop(94.0f);
    g.setColour(juce::Colour::fromRGB(31, 35, 43));
    g.fillRoundedRectangle(metrics, 8.0f);

    g.setFont(juce::FontOptions(12.5f));
    g.setColour(juce::Colours::white);

    if (hasFrame)
    {
        const auto columnWidth = metrics.getWidth() / 4.0f;
        g.drawFittedText("Sample / True Peak\n" + formatDb(latestFrame.peakDb)
                         + " / " + formatDbtp(latestFrame.truePeakDbtp),
                         metrics.withWidth(columnWidth).toNearestInt(),
                         juce::Justification::centred, 2);
        g.drawFittedText("RMS / Crest\n" + formatDb(latestFrame.rmsDb)
                         + " / " + formatDb(latestFrame.crestDb),
                         metrics.withX(metrics.getX() + columnWidth).withWidth(columnWidth).toNearestInt(),
                         juce::Justification::centred, 2);
        g.drawFittedText("LUFS-S / LUFS-I\n" + formatLufs(latestFrame.lufsShortTerm)
                         + " / " + formatLufs(latestFrame.lufsIntegrated),
                         metrics.withX(metrics.getX() + columnWidth * 2.0f).withWidth(columnWidth).toNearestInt(),
                         juce::Justification::centred, 2);
        g.drawFittedText("Corr / Width\n" + juce::String(latestFrame.stereoCorrelation, 2)
                         + " / " + juce::String(latestFrame.stereoWidth, 2),
                         metrics.withX(metrics.getX() + columnWidth * 3.0f).withWidth(columnWidth).toNearestInt(),
                         juce::Justification::centred, 2);
    }
    else
    {
        g.drawText("Waiting for audio...", metrics.toNearestInt(), juce::Justification::centred);
    }

    analysisArea.removeFromTop(12.0f);

    if (hasFrame)
    {
        auto detail = analysisArea.removeFromTop(22.0f);
        g.setFont(juce::FontOptions(11.0f));
        g.setColour(juce::Colours::lightgrey);
        g.drawText("Centroid " + juce::String(latestFrame.spectralCentroidHz, 0) + " Hz"
                   + "   ·   Rolloff " + juce::String(latestFrame.spectralRolloffHz, 0) + " Hz"
                   + "   ·   Session max TP " + formatDbtp(latestFrame.maxTruePeakDbtp),
                   detail.toNearestInt(), juce::Justification::centredLeft);
        analysisArea.removeFromTop(6.0f);
    }

    drawSpectrum(g, analysisArea);

    g.setFont(juce::FontOptions(11.0f));
    g.setColour(juce::Colours::grey);
    g.drawText("Dropped audio FIFO blocks: " + juce::String(static_cast<juce::int64>(processor.getDroppedBlocks())),
               18, getHeight() - 20, getWidth() - 36, 14, juce::Justification::centredRight);
}

void AIAnalyzerAudioProcessorEditor::drawSpectrum(juce::Graphics& g,
                                                   juce::Rectangle<float> bounds) const
{
    g.setColour(juce::Colour::fromRGB(26, 29, 36));
    g.fillRoundedRectangle(bounds, 8.0f);

    if (!hasFrame)
        return;

    juce::Path path;
    const auto left = bounds.getX() + 10.0f;
    const auto right = bounds.getRight() - 10.0f;
    const auto top = bounds.getY() + 10.0f;
    const auto bottom = bounds.getBottom() - 10.0f;
    const auto width = right - left;
    const auto height = bottom - top;

    for (int i = 0; i < aianalyzer::kNumBands; ++i)
    {
        const auto x = left + width * static_cast<float>(i) / static_cast<float>(aianalyzer::kNumBands - 1);
        const auto normalized = juce::jlimit(0.0f, 1.0f,
                                             (latestFrame.bandsDb[static_cast<std::size_t>(i)] + 100.0f) / 100.0f);
        const auto y = bottom - normalized * height;

        if (i == 0)
            path.startNewSubPath(x, y);
        else
            path.lineTo(x, y);
    }

    g.setColour(juce::Colour::fromRGB(95, 200, 255));
    g.strokePath(path, juce::PathStrokeType(2.0f));
}

void AIAnalyzerAudioProcessorEditor::resized()
{
    auto area = getLocalBounds().reduced(18);
    area.removeFromTop(64);

    auto row = area.removeFromTop(34);

    auto label = row.removeFromLeft(58);
    instanceLabel.setBounds(label);
    instanceEditor.setBounds(row.removeFromLeft(170).reduced(2));

    label = row.removeFromLeft(72);
    hostLabel.setBounds(label);
    hostEditor.setBounds(row.removeFromLeft(160).reduced(2));

    label = row.removeFromLeft(42);
    portLabel.setBounds(label);
    portEditor.setBounds(row.removeFromLeft(72).reduced(2));

    applyButton.setBounds(row.removeFromLeft(74).reduced(2));
}
