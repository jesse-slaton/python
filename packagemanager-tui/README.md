# Package Manager TUI

Modern terminal user interface for managing Windows packages via winget and other package managers.

## Features

- **Discover Tab**: Search and install packages from winget
- **Updates Tab**: View and install available package updates
- **Installed Tab**: View and uninstall installed packages
- **Settings Tab**: Application information and keyboard shortcuts
- **Async Operations**: Non-blocking package operations with progress indicators
- **Multi-Select**: Use checkboxes to select multiple packages for bulk operations
- **Self-Updating**: Built-in update mechanism via `-U` flag

## Installation

### From Source

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python packagemanager_tui.py
```

### Building Portable EXE

1. Install build dependencies:
```bash
pip install pyinstaller
```

2. Build the executable:
```bash
pyinstaller build.spec
```

The executable will be created in the `dist/` directory as `packagemanager-tui.exe`.

## Usage

### Running the TUI

Simply run the executable or Python script:
```bash
packagemanager-tui.exe
# or
python packagemanager_tui.py
```

### Keyboard Shortcuts

- `Space` - Toggle package selection
- `Ctrl+A` - Select all packages
- `Ctrl+D` - Deselect all packages
- `Ctrl+R` - Refresh current tab
- `Q` - Quit application

### Command Line Options

- `-U`, `--update` - Check for and install application updates
- `-v`, `--version` - Show version information
- `-h`, `--help` - Show help message

### Self-Updating

To update the application to the latest version:
```bash
packagemanager-tui.exe -U
```

This will:
1. Check GitHub releases for the latest version
2. Download the new executable if available
3. Replace the current executable
4. Prompt to restart

## Requirements

- Windows 10 or later
- winget (Windows Package Manager)
- Python 3.12+ (for running from source)

## Architecture

- **packagemanager_tui.py**: Main application with Textual UI
- **package_manager.py**: Winget integration and async package operations
- **widgets.py**: Custom TUI widgets (PackageTable, SearchBox, StatusBar)
- **updater.py**: Self-update functionality via GitHub releases
- **build.spec**: PyInstaller configuration for EXE generation

## Development

See the main repository [DEVELOPMENT.md](../DEVELOPMENT.md) for development guidelines, testing, and code quality standards.

## License

See repository LICENSE file.

## Author

Jesse Slaton
