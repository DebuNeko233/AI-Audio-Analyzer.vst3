#include "PluginEditor.h"

#include <cmath>

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

juce::String formatTransportTime(float seconds)
{
    const auto safeSeconds = std::max(0.0f, seconds);
    const auto totalHundredths = static_cast<int>(std::round(safeSeconds * 100.0f));
    const auto minutes = totalHundredths / 6000;
    const auto wholeSeconds = (totalHundredths / 100) % 60;
    const auto hundredths = totalHundredths % 100;
    return juce::String::formatted("%02d:%02d.%02d", minutes, wholeSeconds, hundredths);
}

bool frameHasFeatureForProfile(const aianalyzer::AnalysisFrame& frame,
                               int hostProfileIndex,
                               aianalyzer::AnalysisFeature feature) noexcept
{
    const auto profile = static_cast<aianalyzer::AnalysisProfile>(
        juce::jlimit(0, 3, hostProfileIndex));
    const auto requestedMask = aianalyzer::analysisFeatureMaskForProfile(profile);
    const auto featureBit = static_cast<std::uint32_t>(feature);
    return (frame.analysisFeatureMask & requestedMask & featureBit) != 0u;
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
    setSize(820, 590);

    addAndMakeVisible(instanceLabel);
    addAndMakeVisible(hostLabel);
    addAndMakeVisible(portLabel);
    addAndMakeVisible(profileLabel);
    addAndMakeVisible(languageLabel);
    addAndMakeVisible(instanceEditor);
    addAndMakeVisible(hostEditor);
    addAndMakeVisible(portEditor);
    addAndMakeVisible(languageBox);
    addAndMakeVisible(ecoButton);
    addAndMakeVisible(balancedButton);
    addAndMakeVisible(mixButton);
    addAndMakeVisible(fullButton);
    addAndMakeVisible(settingsButton);
    addAndMakeVisible(applyButton);

    juce::String instance;
    juce::String host;
    int port = 9855;
    ownerProcessor.getAnalyzerConfig(instance, host, port);

    instanceEditor.setText(instance, false);
    hostEditor.setText(host, false);
    portEditor.setText(juce::String(port), false);
    portEditor.setInputRestrictions(5, "0123456789");

    ecoButton.onClick = [this] { setProfileFromUi(0); };
    balancedButton.onClick = [this] { setProfileFromUi(1); };
    mixButton.onClick = [this] { setProfileFromUi(2); };
    fullButton.onClick = [this] { setProfileFromUi(3); };

    languageBox.addItem("English", 1);
    languageBox.addItem(aianalyzer::uiText(aianalyzer::UiLanguage::Chinese,
                                           aianalyzer::UiText::Chinese),
                        2);
    languageBox.setSelectedId(ownerProcessor.getUiLanguageIndex() + 1,
                              juce::dontSendNotification);
    languageBox.onChange = [this]
    {
        const auto selected = languageBox.getSelectedId();
        if (selected >= 1 && selected <= 2)
        {
            ownerProcessor.setUiLanguageIndex(selected - 1);
            updateLocalizedText();
            repaint();
        }
    };

    settingsButton.onClick = [this]
    {
        settingsExpanded = !settingsExpanded;
        settingsButton.setToggleState(settingsExpanded, juce::dontSendNotification);
        updateLocalizedText();
        updateSettingsVisibility();
        resized();
        repaint();
    };

    applyButton.onClick = [this] { applyConfig(); };
    instanceEditor.onReturnKey = [this] { applyConfig(); };
    hostEditor.onReturnKey = [this] { applyConfig(); };
    portEditor.onReturnKey = [this] { applyConfig(); };

    updateLocalizedText();
    updateProfileButtons();
    updateSettingsVisibility();
    startTimerHz(30);
}

aianalyzer::UiLanguage AIAnalyzerAudioProcessorEditor::currentLanguage() const noexcept
{
    return ownerProcessor.getUiLanguageIndex() == 1
        ? aianalyzer::UiLanguage::Chinese
        : aianalyzer::UiLanguage::English;
}

