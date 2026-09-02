#!/bin/bash
set -euo pipefail

step() {
  printf '\n==> %s\n' "$1"
}

ROOT="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_SOURCE="$ROOT/AI Audio Analyzer.vst3"
PLUGIN_ROOT="$HOME/Library/Audio/Plug-Ins/VST3"
PLUGIN_DEST="$PLUGIN_ROOT/AI Audio Analyzer.vst3"
INSTALL_ROOT="$HOME/Library/Application Support/AI Audio Analyzer"

if [ "$(uname -m)" != "arm64" ]; then
  echo "This macOS package supports Apple Silicon (arm64) only. Detected: $(uname -m)" >&2
  exit 1
fi

echo 'AI Audio Analyzer installer'
echo 'No programming tools are required.'

step 'Preparing downloaded files'
xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null || true

step 'Installing VST3'
if [ ! -d "$PLUGIN_SOURCE" ]; then
  echo "Plugin bundle not found: $PLUGIN_SOURCE" >&2
  exit 1
fi
mkdir -p "$PLUGIN_ROOT"
rm -rf "$PLUGIN_DEST"
ditto "$PLUGIN_SOURCE" "$PLUGIN_DEST"
xattr -dr com.apple.quarantine "$PLUGIN_DEST" 2>/dev/null || true

if ! codesign --verify --deep --strict --verbose=2 "$PLUGIN_DEST" >/dev/null 2>&1; then
  echo 'Repairing the local plugin signature...'
  codesign --force --deep --sign - --timestamp=none "$PLUGIN_DEST"
fi
codesign --verify --deep --strict --verbose=2 "$PLUGIN_DEST"
xattr -dr com.apple.quarantine "$PLUGIN_DEST" 2>/dev/null || true

echo "Installed: $PLUGIN_DEST"

step 'Installing Analyzer connection and Cherry Studio Skill'
mkdir -p "$INSTALL_ROOT"
rm -rf "$INSTALL_ROOT/mcp" "$INSTALL_ROOT/skill"
ditto "$ROOT/mcp" "$INSTALL_ROOT/mcp"
ditto "$ROOT/skill" "$INSTALL_ROOT/skill"
for doc in START-HERE.md INSTALL.en.md INSTALL.zh-CN.md; do
  if [ -f "$ROOT/$doc" ]; then
    cp "$ROOT/$doc" "$INSTALL_ROOT/$doc"
  fi
done

xattr -dr com.apple.quarantine "$INSTALL_ROOT/mcp" 2>/dev/null || true

MCP_EXE="$INSTALL_ROOT/mcp/ai-audio-analyzer-mcp"
if [ ! -f "$MCP_EXE" ]; then
  echo "Analyzer MCP executable not found: $MCP_EXE" >&2
  exit 1
fi
chmod +x "$MCP_EXE"

step 'Checking Analyzer connection service'
AI_ANALYZER_SELF_TEST=1 "$MCP_EXE"

step 'Creating Cherry Studio configuration'
CONFIG_PATH="$INSTALL_ROOT/cherry-studio-mcp.json"
cat > "$CONFIG_PATH" <<EOF
{
  "mcpServers": {
    "ai-audio-analyzer": {
      "command": "$MCP_EXE",
      "args": [],
      "env": {
        "AI_ANALYZER_OSC_HOST": "127.0.0.1",
        "AI_ANALYZER_OSC_PORT": "9855"
      }
    }
  }
}
EOF

printf '\nInstallation completed successfully.\n'
printf '\nNext steps:\n'
printf '1. Restart FL Studio and rescan VST3 plugins.\n'
printf '2. In Cherry Studio, add this generated MCP configuration:\n   %s\n' "$CONFIG_PATH"
printf '3. Import this installed Skill folder:\n   %s\n' "$INSTALL_ROOT/skill"
printf '\nYou do not need Python, pip, Terminal, or any programming setup.\n'
