"""Self-update functionality for the Package Manager TUI."""

import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

import httpx


class Updater:
    """Handle self-update operations."""

    GITHUB_REPO = "jesse-slaton/python"
    GITHUB_API_BASE = "https://api.github.com"
    RELEASE_ASSET_NAME = "packagemanager-tui.exe"
    VERSION = "1.0.0"

    @staticmethod
    async def check_for_updates() -> str | None:
        """Check if a new version is available.

        Returns:
            New version string if available, None otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{Updater.GITHUB_API_BASE}/repos/{Updater.GITHUB_REPO}/releases/latest",
                    follow_redirects=True,
                )
                response.raise_for_status()
                data = response.json()

                latest_version = data.get("tag_name", "").lstrip("v")
                if latest_version and latest_version != Updater.VERSION:
                    return latest_version

                return None
        except Exception as e:
            print(f"Error checking for updates: {e}")
            return None

    @staticmethod
    async def download_update(version: str) -> Path | None:
        """Download the update file.

        Args:
            version: Version to download

        Returns:
            Path to downloaded file, or None on failure
        """
        try:
            async with httpx.AsyncClient() as client:
                # Get release info
                response = await client.get(
                    f"{Updater.GITHUB_API_BASE}/repos/{Updater.GITHUB_REPO}/releases/tags/v{version}",
                    follow_redirects=True,
                )
                response.raise_for_status()
                data = response.json()

                # Find the asset
                asset_url = None
                for asset in data.get("assets", []):
                    if asset.get("name") == Updater.RELEASE_ASSET_NAME:
                        asset_url = asset.get("browser_download_url")
                        break

                if not asset_url:
                    print(f"Could not find {Updater.RELEASE_ASSET_NAME} in release")
                    return None

                # Download the asset
                print(f"Downloading version {version}...")
                response = await client.get(asset_url, follow_redirects=True)
                response.raise_for_status()

                # Save to temp file
                temp_file = Path(tempfile.gettempdir()) / Updater.RELEASE_ASSET_NAME
                temp_file.write_bytes(response.content)

                return temp_file
        except Exception as e:
            print(f"Error downloading update: {e}")
            return None

    @staticmethod
    def apply_update(new_exe_path: Path) -> bool:
        """Apply the update by replacing the current executable.

        Args:
            new_exe_path: Path to the new executable

        Returns:
            True if update was applied successfully
        """
        try:
            # Get current executable path
            if getattr(sys, "frozen", False):
                current_exe = Path(sys.executable)
            else:
                print("Cannot update: Not running as executable")
                return False

            # Backup current executable
            backup_path = current_exe.with_suffix(".exe.bak")
            shutil.copy2(current_exe, backup_path)

            # Replace with new version
            try:
                shutil.copy2(new_exe_path, current_exe)
                print("✓ Update applied successfully!")
                print(f"Restart the application to use version {Updater.VERSION}")

                # Clean up backup
                backup_path.unlink()
                return True
            except Exception as e:
                # Restore backup on failure
                print(f"Update failed: {e}")
                if backup_path.exists():
                    shutil.copy2(backup_path, current_exe)
                    backup_path.unlink()
                return False
        except Exception as e:
            print(f"Error applying update: {e}")
            return False

    @staticmethod
    async def perform_update() -> bool:
        """Perform a full update check and installation.

        Returns:
            True if update was successful
        """
        print(f"Current version: {Updater.VERSION}")
        print("Checking for updates...")

        new_version = await Updater.check_for_updates()

        if not new_version:
            print("✓ You are running the latest version")
            return True

        print(f"New version available: {new_version}")

        # Download update
        update_file = await Updater.download_update(new_version)
        if not update_file:
            print("❌ Failed to download update")
            return False

        # Apply update
        if Updater.apply_update(update_file):
            # Clean up downloaded file
            update_file.unlink()
            return True
        print("❌ Failed to apply update")
        return False


async def main() -> None:
    """Run the updater standalone."""
    await Updater.perform_update()


if __name__ == "__main__":
    asyncio.run(main())
