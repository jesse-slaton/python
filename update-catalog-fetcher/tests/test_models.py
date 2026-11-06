"""Tests for data models."""

from datetime import datetime

from update_catalog_fetcher.models import TaniumDeployMetadata, WindowsUpdate


class TestWindowsUpdate:
    """Tests for WindowsUpdate model."""

    def test_kb_number_property(self):
        """Test KB number extraction."""
        update = WindowsUpdate(
            title="Test Update",
            kb="KB5034441",
            products="Windows 10",
            classification="Security Updates",
            last_updated=datetime.now(),
            version="1.0",
            size="100 MB",
            update_id="12345",
            architecture="x64",
        )

        assert update.kb_number == "5034441"

    def test_kb_number_lowercase(self):
        """Test KB number extraction with lowercase."""
        update = WindowsUpdate(
            title="Test Update",
            kb="kb5034441",
            products="Windows 10",
            classification="Security Updates",
            last_updated=datetime.now(),
            version="1.0",
            size="100 MB",
            update_id="12345",
            architecture="x64",
        )

        assert update.kb_number == "5034441"

    def test_kb_number_none(self):
        """Test KB number when None."""
        update = WindowsUpdate(
            title="Test Update",
            kb=None,
            products="Windows 10",
            classification="Security Updates",
            last_updated=datetime.now(),
            version="1.0",
            size="100 MB",
            update_id="12345",
            architecture="x64",
        )

        assert update.kb_number is None


class TestTaniumDeployMetadata:
    """Tests for TaniumDeployMetadata model."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        metadata = TaniumDeployMetadata(
            vendor="Microsoft",
            product_name="Test Product",
            product_version="1.0",
            architecture="x64",
            disk_space_mb=100,
            memory_mb=512,
            install_command="install.ps1",
            install_timeout=1800,
            install_success_codes=[0, 3010],
            remove_command="remove.ps1",
            remove_timeout=1200,
            remove_success_codes=[0, 3010],
            os_edition_id="Professional",
            os_product_name="Windows 10 Pro",
            os_build="19045",
            install_requirements='Registry Path exists "HKLM:\\\\Software\\\\Test"',
            install_verification='SELECT * FROM Win32_QuickFixEngineering WHERE HotFixID="KB123"',
        )

        result = metadata.to_dict()

        assert result["vendor"] == "Microsoft"
        assert result["productName"] == "Test Product"
        assert result["architecture"] == "x64"
        assert result["installOperation"]["command"] == "install.ps1"
        assert result["installOperation"]["successCodes"] == [0, 3010]
        assert result["osRequirements"]["editionId"] == "Professional"
        assert result["requirements"] == 'Registry Path exists "HKLM:\\\\Software\\\\Test"'
