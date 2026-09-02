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

case "$(uname -m)" in
  arm64)
    MCP_ARCH="arm64"
    ;;
  x86_64)
    MCP_ARCH="x86_64"
    ;;
  *)
    echo "Unsupported macOS architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

echo 'AI Audio Analyzer automatic installer'
echo "Package: $ROOT"
echo "Architecture: $MCP_ARCH"

step 'Removing package quarantine metadata where possible'
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
  echo 'Existing ad-hoc signature did not verify after installation; re-signing locally.'
  codesign --force --deep --sign - --timestamp=none "$PLUGIN_DEST"
fi
codesign --verify --deep --strict --verbose=2 "$PLUGIN_DEST"
xattr -dr com.apple.quarantine "$PLUGIN_DEST" 2>/dev/null || true
echo "Installed: $PLUGIN_DEST"

step 'Installing packaged Analyzer MCP and Skill'
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

MCP_EXE="$INSTALL_ROOT/mcp/runtime/$MCP_ARCH/ai-audio-analyzer-mcp/ai-audio-analyzer-mcp"
if [ ! -f "$MCP_EXE" ]; then
  echo "Packaged MCP executable not found: $MCP_EXE" >&2
  exit 1
fi
chmod +x "$MCP_EXE"

step 'Validating packaged MCP runtime'
AI_ANALYZER_SELF_TEST=1 "$MCP_EXE"

step 'Generating Cherry Studio MCP configuration'
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

printf '\nInstallation completed.\n'
printf 'Python and pip are NOT required for the packaged MCP runtime.\n'
printf 'VST3: %s\n' "$PLUGIN_DEST"
printf 'MCP executable: %s\n' "$MCP_EXE"
printf 'MCP config: %s\n' "$CONFIG_PATH"
printf 'Skill folder: %s\n' "$INSTALL_ROOT/skill"
printf '\nNext:\n'
printf '1. Fully quit and restart FL Studio, then rescan VST3 plugins.\n'
printf '2. Add the generated MCP config to Cherry Studio.\n'
printf '3. Import the Skill folder into Cherry Studio.\n'
printf '4. For DAW control, also install https://github.com/rosasynthesiz/flstudio-mcp\n'
printf '\nDeveloper/manual Python fallback remains under mcp/source.\n'
