# Package Manager TUI

Modern terminal user interface for managing packages from winget and PowerShell Gallery.

## Features

- **Discover**: Search and install packages from multiple sources
- **Updates**: View and apply available updates with live progress
- **Installed**: Manage installed packages
- **Multi-select**: Checkbox selection with bulk operations
- **Async operations**: Background scanning with animated progress indicators
- **Responsive layout**: Adapts to terminal window size

## Requirements

- Python 3.8+
- Windows (for winget support)
- winget installed (optional)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python packagemanager_tui.py
```

## Keyboard Shortcuts

- **Tab / ← →**: Switch tabs
- **↑ ↓**: Navigate package list
- **Space**: Toggle package selection
- **Enter**: Apply action (install/update/uninstall)
- **Ctrl+A**: Select all packages
- **Ctrl+D**: Deselect all packages
- **Ctrl+F**: Search (Discover tab)
- **Ctrl+R**: Refresh current tab
- **Q / Esc**: Quit

## Development

Built with:
- [Textual](https://github.com/Textualize/textual) - Modern TUI framework
- [Rich](https://github.com/Textualize/rich) - Terminal formatting

## Architecture

```
packagemanager-tui/
  packagemanager_tui.py    # Main application
  requirements.txt         # Python dependencies
  README.md               # This file
```

---

Migrated from powershell-utilities issue #5
