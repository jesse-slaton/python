# Python Utilities

Python-based utilities and tools.

## Projects

### Package Manager TUI

Modern terminal user interface for managing packages from winget and other sources.

- Built with Python and Textual framework
- Features async operations with live progress indicators
- Multi-select with checkboxes for bulk operations
- Responsive layout that adapts to terminal size

### Update Catalog Fetcher

Python tool to fetch Windows updates from Microsoft Update Catalog and generate Tanium Deploy packages.

- Search and download updates by KB number, OS, and architecture
- Generate PowerShell install/remove wrapper scripts
- Create Tanium Deploy package metadata following best practices
- WQL-based install verification using Win32_QuickFixEngineering
- Support for OS requirements using registry values

## Requirements

- Python 3.8+
- See individual project requirements

## Structure

```
python/
  packagemanager-tui/       # Package manager TUI application
  update-catalog-fetcher/   # Microsoft Update Catalog fetcher for Tanium Deploy
  .gitignore               # Python gitignore
  README.md                # This file
```

## Development

See individual project directories for specific development instructions.

---

Created: 2025-10-15
