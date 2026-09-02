# Release / 懒人包发布说明

The normal `build` workflow is for development artifacts. User-facing lazy packages are created by the separate manual workflow:

```text
.github/workflows/release.yml
```

## Publish a release from GitHub UI

1. Open the repository on GitHub.
2. Open **Actions**.
3. Select **release-lazy-package**.
4. Click **Run workflow**.
5. `tag` can be left empty. The workflow then reads the version from `CMakeLists.txt` and uses `v<version>`; for example `v0.4.1`.
6. Enable `prerelease` only for beta/test releases.
7. Enable `draft` if the release should not be public immediately.
8. Click **Run workflow**.

The workflow builds both platforms from the same commit and publishes:

```text
AI-Audio-Analyzer-v<version>-Windows.zip
AI-Audio-Analyzer-v<version>-macOS.zip
SHA256SUMS.txt
```

Each platform ZIP contains the VST3, `mcp/`, `skill/`, automatic installer, English manual, Simplified Chinese manual, and `START-HERE.md`.

If the tag already has a GitHub Release, re-running the workflow replaces the ZIP/checksum assets and updates the release notes instead of creating a duplicate release.

## 中文说明

普通 `build` Action 是开发阶段工件。真正给用户下载的“懒人包”由 `release-lazy-package` 手动发布。

GitHub 页面操作：

```text
Actions
→ release-lazy-package
→ Run workflow
```

`tag` 留空时自动读取 `CMakeLists.txt` 里的版本号。例如项目版本是 `0.4.1`，最终 Release Tag 就是：

```text
v0.4.1
```

正式版保持：

```text
prerelease = false
draft      = false
```

测试版本可以勾选 `prerelease`；想先检查 Release 页面再公开可以勾选 `draft`。

工作流会分别在 macOS 和 Windows Runner 上重新构建 VST3，并生成两个独立安装包，然后自动创建 / 更新 GitHub Release。

## Installer validation

Changes under `release/**` or `.github/workflows/release.yml` are smoke-tested by the normal `build` workflow without rebuilding the VST3:

```text
Windows  → parse Install.ps1
Linux    → bash -n install.sh / Install.command
VST3     → skipped
```

This keeps installer changes cheap to validate while the manual Release workflow still performs a clean platform build before publishing.
