cmake_minimum_required(VERSION 3.22)

project(AIAnalyzer VERSION 0.1.0 LANGUAGES C CXX)

include(FetchContent)
FetchContent_Declare(
    JUCE
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG 8.0.8
)
FetchContent_MakeAvailable(JUCE)

juce_add_plugin(AIAnalyzer
    COMPANY_NAME "DebuNeko233"
    BUNDLE_ID "com.debuneko.aianalyzer"
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT FALSE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS FALSE
    COPY_PLUGIN_AFTER_BUILD FALSE
    PLUGIN_MANUFACTURER_CODE Dbnk
    PLUGIN_CODE Aian
    FORMATS VST3
    PRODUCT_NAME "AI Analyzer"
)

juce_generate_juce_header(AIAnalyzer)

target_sources(AIAnalyzer PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginProcessor.h
    Source/PluginEditor.cpp
    Source/PluginEditor.h
    Source/AnalysisFrame.h
    Source/SpscStereoFifo.h
    Source/AnalysisWorker.cpp
    Source/AnalysisWorker.h
)

target_compile_features(AIAnalyzer PRIVATE cxx_std_20)

target_compile_definitions(AIAnalyzer PUBLIC
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0
)

target_link_libraries(AIAnalyzer PRIVATE
    juce::juce_audio_utils
    juce::juce_dsp
    juce::juce_osc
    PUBLIC
    juce::juce_recommended_config_flags
    juce::juce_recommended_lto_flags
    juce::juce_recommended_warning_flags
)
