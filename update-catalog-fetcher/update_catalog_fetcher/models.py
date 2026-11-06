"""Data models for Windows updates."""

import re
from dataclasses import dataclass
from datetime import datetime

_KB_PATTERN = re.compile(r"(?:KB)?\d+", re.IGNORECASE)


def validate_kb(kb: str) -> str:
    """Return ``kb`` unchanged if it is an optional KB prefix plus digits.

    Raises:
        ValueError: If ``kb`` does not fully match ``(?:KB)?\\d+`` (case-insensitive).
    """
    if _KB_PATTERN.fullmatch(kb) is None:
        raise ValueError(f"invalid KB identifier: {kb!r}")
    return kb


@dataclass
class WindowsUpdate:
    """Represents a Windows update from the Microsoft Update Catalog."""

    title: str
    kb: str | None
    products: str
    classification: str
    last_updated: datetime
    version: str | None
    size: str
    update_id: str
    architecture: str | None
    download_url: str | None = None

    @property
    def kb_number(self) -> str | None:
        """Extract KB number without 'KB' prefix."""
        if self.kb:
            return self.kb.replace("KB", "").replace("kb", "")
        return None


@dataclass
class TaniumDeployMetadata:
    """Metadata for Tanium Deploy package."""

    vendor: str
    product_name: str
    product_version: str
    architecture: str
    disk_space_mb: int
    memory_mb: int
    install_command: str
    install_timeout: int
    install_success_codes: list[int]
    remove_command: str
    remove_timeout: int
    remove_success_codes: list[int]
    os_edition_id: str | None = None
    os_product_name: str | None = None
    os_build: str | None = None
    self_service_name: str | None = None
    self_service_icon: str | None = None
    install_requirements: str | None = None
    update_detection: str | None = None
    install_verification: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary format for JSON export."""
        return {
            "vendor": self.vendor,
            "productName": self.product_name,
            "productVersion": self.product_version,
            "architecture": self.architecture,
            "diskSpaceMB": self.disk_space_mb,
            "memoryMB": self.memory_mb,
            "installOperation": {
                "command": self.install_command,
                "timeout": self.install_timeout,
                "successCodes": self.install_success_codes,
            },
            "removeOperation": {
                "command": self.remove_command,
                "timeout": self.remove_timeout,
                "successCodes": self.remove_success_codes,
            },
            "osRequirements": {
                "editionId": self.os_edition_id,
                "productName": self.os_product_name,
                "build": self.os_build,
            },
            "selfService": {
                "name": self.self_service_name,
                "icon": self.self_service_icon,
            },
            "requirements": self.install_requirements,
            "updateDetection": self.update_detection,
            "installVerification": self.install_verification,
        }
