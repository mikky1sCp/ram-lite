# RAM Lite

A lightweight, personal Roblox account manager for Windows 10/11.

![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-6.8-41CD52?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D4?logo=windows)
![Version](https://img.shields.io/badge/version-0.7.0-blueviolet)
![License](https://img.shields.io/badge/license-MIT-green)

> A personal desktop tool to store Roblox accounts, import cookies, launch multiple clients, keep them alive, and protect everything with strong encryption. Built from scratch with a focus on clean UI, working features, and honest tests.

---

## ✨ Features

- **Account management** — import `.ROBLOSECURITY` cookies, view avatars, edit notes, search, delete.
- **Encrypted storage** — AES-GCM (PBKDF2, 200k iterations) with a user password. Only the salt is written to disk.
- **Cookie validator** — checks all cookies on startup and flags expired ones with a red badge.
- **Single launch** — open Roblox Home or jump into a Place ID with one click.
- **Multi-instance** — run several clients at once via the `ROBLOX_singletonEvent` mutex trick.
- **Instance Guard** — experimental native handle cleanup that keeps multi-instanced windows from closing after the Byfron time limit.
- **Launcher support** — default Windows handler, Bloxstrap, or direct `RobloxPlayerBeta.exe`.
- **Background workers** — imports, cookie checks, avatar downloads, and launches never block the UI.
- **Custom dark theme** — frameless window, custom title bar, consistent styling across dialogs.

---

## 🖼️ Screenshots

### Account list
![Account list](docs/screenshots/accounts.png)

### Settings
![Settings](docs/screenshots/settings.png)

### Multi-launch (context menu)
![Context menu](docs/screenshots/context-menu.png)

### Multiple Roblox clients running
![Multi launch](docs/screenshots/launch.png)

### Password prompt on startup
![Password prompt](docs/screenshots/encryption.png)

---

## 📋 Requirements

- **Windows 10 or Windows 11**
- **Python 3.12** (uv installs it automatically)
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** 0.4+
- **Roblox Player** installed from [roblox.com](https://www.roblox.com)

---

## 🚀 Installation

```powershell
# 1. Clone or download the project
git clone <your-fork-url> ram-lite
cd ram-lite

# 2. Install dependencies
uv sync

# 3. Run
uv run python src/main.py
