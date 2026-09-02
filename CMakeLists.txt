cmake_minimum_required(VERSION 3.22)

# GitHub's macOS runner currently uses a very new SDK. Without an explicit
# deployment target, the produced Mach-O inherits that runner OS as its minimum
# supported macOS version and older Macs/hosts silently refuse to load it.
# Keep this before project()/enable_language(). Callers can still override it
# with -DCMAKE_OSX_DEPLOYMENT_TARGET=...
if(APPLE AND NOT CMAKE_OSX_DEPLOYMENT_TARGET)
    set(CMAKE_OSX_DEPLOYMENT_TARGET "11.0" CACHE STRING "Minimum supported macOS version")
endif()

project(AIAnalyzer VERSION 0.2.1 LANGUAGES C CXX)

include(FetchContent)

FetchContent_Declare(
    JUCE
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG 8.0.8
)
FetchContent_MakeAvailable(JUCE)

# libebur128 supplies standards-based EBU R128 / ITU-R BS.1770 loudness and
# true-peak measurement. Build it statically so the VST3 has no extra runtime
# library dependency. libebur128 1.2.6 still declares an old CMake minimum, so
# modern CMake 4 runners need an explicit policy compatibility floor.
set(CMAKE_POLICY_VERSION_MINIMUM 3.5 CACHE STRING "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(WITH_STATIC_PIC ON CACHE BOOL "" FORCE)
set(ENABLE_TESTS OFF CACHE BOOL "" FORCE)
FetchContent_Declare(
    libebur128
    GIT_REPOSITORY https://github.com/jiixyj/libebur128.git
    GIT_TAG v1.2.6
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(libebur128)

# Keep the internal target, manufacturer code and plugin code stable so existing
# DAW projects are less likely to lose the plugin after this user-facing rename.
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
    PRODUCT_NAME "AI Audio Analyzer"
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

target_include_directories(AIAnalyzer PRIVATE
    ${libebur128_SOURCE_DIR}/ebur128
)

target_link_libraries(AIAnalyzer PRIVATE
    juce::juce_audio_utils
    juce::juce_dsp
    juce::juce_osc
    ebur128
    PUBLIC
    juce::juce_recommended_config_flags
    juce::juce_recommended_lto_flags
    juce::juce_recommended_warning_flags
)
