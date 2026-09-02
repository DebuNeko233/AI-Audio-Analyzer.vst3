# AI Audio Analyzer 0.9 — Start Here / 从这里开始

[English guide](INSTALL.en.md) | [中文教程](INSTALL.zh-CN.md)

This package is designed for users who have never used Python, a terminal, or programming tools.

You only need to **unzip the downloaded Release once** and run the installer inside.

## Windows

1. Download the file ending in `Windows.zip`.
2. Right-click the ZIP and choose **Extract All**.
3. Open the extracted folder.
4. Double-click `Install.cmd`.
5. Approve the Windows permission prompt if it appears.
6. Wait until the installer says **Installation completed successfully**.
7. Restart FL Studio and rescan plugins.

## macOS Apple Silicon

1. Download the file ending in `macOS.zip`.
2. Double-click the ZIP to extract it.
3. Open the extracted folder.
4. Double-click `Install.command`.
5. If macOS blocks it, right-click `Install.command` and choose **Open**.
6. Wait until the installer says **Installation completed successfully**.
7. Restart FL Studio and rescan plugins.

Current macOS Release supports **Apple Silicon (arm64) only**. Intel Macs are not supported by the packaged Release.

## What is inside

```text
AI Audio Analyzer.vst3
mcp/                         standalone Analyzer connection executable
skill/                       Cherry Studio Skill
Install.cmd / Install.ps1    Windows installer
Install.command / install.sh macOS installer
START-HERE.md
INSTALL.en.md
INSTALL.zh-CN.md
VERSION.txt
```

There is **no MCP source code** in the user Release. There is also no Python environment, package manager, requirements file, PyInstaller `_internal` folder, or nested Release ZIP inside the package.

After installation, the installer tells you where to find:

- the generated Cherry Studio MCP configuration;
- the installed Cherry Studio Skill folder.

AI Audio Analyzer 0.9 adds audio-domain chroma, tonal-center candidate evidence, and harmonic-alignment evidence internally. Installation remains exactly the same: no additional software or setup is required.

---

# 中文快速说明

这个 Release 就是按“**完全没接触过编程也能安装**”来设计的。

你不需要安装 Python，不需要 pip，不需要打开命令行，也不需要理解 MCP 源码。

## Windows

1. 下载名称以 `Windows.zip` 结尾的文件；
2. 右键 ZIP → **全部解压缩**；
3. 打开解压后的文件夹；
4. 双击 `Install.cmd`；
5. Windows 弹出权限确认时点击允许；
6. 等待显示 **Installation completed successfully**；
7. 重启 FL Studio，并重新扫描插件。

## macOS Apple Silicon

1. 下载名称以 `macOS.zip` 结尾的文件；
2. 双击 ZIP 解压；
3. 打开解压后的文件夹；
4. 双击 `Install.command`；
5. 如果 macOS 阻止运行，右键 `Install.command` → **打开**；
6. 等待显示安装成功；
7. 重启 FL Studio，并重新扫描插件。

当前 macOS Release **只支持 Apple Silicon / arm64**，不提供 Intel Mac 包。

安装完成后，安装器会直接告诉你 Cherry Studio 的 MCP 配置文件位置和 Skill 文件夹位置。

AI Audio Analyzer 0.9 新增了音频域 Chroma、Tonal-center Candidate 和 Harmonic-alignment Evidence，但安装方式没有增加任何额外步骤或依赖。