void AIAnalyzerAudioProcessorEditor::updateLocalizedText()
{
    const auto language = currentLanguage();
    instanceLabel.setText(aianalyzer::uiText(language, aianalyzer::UiText::Instance),
                          juce::dontSendNotification);
    hostLabel.setText(aianalyzer::uiText(language, aianalyzer::UiText::OscHost),
                      juce::dontSendNotification);
    portLabel.setText(aianalyzer::uiText(language, aianalyzer::UiText::Port),
                      juce::dontSendNotification);
    profileLabel.setText(aianalyzer::uiText(language, aianalyzer::UiText::Profile),
                         juce::dontSendNotification);
    languageLabel.setText(aianalyzer::uiText(language, aianalyzer::UiText::Language),
                          juce::dontSendNotification);
    settingsButton.setButtonText(aianalyzer::uiText(
        language,
        settingsExpanded ? aianalyzer::UiText::HideSettings : aianalyzer::UiText::Settings));
    applyButton.setButtonText(aianalyzer::uiText(language, aianalyzer::UiText::Apply));
}

void AIAnalyzerAudioProcessorEditor::updateProfileButtons()
{
    const auto active = ownerProcessor.getAnalysisProfileIndex();
    ecoButton.setToggleState(active == 0, juce::dontSendNotification);
    balancedButton.setToggleState(active == 1, juce::dontSendNotification);
    mixButton.setToggleState(active == 2, juce::dontSendNotification);
    fullButton.setToggleState(active == 3, juce::dontSendNotification);
}

void AIAnalyzerAudioProcessorEditor::updateSettingsVisibility()
{
    instanceLabel.setVisible(settingsExpanded);
    hostLabel.setVisible(settingsExpanded);
    portLabel.setVisible(settingsExpanded);
    instanceEditor.setVisible(settingsExpanded);
    hostEditor.setVisible(settingsExpanded);
    portEditor.setVisible(settingsExpanded);
    applyButton.setVisible(settingsExpanded);
}

void AIAnalyzerAudioProcessorEditor::setProfileFromUi(int profileIndex)
{
    ownerProcessor.setAnalysisProfileIndex(profileIndex, true);
    updateProfileButtons();
    repaint();
}

void AIAnalyzerAudioProcessorEditor::applyConfig()
{
    ownerProcessor.setAnalyzerConfig(instanceEditor.getText(),
                                     hostEditor.getText(),
                                     portEditor.getText().getIntValue());

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

    // The host parameter is authoritative. This catches DAW automation/state
    // restoration and external LLM/DAW-control MCP writes without feeding a
    // second change back into the host.
    updateProfileButtons();

    const auto actualLanguageId = ownerProcessor.getUiLanguageIndex() + 1;
    if (languageBox.getSelectedId() != actualLanguageId)
    {
        languageBox.setSelectedId(actualLanguageId, juce::dontSendNotification);
        updateLocalizedText();
    }

    repaint();
}

