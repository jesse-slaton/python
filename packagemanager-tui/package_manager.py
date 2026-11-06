"""Package manager integration module for winget and other package sources."""

import asyncio
from dataclasses import dataclass
from enum import Enum


class PackageSource(Enum):
    """Package source types."""

    WINGET = "winget"
    CHOCOLATEY = "chocolatey"
    SCOOP = "scoop"


@dataclass
class Package:
    """Package information."""

    id: str
    name: str
    version: str
    available_version: str | None = None
    source: str = "winget"
    description: str = ""

    @property
    def has_update(self) -> bool:
        """Check if package has an update available."""
        return self.available_version is not None and self.available_version != self.version


class WingetManager:
    """Winget package manager integration."""

    @staticmethod
    async def run_command(args: list[str]) -> tuple[str, str, int]:
        """Run a winget command asynchronously.

        Args:
            args: Command arguments to pass to winget

        Returns:
            Tuple of (stdout, stderr, return_code)
        """
        process = await asyncio.create_subprocess_exec(
            "winget",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            stdout.decode("utf-8", errors="ignore"),
            stderr.decode("utf-8", errors="ignore"),
            process.returncode or 0,
        )

    @staticmethod
    async def search(query: str) -> list[Package]:
        """Search for packages.

        Args:
            query: Search query string

        Returns:
            List of matching packages
        """
        stdout, _, returncode = await WingetManager.run_command(
            ["search", query, "--accept-source-agreements"]
        )

        if returncode != 0:
            return []

        packages = []
        lines = stdout.strip().split("\n")

        # Skip header lines
        data_started = False
        for line in lines:
            if not data_started:
                if line.startswith("-"):
                    data_started = True
                continue

            # Parse line - format: Name  Id  Version  Source
            parts = line.split()
            if len(parts) >= 3:
                # Find the last two parts (version and source)
                source = parts[-1] if len(parts) >= 4 else "winget"
                version = parts[-2] if len(parts) >= 3 else "Unknown"

                # Everything before version is the ID
                # Find where version starts by checking from the end
                line_parts = line.split()
                version_index = -2 if len(line_parts) >= 4 else -1  # noqa: F841  dead assignment; deleting it is a code change deferred to burn-down

                # Get ID (usually second to last or third to last segment)
                pkg_id = parts[-3] if len(parts) >= 4 else parts[0]

                # Name is everything before the ID
                name_end = line.find(pkg_id)
                name = line[:name_end].strip() if name_end > 0 else pkg_id

                packages.append(
                    Package(
                        id=pkg_id, name=name, version=version, source=source, description=""
                    )
                )

        return packages

    @staticmethod
    async def get_installed() -> list[Package]:
        """Get list of installed packages.

        Returns:
            List of installed packages
        """
        stdout, _, returncode = await WingetManager.run_command(["list"])

        if returncode != 0:
            return []

        packages = []
        lines = stdout.strip().split("\n")

        # Skip header lines
        data_started = False
        for line in lines:
            if not data_started:
                if line.startswith("-"):
                    data_started = True
                continue

            # Parse line similar to search
            parts = line.split()
            if len(parts) >= 2:
                source = parts[-1] if len(parts) >= 4 else "winget"
                version = parts[-2] if len(parts) >= 3 else "Unknown"
                available = parts[-3] if len(parts) >= 4 and parts[-3] != parts[-2] else None

                # Get package ID
                if len(parts) >= 4:  # noqa: SIM108  explicit if/else is clearer than the nested ternary; no refactor in baseline
                    pkg_id = parts[-4] if available else parts[-3]
                else:
                    pkg_id = parts[0]

                # Get name
                name_end = line.find(pkg_id)
                name = line[:name_end].strip() if name_end > 0 else pkg_id

                packages.append(
                    Package(
                        id=pkg_id,
                        name=name,
                        version=version,
                        available_version=available,
                        source=source,
                    )
                )

        return packages

    @staticmethod
    async def get_updates() -> list[Package]:
        """Get list of packages with updates available.

        Returns:
            List of packages that can be updated
        """
        stdout, _, returncode = await WingetManager.run_command(["upgrade"])

        if returncode != 0:
            return []

        packages = []
        lines = stdout.strip().split("\n")

        # Skip header lines
        data_started = False
        for line in lines:
            if not data_started:
                if line.startswith("-"):
                    data_started = True
                continue

            # Skip summary lines
            if "upgrades available" in line.lower():
                break

            # Parse line - format: Name  Id  Version  Available  Source
            parts = line.split()
            if len(parts) >= 4:
                source = parts[-1]
                available_version = parts[-2]
                current_version = parts[-3]
                pkg_id = parts[-4]

                # Name is everything before the ID
                name_end = line.find(pkg_id)
                name = line[:name_end].strip() if name_end > 0 else pkg_id

                packages.append(
                    Package(
                        id=pkg_id,
                        name=name,
                        version=current_version,
                        available_version=available_version,
                        source=source,
                    )
                )

        return packages

    @staticmethod
    async def install(package_id: str) -> bool:
        """Install a package.

        Args:
            package_id: Package identifier to install

        Returns:
            True if installation succeeded
        """
        _, _, returncode = await WingetManager.run_command(
            ["install", "--id", package_id, "--silent", "--accept-source-agreements"]
        )
        return returncode == 0

    @staticmethod
    async def uninstall(package_id: str) -> bool:
        """Uninstall a package.

        Args:
            package_id: Package identifier to uninstall

        Returns:
            True if uninstallation succeeded
        """
        _, _, returncode = await WingetManager.run_command(["uninstall", "--id", package_id])
        return returncode == 0

    @staticmethod
    async def upgrade(package_id: str) -> bool:
        """Upgrade a package.

        Args:
            package_id: Package identifier to upgrade

        Returns:
            True if upgrade succeeded
        """
        _, _, returncode = await WingetManager.run_command(
            ["upgrade", "--id", package_id, "--silent", "--accept-source-agreements"]
        )
        return returncode == 0

    @staticmethod
    async def upgrade_all(package_ids: list[str]) -> dict[str, bool]:
        """Upgrade multiple packages.

        Args:
            package_ids: List of package identifiers to upgrade

        Returns:
            Dictionary mapping package_id to success status
        """
        results = {}
        for pkg_id in package_ids:
            results[pkg_id] = await WingetManager.upgrade(pkg_id)
        return results
