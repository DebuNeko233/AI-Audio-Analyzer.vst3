# AI Analyzer

**AI Analyzer** is a machine-readable audio analysis VST3 designed for AI/LLM-assisted music production.

It runs inside a DAW (initially focused on FL Studio), analyzes the incoming audio off the realtime audio thread, and sends compact analysis frames over OSC to a Python MCP bridge. An LLM can then query spectrum, dynamics, stereo information, and track-to-track overlap without having to inspect a GUI spectrum analyzer.

## Planned V0.1

- 4096-point Hann FFT
- 32 logarithmic frequency bands (20 Hz–20 kHz)
- Peak / RMS / crest factor
- Spectral centroid / 85% rolloff / flatness
- Stereo correlation / Mid-Side width ratio
- Multi-instance track IDs (`Kick`, `Bass`, `Vocal`, `Master`, ...)
- OSC output on localhost
- Python MCP bridge for Cherry Studio
- No network or FFT work on the DAW realtime audio thread

The initial JUCE VST3 implementation and MCP bridge are being added in the next commit.
