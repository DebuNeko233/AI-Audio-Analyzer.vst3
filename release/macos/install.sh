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
VENV_ROOT="$INSTALL_ROOT/venv"
PYPI_MODE="${AI_ANALYZER_PYPI:-auto}"
PYTHON=""

find_python() {
  local c
  for c in python3.12 python3 python; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' >/dev/null 2>&1; then
        command -v "$c"
        return 0
      fi
    fi
  done
  return 1
}

setup_brew_path() {
  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
}

install_python_if_needed() {
  local python_path
  if python_path="$(find_python)"; then
    PYTHON="$python_path"
    return 0
  fi

  setup_brew_path
  if command -v brew >/dev/null 2>&1; then
    step 'Python 3.10+ not found; installing Python 3.12 with Homebrew'
    brew install python@3.12
    setup_brew_path
    if python_path="$(find_python)"; then
      PYTHON="$python_path"
      return 0
    fi
  fi

  printf '\nPython 3.10+ and Homebrew were not found.\n'
  if [ -t 0 ]; then
    read -r -p 'Install Homebrew now, then install Python 3.12? [y/N] ' answer
    case "$answer" in
      y|Y|yes|YES)
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        setup_brew_path
        brew install python@3.12
        if python_path="$(find_python)"; then
          PYTHON="$python_path"
          return 0
        fi
        ;;
    esac
  fi

  printf '%s\n' 'Install Python 3.12 manually, then run Install.command again:' >&2
  printf '%s\n' 'https://www.python.org/downloads/macos/' >&2
  return 1
}

pypi_indexes() {
  case "$PYPI_MODE" in
    official)
      printf '%s\n' 'https://pypi.org/simple'
      ;;
    tsinghua)
      printf '%s\n' 'https://pypi.tuna.tsinghua.edu.cn/simple'
      ;;
    aliyun)
      printf '%s\n' 'https://mirrors.aliyun.com/pypi/simple/'
      ;;
    auto)
      printf '%s\n' \
        'https://pypi.org/simple' \
        'https://pypi.tuna.tsinghua.edu.cn/simple' \
        'https://mirrors.aliyun.com/pypi/simple/'
      ;;
    *)
      printf '%s\n' "Unknown AI_ANALYZER_PYPI mode: $PYPI_MODE" >&2
      return 1
      ;;
  esac
}

echo 'AI Audio Analyzer automatic installer'
echo "Package: $ROOT"

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

step 'Preparing Analyzer MCP and Skill'
mkdir -p "$INSTALL_ROOT"
rm -rf "$INSTALL_ROOT/mcp" "$INSTALL_ROOT/skill"
ditto "$ROOT/mcp" "$INSTALL_ROOT/mcp"
ditto "$ROOT/skill" "$INSTALL_ROOT/skill"
for doc in START-HERE.md INSTALL.en.md INSTALL.zh-CN.md; do
  if [ -f "$ROOT/$doc" ]; then
    cp "$ROOT/$doc" "$INSTALL_ROOT/$doc"
  fi
done

step 'Checking Python'
install_python_if_needed
echo "Python: $PYTHON"
"$PYTHON" -c "import sys; print('Python', sys.version)"

step 'Creating isolated MCP virtual environment'
rm -rf "$VENV_ROOT"
"$PYTHON" -m venv "$VENV_ROOT"
VENV_PYTHON="$VENV_ROOT/bin/python"
"$VENV_PYTHON" -m pip install --upgrade pip --disable-pip-version-check || true

step 'Installing MCP dependencies'
REQUIREMENTS="$INSTALL_ROOT/mcp/requirements.txt"
installed=0
while IFS= read -r index; do
  [ -z "$index" ] && continue
  echo "Trying PyPI index: $index"
  if "$VENV_PYTHON" -m pip install \
      --disable-pip-version-check \
      --timeout 30 \
      --retries 2 \
      -i "$index" \
      -r "$REQUIREMENTS"; then
    installed=1
    echo "Dependencies installed from: $index"
    break
  fi
  echo "Dependency installation failed from $index" >&2
done < <(pypi_indexes)

if [ "$installed" -ne 1 ]; then
  echo 'Could not install MCP dependencies from any configured PyPI index.' >&2
  echo 'Read INSTALL.zh-CN.md / INSTALL.en.md.' >&2
  exit 1
fi

step 'Validating MCP runtime'
SERVER_PATH="$INSTALL_ROOT/mcp/server.py"
"$VENV_PYTHON" -m py_compile "$SERVER_PATH"
"$VENV_PYTHON" -c "from mcp.server import MCPServer; import pythonosc; print('MCP v2 runtime OK')"

step 'Generating Cherry Studio MCP configuration'
CONFIG_PATH="$INSTALL_ROOT/cherry-studio-mcp.json"
AI_INSTALL_ROOT="$INSTALL_ROOT" AI_VENV_PYTHON="$VENV_PYTHON" \
  "$VENV_PYTHON" - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ['AI_INSTALL_ROOT'])
config = {
    'mcpServers': {
        'ai-audio-analyzer': {
            'command': os.environ['AI_VENV_PYTHON'],
            'args': [str(root / 'mcp' / 'server.py')],
            'env': {
                'AI_ANALYZER_OSC_HOST': '127.0.0.1',
                'AI_ANALYZER_OSC_PORT': '9855',
            },
        }
    }
}
(root / 'cherry-studio-mcp.json').write_text(
    json.dumps(config, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
)
PY

printf '\nInstallation completed.\n'
printf 'VST3: %s\n' "$PLUGIN_DEST"
printf 'MCP config: %s\n' "$CONFIG_PATH"
printf 'Skill folder: %s\n' "$INSTALL_ROOT/skill"
printf '\nNext:\n'
printf '1. Fully quit and restart FL Studio, then rescan VST3 plugins.\n'
printf '2. Add the generated MCP config to Cherry Studio.\n'
printf '3. Import the Skill folder into Cherry Studio.\n'
printf '4. For DAW control, also install https://github.com/rosasynthesiz/flstudio-mcp\n'
