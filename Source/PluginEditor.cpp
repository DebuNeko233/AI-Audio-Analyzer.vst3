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

bool frameHasFeature(const aianalyzer::AnalysisFrame& frame,
                     aianalyzer::AnalysisFeature feature) noexcept
{
    return (frame.analysisFeatureMask & static_cast<std::uint32_t>(feature)) != 0u;
}

juce::String profileName(int profile)
{
    switch (static_cast<aianalyzer::AnalysisProfile>(juce::jlimit(0, 3, profile)))
    {
        case aianalyzer::AnalysisProfile::Eco: return "Eco";
        case aianalyzer::AnalysisProfile::Balanced: return "Balanced";
        case aianalyzer::AnalysisProfile::Mix: return "Mix";
        case aianalyzer::AnalysisProfile::Full:
        default: return "Full";
    }
}
} // namespace

AIAnalyzerAudioProcessorEditor::AIAnalyzerAudioProcessorEditor(AIAnalyzerAudioProcessor& p)
    : AudioProcessorEditor(&p), ownerProcessor(p)
{
    setSize(760, 500);

    instanceLabel.setText("Instance", juce::dontSendNotification);
    hostLabel.setText("OSC Host", juce::dontSendNotification);
    portLabel.setText("Port", juce::dontSendNotification);
    profileLabel.setText("Profile", juce::dontSendNotification);

    addAndMakeVisible(instanceLabel);
    addAndMakeVisible(hostLabel);
    addAndMakeVisible(portLabel);
    addAndMakeVisible(profileLabel);
    addAndMakeVisible(instanceEditor);
    addAndMakeVisible(hostEditor);
    addAndMakeVisible(portEditor);
    addAndMakeVisible(profileBox);
    addAndMakeVisible(applyButton);

    juce::String instance;
    juce::String host;
    int port = 9855;
    ownerProcessor.getAnalyzerConfig(instance, host, port);

    instanceEditor.setText(instance, false);
    hostEditor.setText(host, false);
    portEditor.setText(juce::String(port), false);
    portEditor.setInputRestrictions(5, "0123456789");

    profileBox.addItem("Eco", 1);
    profileBox.addItem("Balanced", 2);
    profileBox.addItem("Mix", 3);
    profileBox.addItem("Full", 4);
    profileBox.setSelectedId(ownerProcessor.getAnalysisProfileIndex() + 1,
                             juce::dontSendNotification);
    profileBox.onChange = [this]
    {
        const auto selected = profileBox.getSelectedId();
        if (selected >= 1 && selected <= 4)
            ownerProcessor.setAnalysisProfileIndex(selected - 1, true);
    };

    applyButton.onClick = [this] { applyConfig(); };
    instanceEditor.onReturnKey = [this] { applyConfig(); };
    hostEditor.onReturnKey = [this] { applyConfig(); };
    portEditor.onReturnKey = [this] { applyConfig(); };

    startTimerHz(30);
}

void AIAnalyzerAudioProcessorEditor::applyConfig()
{
    ownerProcessor.setAnalyzerConfig(instanceEditor.getText(),
                                     hostEditor.getText(),
                                     portEditor.getText().getIntValue());

    // Echo the actual sanitized configuration back to the editor. This avoids
    // showing stale/invalid text when empty values fall back to defaults or the
    // port is clamped to its valid range.
    juce::String instance;
    juce::String host;
    int port = 9855;
    ownerProcessor.getAnalyzerConfig(instance, host, port);
    instanceEditor.setText(instance, false);
    hostEditor.setText(host, false);
    portEditor.setText(juce::String(port), false);
}

