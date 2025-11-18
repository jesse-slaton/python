"""Data models for Windows updates."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WindowsUpdate:
    """Represents a Windows update from the Microsoft Update Catalog."""

    title: str
    kb: Optional[str]
    products: str
    classification: str
    last_updated: datetime
    version: Optional[str]
    size: str
    update_id: str
    architecture: Optional[str]
    download_url: Optional[str] = None

    @property
    def kb_number(self) -> Optional[str]:
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
    os_edition_id: Optional[str] = None
    os_product_name: Optional[str] = None
    os_build: Optional[str] = None
    self_service_name: Optional[str] = None
    self_service_icon: Optional[str] = None
    install_requirements: Optional[str] = None
    update_detection: Optional[str] = None
    install_verification: Optional[str] = None

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
