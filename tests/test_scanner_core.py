"""
Tests for DNSLatencyScanner core functionality using AAA pattern
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from dnsping.scanner import DNSLatencyScanner, ScanConfig


class TestDNSLatencyScanner:
    """Test DNSLatencyScanner core functionality with AAA pattern"""

    @pytest.fixture
    def temp_dns_file(self, tmp_path):
        """Create a temporary DNS servers file"""
        # Arrange
        dns_file = tmp_path / "test_dns.txt"
        dns_file.write_text("# Test Provider\n8.8.8.8\n1.1.1.1\n")
        return dns_file

    @pytest.fixture
    def scanner_config(self, temp_dns_file):
        """Create a scanner configuration"""
        # Arrange
        return ScanConfig(
            dns_file=temp_dns_file,
            max_servers=2,
            ping_count=1,
            timeout=0.5,
            enable_ping=False,
            enable_socket=False,
            enable_dns_query=False,  # Disable all for faster tests
        )

    @pytest.fixture
    def scanner(self, scanner_config):
        """Create a scanner instance"""
        # Arrange
        return DNSLatencyScanner(scanner_config)

    def test_scanner_initialization(self, scanner_config):
        """Test scanner initialization"""
        # Arrange & Act
        scanner = DNSLatencyScanner(scanner_config)

        # Assert
        assert scanner.config == scanner_config, "Config should be set"
        assert scanner.dns_servers == [], "DNS servers should be empty initially"
        assert scanner.running == True, "Running should be True initially"
        assert scanner.results == {}, "Results should be empty initially"
        assert scanner.providers == {}, "Providers should be empty initially"

    def test_scanner_logging_setup(self, scanner):
        """Test that logging is properly set up"""
        # Arrange & Act
        logger = scanner.logger

        # Assert
        assert logger is not None, "Logger should be initialized"
        assert logger.name == "dnsping.scanner", "Logger should have correct name"

    @pytest.mark.asyncio
    async def test_load_dns_servers(self, temp_dns_file):
        """Test loading DNS servers from file"""
        # Arrange
        config = ScanConfig(dns_file=temp_dns_file, max_servers=2, ping_count=1, timeout=0.5)
        scanner = DNSLatencyScanner(config)

        # Act
        servers = await scanner.load_dns_servers()

        # Assert
        assert len(servers) == 2, "Should load 2 servers"
        assert "8.8.8.8" in servers, "Should include 8.8.8.8"
        assert "1.1.1.1" in servers, "Should include 1.1.1.1"
        assert scanner.providers["8.8.8.8"] == "Test Provider", "Should map provider correctly"

    @pytest.mark.asyncio
    async def test_load_dns_servers_with_comments(self, tmp_path):
        """Test loading DNS servers with comments and empty lines"""
        # Arrange
        dns_file = tmp_path / "test_dns.txt"
        dns_file.write_text("# Provider 1\n8.8.8.8\n// Comment line\n\n# Provider 2\n1.1.1.1\n")
        config = ScanConfig(dns_file=dns_file, max_servers=2, ping_count=1, timeout=0.5)
        scanner = DNSLatencyScanner(config)

        # Act
        servers = await scanner.load_dns_servers()

        # Assert
        assert len(servers) == 2, "Should skip comments and empty lines"
        assert "8.8.8.8" in servers, "Should include first server"
        assert "1.1.1.1" in servers, "Should include second server"

    @pytest.mark.asyncio
    async def test_load_dns_servers_max_limit(self, tmp_path):
        """Test that max_servers limit is respected"""
        # Arrange
        dns_file = tmp_path / "test_dns.txt"
        dns_file.write_text("\n".join([f"8.8.8.{i}" for i in range(1, 11)]))
        config = ScanConfig(dns_file=dns_file, max_servers=5, ping_count=1, timeout=0.5)
        scanner = DNSLatencyScanner(config)

        # Act
        servers = await scanner.load_dns_servers()

        # Assert
        assert len(servers) == 5, "Should respect max_servers limit"

    @pytest.mark.asyncio
    async def test_load_dns_servers_file_not_found(self):
        """Test loading DNS servers when file doesn't exist"""
        # Arrange
        config = ScanConfig(dns_file=Path("nonexistent_file.txt"), max_servers=2, ping_count=1, timeout=0.5)
        scanner = DNSLatencyScanner(config)

        # Act & Assert
        with pytest.raises(Exception):  # Should raise ConfigurationError
            await scanner.load_dns_servers()

    def test_get_provider_name(self, scanner):
        """Test getting provider name for a server"""
        # Arrange
        scanner.providers["8.8.8.8"] = "Google"

        # Act
        provider = scanner.get_provider_name("8.8.8.8")

        # Assert
        assert provider == "Google", "Should return correct provider name"

    def test_get_provider_name_unknown(self, scanner):
        """Test getting provider name for unknown server"""
        # Arrange
        unknown_server = "192.168.1.1"

        # Act
        provider = scanner.get_provider_name(unknown_server)

        # Assert
        assert provider == "Unknown Provider", "Should return Unknown Provider for unknown server"

    def test_get_latency_color_excellent(self, scanner):
        """Test latency color for excellent latency"""
        # Arrange
        latency = 10.0  # < 20ms

        # Act
        color = scanner._get_latency_color(latency)

        # Assert
        from dnsping.scanner import Color

        assert color == Color.GREEN.value, "Excellent latency should be green"

    def test_get_latency_color_good(self, scanner):
        """Test latency color for good latency"""
        # Arrange
        latency = 30.0  # 20-50ms

        # Act
        color = scanner._get_latency_color(latency)

        # Assert
        from dnsping.scanner import Color

        assert color == Color.YELLOW.value, "Good latency should be yellow"

    def test_get_latency_color_fair(self, scanner):
        """Test latency color for fair latency"""
        # Arrange
        latency = 75.0  # 50-100ms

        # Act
        color = scanner._get_latency_color(latency)

        # Assert
        from dnsping.scanner import Color

        assert color == Color.ORANGE.value, "Fair latency should be orange"

    def test_get_latency_color_poor(self, scanner):
        """Test latency color for poor latency"""
        # Arrange
        latency = 250.0  # > 200ms

        # Act
        color = scanner._get_latency_color(latency)

        # Assert
        from dnsping.scanner import Color

        assert color == Color.RED.value, "Poor latency should be red"

    def test_create_progress_bar(self, scanner):
        """Test progress bar creation"""
        # Arrange
        current = 5
        total = 10

        # Act
        bar = scanner._create_progress_bar(current, total)

        # Assert
        assert "50.0%" in bar, "Should show correct percentage"
        assert "5/10" in bar, "Should show current/total"

    def test_create_progress_bar_zero_total(self, scanner):
        """Test progress bar with zero total"""
        # Arrange
        current = 0
        total = 0

        # Act
        bar = scanner._create_progress_bar(current, total)

        # Assert
        assert "0.0%" in bar, "Should handle zero total"
        assert "0/0" in bar, "Should show 0/0"

    def test_create_latency_bar(self, scanner):
        """Test latency bar creation"""
        # Arrange
        latency = 50.0

        # Act
        bar = scanner._create_latency_bar(latency)

        # Assert
        assert len(bar) > 0, "Should create a bar"
        assert "█" in bar or "#" in bar, "Should contain filled character"

    def test_create_latency_bar_infinity(self, scanner):
        """Test latency bar for failed measurement"""
        # Arrange
        latency = float("inf")

        # Act
        bar = scanner._create_latency_bar(latency)

        # Assert
        assert "[FAIL]" in bar or "❌" in bar, "Should show failure indicator"

    def test_get_status_icon(self, scanner):
        """Test status icon generation"""
        # Arrange
        latencies = [
            (10.0, "[EXC]"),  # Excellent
            (30.0, "[GOOD]"),  # Good
            (75.0, "[FAIR]"),  # Fair
            (250.0, "[POOR]"),  # Poor
            (float("inf"), "[FAIL]"),  # Failed
        ]

        # Act & Assert
        for latency, expected_indicator in latencies:
            icon = scanner._get_status_icon(latency)
            assert expected_indicator in icon, f"Latency {latency} should show {expected_indicator}"
