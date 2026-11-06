"""Tanium Deploy package metadata generator."""

import json
import re
from pathlib import Path
from typing import Optional

from .models import TaniumDeployMetadata, WindowsUpdate


class MetadataGenerator:
    """Generates Tanium Deploy package metadata."""

    @staticmethod
    def generate_metadata(
        update: WindowsUpdate,
        install_script: str,
        remove_script: str,
        update_file_name: str,
        os_edition_id: Optional[str] = None,
        os_product_name: Optional[str] = None,
        os_build: Optional[str] = None,
    ) -> TaniumDeployMetadata:
        """Generate Tanium Deploy metadata for an update.

        Args:
            update: The WindowsUpdate object
            install_script: Name of the install script
            remove_script: Name of the remove script
            update_file_name: Name of the update file
            os_edition_id: Windows Edition ID (from registry)
            os_product_name: Windows Product Name (from registry)
            os_build: Windows Build number (from registry)

        Returns:
            TaniumDeployMetadata object
        """
        # Parse file size to MB
        size_mb = MetadataGenerator._parse_size_to_mb(update.size)

        # Estimate disk space (2x file size for safety)
        disk_space_mb = max(size_mb * 2, 100)

        # Memory requirement (conservative estimate)
        memory_mb = 512

        # Determine vendor
        vendor = "Microsoft"

        # Generate product name
        product_name = MetadataGenerator._generate_product_name(update)

        # Product version
        product_version = update.version or update.kb or "Unknown"

        # Architecture
        architecture = update.architecture or "x64"

        # Install operation
        install_command = f'powershell.exe -ExecutionPolicy Bypass -File ".\\{install_script}"'
        install_timeout = 1800  # 30 minutes
        install_success_codes = [0, 3010]  # Success and success with reboot

        # Remove operation
        remove_command = f'powershell.exe -ExecutionPolicy Bypass -File ".\\{remove_script}"'
        remove_timeout = 1200  # 20 minutes
        remove_success_codes = [0, 3010]  # Success and success with reboot

        # Self-service name
        self_service_name = f"{update.kb} - {update.classification}"

        # Install requirements - Use bogus path so install always runs
        # This is Tanium's best practice for hotfixes
        install_requirements = 'Registry Path exists "HKLM:\\Software\\Tanium\\Deploy\\BogusPath"'

        # Install verification - Use WQL query for Win32_QuickFixEngineering
        install_verification = MetadataGenerator._generate_wql_verification(update)

        # Update detection is not used for hotfixes (no update operation)
        update_detection = None

        return TaniumDeployMetadata(
            vendor=vendor,
            product_name=product_name,
            product_version=product_version,
            architecture=architecture,
            disk_space_mb=disk_space_mb,
            memory_mb=memory_mb,
            install_command=install_command,
            install_timeout=install_timeout,
            install_success_codes=install_success_codes,
            remove_command=remove_command,
            remove_timeout=remove_timeout,
            remove_success_codes=remove_success_codes,
            os_edition_id=os_edition_id,
            os_product_name=os_product_name,
            os_build=os_build,
            self_service_name=self_service_name,
            install_requirements=install_requirements,
            install_verification=install_verification,
            update_detection=update_detection,
        )

    @staticmethod
    def _parse_size_to_mb(size_str: str) -> int:
        """Parse size string to megabytes.

        Args:
            size_str: Size string (e.g., '100 MB', '1.5 GB', '500 KB')

        Returns:
            Size in megabytes
        """
        try:
            # Remove commas and split
            size_str = size_str.replace(",", "").strip()
            match = re.match(r"([\d.]+)\s*([KMGT]?B)", size_str, re.IGNORECASE)

            if not match:
                return 100  # Default

            value = float(match.group(1))
            unit = match.group(2).upper()

            # Convert to MB
            if unit == "KB":
                return max(int(value / 1024), 1)
            if unit == "MB":
                return max(int(value), 1)
            if unit == "GB":
                return max(int(value * 1024), 1)
            if unit == "TB":
                return max(int(value * 1024 * 1024), 1)
            return 100  # Default
        except (ValueError, AttributeError):
            return 100  # Default

    @staticmethod
    def _generate_product_name(update: WindowsUpdate) -> str:
        """Generate a product name from the update."""
        # Try to extract a meaningful name from the title
        title = update.title

        # Remove common prefixes
        for prefix in [
            "Update for ",
            "Security Update for ",
            "Cumulative Update for ",
        ]:
            if title.startswith(prefix):
                title = title[len(prefix) :]
                break

        # Remove KB number from title
        if update.kb:
            title = title.replace(f"({update.kb})", "").replace(update.kb, "")

        # Clean up
        title = " ".join(title.split())

        return title[:100]  # Limit length

    @staticmethod
    def _generate_wql_verification(update: WindowsUpdate) -> str:
        """Generate WQL query for install verification.

        Returns WQL query string for Win32_QuickFixEngineering.
        Per Tanium best practices for hotfix packages.
        """
        if not update.kb:
            return ""

        kb_number = update.kb_number or update.kb.replace("KB", "")

        # WQL query to check if KB is installed
        # Uses Win32_QuickFixEngineering WMI class
        wql_query = f'SELECT HotFixID FROM Win32_QuickFixEngineering WHERE HotFixID="KB{kb_number}"'

        return wql_query

    @staticmethod
    def save_metadata(metadata: TaniumDeployMetadata, output_path: Path) -> Path:
        """Save metadata to JSON file.

        Args:
            metadata: The TaniumDeployMetadata object
            output_path: Path to save the JSON file

        Returns:
            Path to the saved file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        return output_path

    @staticmethod
    def generate_readme(
        update: WindowsUpdate,
        update_file_name: str,
        install_script: str,
        remove_script: str,
        metadata_file: str,
    ) -> str:
        """Generate README for the package.

        Args:
            update: The WindowsUpdate object
            update_file_name: Name of the update file
            install_script: Name of the install script
            remove_script: Name of the remove script
            metadata_file: Name of the metadata JSON file

        Returns:
            README content in Markdown format
        """
        return f"""# {update.kb or 'Windows Update'} - Tanium Deploy Package

## Update Information

- **Title**: {update.title}
- **KB**: {update.kb or 'N/A'}
- **Classification**: {update.classification}
- **Products**: {update.products}
- **Architecture**: {update.architecture or 'N/A'}
- **Size**: {update.size}
- **Last Updated**: {update.last_updated.strftime('%Y-%m-%d')}
- **Update ID**: {update.update_id}

## Package Contents

- `{update_file_name}` - Update package file
- `{install_script}` - Install wrapper script
- `{remove_script}` - Remove wrapper script
- `{metadata_file}` - Tanium Deploy metadata
- `README.md` - This file

## Installation

To install this update via Tanium Deploy:

1. Upload the entire package directory to Tanium Deploy
2. Configure the install operation to run: `{install_script}`
3. Configure the remove operation to run: `{remove_script}`
4. Import metadata from `{metadata_file}` for suggested settings

## Manual Installation

To install manually:

```powershell
.\\{install_script}
```

## Manual Removal

To remove manually:

```powershell
.\\{remove_script}
```

## Requirements

- Windows operating system matching the update products
- PowerShell 5.1 or later
- Administrative privileges

## Notes

- The install script uses quiet installation by default
- Automatic restart is suppressed by default
- Check the Tanium Deploy metadata for recommended settings
- See the Tanium Deploy documentation for best practices: https://help.tanium.com/bundle/ug_deploy_cloud/page/deploy/managing_software.html

## Generated By

This package was generated using `update-catalog-fetcher`.

**Generated on**: {Path.ctime}
"""
