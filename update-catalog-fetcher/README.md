# Update Catalog Fetcher

Python tool to fetch Windows updates from Microsoft Update Catalog and generate Tanium Deploy packages with PowerShell wrapper scripts.

## Features

- Search and download updates from Microsoft Update Catalog
- Filter by KB number, OS version, and architecture
- Generate PowerShell install/remove wrapper scripts
- Create Tanium Deploy package metadata (JSON)
- Follows Tanium best practices for hotfix packages:
  - WQL-based install verification using `Win32_QuickFixEngineering`
  - Bogus registry path for install requirements
  - OS detection using registry values instead of "Restrict Operating Systems"

## Installation

```bash
# Clone the repository
cd python/update-catalog-fetcher

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Usage

### Basic Usage

Fetch a specific KB for Windows 10 x64:

```bash
update-catalog-fetcher --kb KB5034441 --os "Windows 10" --arch x64
```

### Specifying Output Directory

```bash
update-catalog-fetcher --kb 5034441 --os "Windows 10" --arch x64 --output ./packages
```

### Windows 11 Example

```bash
update-catalog-fetcher --kb KB5034123 --os "Windows 11" --arch x64
```

### Windows Server Example

```bash
update-catalog-fetcher --kb KB5034129 --os "Windows Server 2022" --arch x64
```

### With OS Requirements

Specify OS requirements for Tanium Deploy using registry values:

```bash
update-catalog-fetcher --kb KB5034441 --os "Windows 10" --arch x64 \
    --os-edition-id Professional \
    --os-product-name "Windows 10 Pro" \
    --os-build 19045
```

### List Matching Updates

List updates without downloading:

```bash
update-catalog-fetcher --kb KB5034441 --os "Windows 10" --arch x64 --list-only
```

### Select Specific Update

If multiple updates match, select by index:

```bash
update-catalog-fetcher --kb KB5034441 --os "Windows 10" --arch x64 --select 1
```

## Command-Line Options

```
  --kb KB                  KB number to fetch (required)
  --os OS                  Operating system filter
  --arch {x64,x86,ARM64}   Architecture filter (default: x64)
  --output PATH, -o PATH   Output directory (default: current directory)
  --os-edition-id ID       Windows Edition ID (e.g., Professional)
  --os-product-name NAME   Windows Product Name (e.g., 'Windows 10 Pro')
  --os-build BUILD         Windows Build number (e.g., 19045)
  --allow-restart          Allow automatic restart (default: disabled)
  --verbose                Use verbose installation (default: quiet)
  --list-only              Only list matching updates
  --select INDEX           Select update by index (default: 0)
```

## Generated Package Structure

When you run the tool, it creates a package directory with the following structure:

```
KB5034441/
├── windows10-kb5034441-x64.msu    # Update file
├── Install-KB5034441.ps1           # Install wrapper script
├── Remove-KB5034441.ps1            # Remove wrapper script
├── tanium-deploy-metadata.json    # Tanium Deploy metadata
└── README.md                       # Package documentation
```

## Tanium Deploy Integration

1. **Upload the package**: Upload the entire package directory to Tanium Deploy

2. **Configure install operation**:
   ```
   powershell.exe -ExecutionPolicy Bypass -File ".\Install-KB5034441.ps1"
   ```

3. **Configure remove operation**:
   ```
   powershell.exe -ExecutionPolicy Bypass -File ".\Remove-KB5034441.ps1"
   ```

4. **Import metadata**: Use `tanium-deploy-metadata.json` for suggested package settings

5. **Install verification**: The metadata includes a WQL query for `Win32_QuickFixEngineering` to verify installation

6. **Install requirements**: Uses a bogus registry path per Tanium best practices for hotfixes

## Tanium Deploy Metadata

The generated `tanium-deploy-metadata.json` includes:

- Vendor, product name, and version information
- Architecture and system requirements
- Install/remove commands with timeouts and success codes
- OS requirements (EditionID, ProductName, Build)
- Install verification using WQL query
- Self-service information
- Disk space and memory requirements

Example metadata:

```json
{
  "vendor": "Microsoft",
  "productName": "Windows 10 Security Update",
  "productVersion": "KB5034441",
  "architecture": "x64",
  "diskSpaceMB": 200,
  "memoryMB": 512,
  "installOperation": {
    "command": "powershell.exe -ExecutionPolicy Bypass -File \".\\Install-KB5034441.ps1\"",
    "timeout": 1800,
    "successCodes": [0, 3010]
  },
  "removeOperation": {
    "command": "powershell.exe -ExecutionPolicy Bypass -File \".\\Remove-KB5034441.ps1\"",
    "timeout": 1200,
    "successCodes": [0, 3010]
  },
  "installVerification": "SELECT HotFixID FROM Win32_QuickFixEngineering WHERE HotFixID=\"KB5034441\"",
  "installRequirements": "Registry Path exists \"HKLM:\\\\Software\\\\Tanium\\\\Deploy\\\\BogusPath\""
}
```

## How It Works

1. **Search**: Queries Microsoft Update Catalog using BeautifulSoup to parse HTML results
2. **Filter**: Applies OS and architecture filters to find matching updates
3. **Download**: Extracts download URLs using regex patterns and downloads the update file
4. **Generate Scripts**: Creates PowerShell wrapper scripts for install/remove operations
5. **Generate Metadata**: Creates Tanium Deploy metadata following best practices

## Requirements

- Python 3.12+
- beautifulsoup4
- requests

## Development

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```

Code quality checks:

```bash
ruff check .
mypy update_catalog_fetcher
```

## Future Enhancements

- [ ] Tanium REST/GraphQL API integration to create packages automatically
- [ ] Support for dependency handling
- [ ] Integration with Microsoft Graph Windows Updates API
- [ ] Batch processing of multiple KBs
- [ ] Supersedence checking

## References

- [Tanium Deploy Documentation](https://help.tanium.com/bundle/ug_deploy_cloud/page/deploy/managing_software.html)
- [Microsoft Update Catalog](https://www.catalog.update.microsoft.com/)
- [Win32_QuickFixEngineering WMI Class](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-quickfixengineering)

## Related Issues

- Python repo issue #4: Python implementation: Microsoft Update Catalog package fetcher
- tanium-powershell repo issue #8: Original PowerShell version specification

## License

MIT

## Author

Jesse Slaton

---

**Generated**: 2025-10-16
