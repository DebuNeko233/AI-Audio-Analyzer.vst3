#!/bin/bash
set +e
DIR="$(cd "$(dirname "$0")" && pwd)"
xattr -dr com.apple.quarantine "$DIR" 2>/dev/null || true
/bin/bash "$DIR/install.sh"
STATUS=$?
printf '\n'
if [ "$STATUS" -ne 0 ]; then
  echo "Installation failed with exit code $STATUS."
  echo 'Read INSTALL.zh-CN.md or INSTALL.en.md for manual installation and troubleshooting.'
else
  echo 'Installation finished successfully.'
fi
printf '\nPress Enter to close this window...'
read -r _
exit "$STATUS"
