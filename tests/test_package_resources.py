"""
Tests for package resource loading using AAA pattern
"""

import dataclasses
import importlib.resources
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from dnsping.scanner import DNSLatencyScanner, ScanConfig


class TestPackageResources:
    """Test package resource loading with AAA pattern"""

    @pytest.fixture
    def scanner_config(self, tmp_path):
        """Create scanner configuration"""
        # Arrange
        return ScanConfig(
            dns_file=Path("dns_servers.txt"),
            max_servers=5,
            ping_count=1,
            timeout=0.1,
        )

    @pytest.fixture
    def scanner(self, scanner_config):
        """Create scanner instance"""
        # Arrange
        return DNSLatencyScanner(scanner_config)

    @pytest.mark.asyncio
    async def test_load_dns_servers_package_resource(self, scanner_config, tmp_path):
        """Test loading DNS servers from package resource"""
        # Arrange
        from pathlib import Path

        config = dataclasses.replace(scanner_config, dns_file=Path("dns_servers.txt"))
        scanner = DNSLatencyScanner(config)
        # File doesn't exist in current directory

        # Act
        with patch("pathlib.Path.exists", return_value=False):
            with patch("importlib.resources.files") as mock_files:
                mock_package = MagicMock()
                mock_resource = tmp_path / "dns_servers.txt"
                mock_resource.write_text("# Test\n8.8.8.8\n1.1.1.1\n")
                mock_files.return_value.__truediv__.return_value = mock_resource
                servers = await scanner.load_dns_servers()

        # Assert
        assert len(servers) == 2, "Should load from package resource"

    @pytest.mark.asyncio
    async def test_load_dns_servers_package_resource_fallback(self, scanner_config, tmp_path):
        """Test loading DNS servers with pkg_resources fallback"""
        # Arrange
        from pathlib import Path

        config = dataclasses.replace(scanner_config, dns_file=Path("dns_servers.txt"))
        scanner = DNSLatencyScanner(config)

        # Act
        try:
            import pkg_resources
        except ImportError:
            pytest.skip("pkg_resources not available")

        with patch("pathlib.Path.exists", return_value=False):
            with patch("importlib.resources.files", side_effect=AttributeError("No attribute")):
                with patch("pkg_resources.resource_filename") as mock_resource:
                    mock_resource.return_value = str(tmp_path / "dns_servers.txt")
                    (tmp_path / "dns_servers.txt").write_text("# Test\n8.8.8.8\n")
                    servers = await scanner.load_dns_servers()

        # Assert
        assert len(servers) == 1, "Should use pkg_resources fallback"

    @pytest.mark.asyncio
    async def test_load_dns_servers_local_file_exists(self, scanner_config, tmp_path):
        """Test loading DNS servers from local file when it exists"""
        # Arrange
        local_file = tmp_path / "dns_servers.txt"
        local_file.write_text("# Local\n8.8.8.8\n1.1.1.1\n")
        config = dataclasses.replace(scanner_config, dns_file=local_file)
        scanner = DNSLatencyScanner(config)

        # Act
        servers = await scanner.load_dns_servers()

        # Assert
        assert len(servers) == 2, "Should load from local file"
        assert scanner.providers["8.8.8.8"] == "Local", "Should use local file provider"

    @pytest.mark.asyncio
    async def test_load_dns_servers_custom_file(self, scanner_config, tmp_path):
        """Test loading DNS servers from custom file"""
        # Arrange
        custom_file = tmp_path / "custom_dns.txt"
        custom_file.write_text("# Custom\n9.9.9.9\n")
        config = dataclasses.replace(scanner_config, dns_file=custom_file)
        scanner = DNSLatencyScanner(config)

        # Act
        servers = await scanner.load_dns_servers()

        # Assert
        assert len(servers) == 1, "Should load from custom file"
        assert "9.9.9.9" in servers, "Should include custom server"