void AIAnalyzerAudioProcessorEditor::paint(juce::Graphics& g)
{
    const auto language = currentLanguage();
    g.fillAll(juce::Colour::fromRGB(19, 21, 26));

    g.setColour(juce::Colours::white);
    g.setFont(juce::FontOptions(22.0f, juce::Font::bold));
    g.drawText("AI Audio Analyzer", 18, 12, getWidth() - 240, 32, juce::Justification::centredLeft);

    g.setFont(juce::FontOptions(12.0f));
    g.setColour(juce::Colours::lightgrey);
    g.drawText(aianalyzer::uiText(language, aianalyzer::UiText::Subtitle),
               18, 42, getWidth() - 240, 22, juce::Justification::centredLeft);

    if (settingsExpanded)
    {
        const auto settingsPanel = juce::Rectangle<float>(18.0f, 106.0f,
                                                          static_cast<float>(getWidth() - 36), 38.0f);
        g.setColour(juce::Colour::fromRGB(25, 28, 35));
        g.fillRoundedRectangle(settingsPanel, 7.0f);
    }

    auto analysisArea = getLocalBounds().toFloat().reduced(18.0f);
    analysisArea.removeFromTop(settingsExpanded ? 148.0f : 108.0f);

    auto status = analysisArea.removeFromTop(58.0f);
    g.setColour(juce::Colour::fromRGB(27, 31, 38));
    g.fillRoundedRectangle(status, 8.0f);

    auto transportArea = status.reduced(12.0f, 7.0f);
    auto healthArea = transportArea.removeFromRight(status.getWidth() * 0.42f);
    transportArea.removeFromRight(12.0f);

    g.setFont(juce::FontOptions(11.5f, juce::Font::bold));
    g.setColour(juce::Colours::lightgrey);
    g.drawText(aianalyzer::uiText(language, aianalyzer::UiText::Transport),
               transportArea.removeFromTop(18.0f).toNearestInt(), juce::Justification::centredLeft);

    g.setFont(juce::FontOptions(11.0f));
    juce::String transportText;
    if (!hasFrame || !latestFrame.transportSupported)
    {
        transportText = aianalyzer::uiText(language, aianalyzer::UiText::Unsupported);
        g.setColour(juce::Colours::grey);
    }
    else
    {
        if (latestFrame.transportIsRecording)
            transportText = aianalyzer::uiText(language, aianalyzer::UiText::Recording);
        else if (latestFrame.transportIsPlaying)
            transportText = aianalyzer::uiText(language, aianalyzer::UiText::Playing);
        else
            transportText = aianalyzer::uiText(language, aianalyzer::UiText::Stopped);

        transportText += "   " + formatTransportTime(latestFrame.transportTimeSeconds);
        if (latestFrame.transportBpm > 0.0f)
            transportText += "   |   " + juce::String(latestFrame.transportBpm, 1) + " BPM";
        transportText += "   |   " + juce::String(latestFrame.transportTimeSignatureNumerator)
                       + "/" + juce::String(latestFrame.transportTimeSignatureDenominator);
        transportText += "   |   " + aianalyzer::uiText(language, aianalyzer::UiText::Pass)
                       + " " + juce::String(static_cast<int>(latestFrame.transportEpoch));
        if (latestFrame.transportIsLooping)
            transportText += "   |   " + aianalyzer::uiText(language, aianalyzer::UiText::Loop);
        g.setColour(latestFrame.transportIsPlaying ? juce::Colours::lightgreen : juce::Colours::lightgrey);
    }
    g.drawFittedText(transportText, transportArea.toNearestInt(), juce::Justification::centredLeft, 1);

    const auto drops = hasFrame ? latestFrame.droppedBlocks : ownerProcessor.getDroppedBlocks();
    juce::String healthText = aianalyzer::uiText(language, aianalyzer::UiText::Healthy);
    auto healthColour = juce::Colours::lightgreen;
    if (drops > 0)
    {
        healthText = aianalyzer::uiText(language, aianalyzer::UiText::DroppedAudio);
        healthColour = juce::Colours::orangered;
    }
    else if (hasFrame && latestFrame.fifoFillRatio >= 0.75f)
    {
        healthText = aianalyzer::uiText(language, aianalyzer::UiText::FifoPressure);
        healthColour = juce::Colours::orange;
    }
    else if (hasFrame && latestFrame.estimatedAnalysisLagMs >= 250.0f)
    {
        healthText = aianalyzer::uiText(language, aianalyzer::UiText::HighLatency);
        healthColour = juce::Colours::orange;
    }

    auto healthTop = healthArea.removeFromTop(18.0f);
    g.setFont(juce::FontOptions(11.5f, juce::Font::bold));
    g.setColour(juce::Colours::lightgrey);
    g.drawText(aianalyzer::uiText(language, aianalyzer::UiText::AnalysisHealth),
               healthTop.removeFromLeft(112.0f).toNearestInt(), juce::Justification::centredLeft);
    g.setColour(healthColour);
    g.drawFittedText(healthText, healthTop.toNearestInt(), juce::Justification::centredRight, 1);

    g.setFont(juce::FontOptions(10.5f));
    g.setColour(juce::Colours::lightgrey);
    juce::String healthMetrics;
    if (hasFrame)
    {
        healthMetrics = aianalyzer::uiText(language, aianalyzer::UiText::Worker)
                      + " " + juce::String(latestFrame.workerLoadRatio * 100.0f, 0) + "%"
                      + "   |   " + aianalyzer::uiText(language, aianalyzer::UiText::Fifo)
                      + " " + juce::String(latestFrame.fifoFillRatio * 100.0f, 0) + "%"
                      + "   |   " + aianalyzer::uiText(language, aianalyzer::UiText::Lag)
                      + " " + juce::String(latestFrame.estimatedAnalysisLagMs, 0) + " ms"
                      + "   |   " + aianalyzer::uiText(language, aianalyzer::UiText::Drops)
                      + " " + juce::String(static_cast<juce::int64>(drops));
    }
    else
    {
        healthMetrics = aianalyzer::uiText(language, aianalyzer::UiText::WaitingForAudio);
    }
    g.drawFittedText(healthMetrics, healthArea.removeFromTop(16.0f).toNearestInt(),
                     juce::Justification::centredLeft, 1);

    juce::String instance;
    juce::String host;
    int port = 9855;
    ownerProcessor.getAnalyzerConfig(instance, host, port);
    g.setColour(juce::Colours::grey);
    g.drawFittedText(aianalyzer::uiText(language, aianalyzer::UiText::OscTx)
                     + " -> " + host + ":" + juce::String(port),
                     healthArea.toNearestInt(), juce::Justification::centredLeft, 1);

    analysisArea.removeFromTop(8.0f);

    auto metrics = analysisArea.removeFromTop(94.0f);
    g.setColour(juce::Colour::fromRGB(31, 35, 43));
    g.fillRoundedRectangle(metrics, 8.0f);

    g.setFont(juce::FontOptions(12.5f));
    g.setColour(juce::Colours::white);

    const auto hostProfileIndex = ownerProcessor.getAnalysisProfileIndex();

    if (hasFrame)
    {
        const bool loudnessAvailable = frameHasFeatureForProfile(
            latestFrame, hostProfileIndex, aianalyzer::FeatureLoudness);
        const bool stereoAvailable = frameHasFeatureForProfile(
            latestFrame, hostProfileIndex, aianalyzer::FeatureStereo);
        const auto columnWidth = metrics.getWidth() / 4.0f;

        const auto truePeakText = loudnessAvailable
            ? formatDbtp(latestFrame.truePeakDbtp)
            : juce::String("--");
        g.drawFittedText(aianalyzer::uiText(language, aianalyzer::UiText::SampleTruePeak)
                         + "\n" + formatDb(latestFrame.peakDb) + " / " + truePeakText,
                         metrics.withWidth(columnWidth).toNearestInt(),
                         juce::Justification::centred, 2);

        g.drawFittedText(aianalyzer::uiText(language, aianalyzer::UiText::RmsCrest)
                         + "\n" + formatDb(latestFrame.rmsDb)
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
        g.drawFittedText(aianalyzer::uiText(language, aianalyzer::UiText::LufsShortIntegrated)
                         + "\n" + shortTermText + " / " + integratedText,
                         metrics.withX(metrics.getX() + columnWidth * 2.0f).withWidth(columnWidth).toNearestInt(),
                         juce::Justification::centred, 2);

        const auto stereoText = !stereoAvailable
            ? juce::String("-- / --")
            : (latestFrame.signalPresent
                ? juce::String(latestFrame.stereoCorrelation, 2) + " / " + juce::String(latestFrame.stereoWidth, 2)
                : aianalyzer::uiText(language, aianalyzer::UiText::NoSignal));
        g.drawFittedText(aianalyzer::uiText(language, aianalyzer::UiText::CorrWidth)
                         + "\n" + stereoText,
                         metrics.withX(metrics.getX() + columnWidth * 3.0f).withWidth(columnWidth).toNearestInt(),
                         juce::Justification::centred, 2);
    }
    else
    {
        g.drawText(aianalyzer::uiText(language, aianalyzer::UiText::WaitingForAudio),
                   metrics.toNearestInt(), juce::Justification::centred);
    }

    analysisArea.removeFromTop(12.0f);

    if (hasFrame)
    {
        auto detail = analysisArea.removeFromTop(22.0f);
        g.setFont(juce::FontOptions(11.0f));
        g.setColour(latestFrame.signalPresent ? juce::Colours::lightgrey : juce::Colours::orange);

        const bool spectrumAvailable = frameHasFeatureForProfile(
            latestFrame, hostProfileIndex, aianalyzer::FeatureSpectrum);
        const bool loudnessAvailable = frameHasFeatureForProfile(
            latestFrame, hostProfileIndex, aianalyzer::FeatureLoudness);
        const bool profilePending = latestFrame.analysisProfile != hostProfileIndex;

        juce::String detailText = aianalyzer::uiText(language, aianalyzer::UiText::Profile)
                                + " " + profileName(hostProfileIndex);
        if (profilePending)
            detailText += " (" + aianalyzer::uiText(language, aianalyzer::UiText::Pending) + ")";
        detailText += "   |   ";

        if (latestFrame.signalPresent)
        {
            detailText += aianalyzer::uiText(language, aianalyzer::UiText::Signal)
                       + "   |   " + aianalyzer::uiText(language, aianalyzer::UiText::Detector)
                       + " " + formatDb(latestFrame.detectorPeakDb);
            if (spectrumAvailable)
            {
                detailText += "   |   Centroid " + juce::String(latestFrame.spectralCentroidHz, 0) + " Hz"
                           + "   |   Rolloff " + juce::String(latestFrame.spectralRolloffHz, 0) + " Hz";
            }
            else
            {
                detailText += "   |   " + aianalyzer::uiText(language, aianalyzer::UiText::SpectrumUnavailable);
            }
        }
        else
        {
            detailText += aianalyzer::uiText(language, aianalyzer::UiText::NoSignal)
                       + " (< -50 dBFS)   |   " + aianalyzer::uiText(language, aianalyzer::UiText::Detector)
                       + " " + formatDb(latestFrame.detectorPeakDb)
                       + "   |   " + aianalyzer::uiText(language, aianalyzer::UiText::Silence)
                       + " " + juce::String(latestFrame.silenceSeconds, 1) + " s";
        }

        if (loudnessAvailable)
            detailText += "   |   " + aianalyzer::uiText(language, aianalyzer::UiText::SessionMaxTp)
                       + " " + formatDbtp(latestFrame.maxTruePeakDbtp);

        g.drawFittedText(detailText,
                         detail.toNearestInt(),
                         juce::Justification::centredLeft,
                         1);
        analysisArea.removeFromTop(6.0f);
    }

    drawSpectrum(g, analysisArea);
}

void AIAnalyzerAudioProcessorEditor::drawSpectrum(juce::Graphics& g,
                                                   juce::Rectangle<float> bounds) const
{
    const auto language = currentLanguage();
    g.setColour(juce::Colour::fromRGB(26, 29, 36));
    g.fillRoundedRectangle(bounds, 8.0f);

    if (!hasFrame)
        return;

    const auto hostProfileIndex = ownerProcessor.getAnalysisProfileIndex();
    if (!frameHasFeatureForProfile(latestFrame,
                                   hostProfileIndex,
                                   aianalyzer::FeatureSpectrum))
    {
        g.setColour(juce::Colours::grey);
        g.setFont(juce::FontOptions(13.0f));
        const auto pending = latestFrame.analysisProfile != hostProfileIndex;
        g.drawText(pending ? aianalyzer::uiText(language, aianalyzer::UiText::SpectrumWaiting)
                           : aianalyzer::uiText(language, aianalyzer::UiText::SpectrumDisabled),
                   bounds.toNearestInt(),
                   juce::Justification::centred);
        return;
    }

    if (!latestFrame.signalPresent)
    {
        g.setColour(juce::Colours::grey);
        g.setFont(juce::FontOptions(13.0f));
        g.drawText(aianalyzer::uiText(language, aianalyzer::UiText::NoActiveInput),
                   bounds.toNearestInt(), juce::Justification::centred);
        return;
    }

    const auto left = bounds.getX() + 34.0f;
    const auto right = bounds.getRight() - 10.0f;
    const auto top = bounds.getY() + 10.0f;
    const auto bottom = bounds.getBottom() - 10.0f;
    const auto width = right - left;
    const auto height = bottom - top;

    g.setFont(juce::FontOptions(9.5f));
    for (int db = -20; db >= -80; db -= 20)
    {
        const auto normalized = (static_cast<float>(db) + 100.0f) / 100.0f;
        const auto y = bottom - normalized * height;
        g.setColour(juce::Colour::fromRGB(48, 53, 63));
        g.drawHorizontalLine(static_cast<int>(std::round(y)), left, right);
        g.setColour(juce::Colours::grey);
        g.drawText(juce::String(db), bounds.getX() + 4.0f, y - 7.0f, 26.0f, 14.0f,
                   juce::Justification::centredRight);
    }

    juce::Path path;
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
    languageLabel.setBounds(getWidth() - 190, 18, 64, 28);
    languageBox.setBounds(getWidth() - 126, 18, 108, 28);

    auto area = getLocalBounds().reduced(18);
    area.removeFromTop(64);

    auto profileRow = area.removeFromTop(34);
    profileLabel.setBounds(profileRow.removeFromLeft(72));
    ecoButton.setBounds(profileRow.removeFromLeft(78).reduced(2));
    balancedButton.setBounds(profileRow.removeFromLeft(104).reduced(2));
    mixButton.setBounds(profileRow.removeFromLeft(78).reduced(2));
    fullButton.setBounds(profileRow.removeFromLeft(78).reduced(2));
    settingsButton.setBounds(profileRow.removeFromRight(112).reduced(2));

    if (settingsExpanded)
    {
        area.removeFromTop(4);
        auto row = area.removeFromTop(34);

        auto label = row.removeFromLeft(54);
        instanceLabel.setBounds(label);
        instanceEditor.setBounds(row.removeFromLeft(142).reduced(2));

        label = row.removeFromLeft(68);
        hostLabel.setBounds(label);
        hostEditor.setBounds(row.removeFromLeft(142).reduced(2));

        label = row.removeFromLeft(42);
        portLabel.setBounds(label);
        portEditor.setBounds(row.removeFromLeft(60).reduced(2));

        applyButton.setBounds(row.removeFromLeft(84).reduced(2));
    }
}