void AIAnalyzerAudioProcessorEditor::timerCallback()
{
    hasFrame = ownerProcessor.getLatestAnalysis(latestFrame);

    // Follow host automation/state restoration without feeding the change back
    // into the host from the editor timer.
    const auto actualProfileId = ownerProcessor.getAnalysisProfileIndex() + 1;
    if (profileBox.getSelectedId() != actualProfileId)
        profileBox.setSelectedId(actualProfileId, juce::dontSendNotification);

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
    g.drawText("Adaptive audio analysis → OSC → MCP",
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
        const bool loudnessAvailable = frameHasFeature(latestFrame, aianalyzer::FeatureLoudness);
        const bool stereoAvailable = frameHasFeature(latestFrame, aianalyzer::FeatureStereo);
        const auto columnWidth = metrics.getWidth() / 4.0f;

        const auto truePeakText = loudnessAvailable
            ? formatDbtp(latestFrame.truePeakDbtp)
            : juce::String("--");
        g.drawFittedText("Sample / True Peak\n" + formatDb(latestFrame.peakDb)
                         + " / " + truePeakText,
                         metrics.withWidth(columnWidth).toNearestInt(),
                         juce::Justification::centred, 2);

        g.drawFittedText("RMS / Crest\n" + formatDb(latestFrame.rmsDb)
                         + " / " + (latestFrame.signalPresent ? formatDb(latestFrame.crestDb) : juce::String("--")),
                         metrics.withX(metrics.getX() + columnWidth).withWidth(columnWidth).toNearestInt(),
                         juce::Justification::centred, 2);

        const auto shortTermText = !loudnessAvailable
            ? juce::String("--")
            : ((!latestFrame.signalPresent && latestFrame.silenceSeconds >= 3.0f)
                ? juce::String("--")
                : formatLufs(latestFrame.lufsShortTerm));
        const auto integratedText = loudnessAvailable
            ? formatLufs(latestFrame.lufsIntegrated)
            : juce::String("--");
        g.drawFittedText("LUFS-S / LUFS-I\n" + shortTermText
                         + " / " + integratedText,
                         metrics.withX(metrics.getX() + columnWidth * 2.0f).withWidth(columnWidth).toNearestInt(),
                         juce::Justification::centred, 2);

        const auto stereoText = !stereoAvailable
            ? juce::String("-- / --")
            : (latestFrame.signalPresent
                ? juce::String(latestFrame.stereoCorrelation, 2) + " / " + juce::String(latestFrame.stereoWidth, 2)
                : juce::String("NO SIGNAL"));
        g.drawFittedText("Corr / Width\n" + stereoText,
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
        g.setColour(latestFrame.signalPresent ? juce::Colours::lightgrey : juce::Colours::orange);

        const bool spectrumAvailable = frameHasFeature(latestFrame, aianalyzer::FeatureSpectrum);
        const bool loudnessAvailable = frameHasFeature(latestFrame, aianalyzer::FeatureLoudness);

        juce::String detailText = "PROFILE " + profileName(latestFrame.analysisProfile) + "   ·   ";
        if (latestFrame.signalPresent)
        {
            detailText += "SIGNAL   ·   Detector " + formatDb(latestFrame.detectorPeakDb);
            if (spectrumAvailable)
            {
                detailText += "   ·   Centroid " + juce::String(latestFrame.spectralCentroidHz, 0) + " Hz"
                           + "   ·   Rolloff " + juce::String(latestFrame.spectralRolloffHz, 0) + " Hz";
            }
            else
            {
                detailText += "   ·   Spectrum disabled";
            }
        }
        else
        {
            detailText += "NO INPUT (< -50 dBFS)   ·   Detector " + formatDb(latestFrame.detectorPeakDb)
                       + "   ·   Silence " + juce::String(latestFrame.silenceSeconds, 1) + " s";
        }

        if (loudnessAvailable)
            detailText += "   ·   Session max TP " + formatDbtp(latestFrame.maxTruePeakDbtp);

        g.drawFittedText(detailText,
                         detail.toNearestInt(),
                         juce::Justification::centredLeft,
                         1);
        analysisArea.removeFromTop(6.0f);
    }

    drawSpectrum(g, analysisArea);

    g.setFont(juce::FontOptions(11.0f));
    g.setColour(juce::Colours::grey);
    g.drawText("Dropped audio FIFO blocks: " + juce::String(static_cast<juce::int64>(ownerProcessor.getDroppedBlocks())),
               18, getHeight() - 20, getWidth() - 36, 14, juce::Justification::centredRight);
}

void AIAnalyzerAudioProcessorEditor::drawSpectrum(juce::Graphics& g,
                                                   juce::Rectangle<float> bounds) const
{
    g.setColour(juce::Colour::fromRGB(26, 29, 36));
    g.fillRoundedRectangle(bounds, 8.0f);

    if (!hasFrame)
        return;

    if (!frameHasFeature(latestFrame, aianalyzer::FeatureSpectrum))
    {
        g.setColour(juce::Colours::grey);
        g.setFont(juce::FontOptions(13.0f));
        g.drawText("Spectrum disabled by Analysis Profile",
                   bounds.toNearestInt(),
                   juce::Justification::centred);
        return;
    }

    if (!latestFrame.signalPresent)
    {
        g.setColour(juce::Colours::grey);
        g.setFont(juce::FontOptions(13.0f));
        g.drawText("No active input", bounds.toNearestInt(), juce::Justification::centred);
        return;
    }

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

    auto label = row.removeFromLeft(54);
    instanceLabel.setBounds(label);
    instanceEditor.setBounds(row.removeFromLeft(120).reduced(2));

    label = row.removeFromLeft(62);
    hostLabel.setBounds(label);
    hostEditor.setBounds(row.removeFromLeft(120).reduced(2));

    label = row.removeFromLeft(34);
    portLabel.setBounds(label);
    portEditor.setBounds(row.removeFromLeft(60).reduced(2));

    label = row.removeFromLeft(48);
    profileLabel.setBounds(label);
    profileBox.setBounds(row.removeFromLeft(112).reduced(2));

    applyButton.setBounds(row.removeFromLeft(84).reduced(2));
}
