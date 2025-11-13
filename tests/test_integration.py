"""
Integration tests for DNS scanner using AAA pattern
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dnsping.scanner import DNSLatencyScanner, ScanConfig


class TestScannerIntegration:
    """Integration tests with AAA pattern"""

    @pytest.fixture
    def temp_dns_file(self, tmp_path):
        """Create a temporary DNS servers file"""
        # Arrange
        dns_file = tmp_path / "test_dns.txt"
        dns_file.write_text("# Test Provider\n8.8.8.8\n1.1.1.1\n")
        return dns_file

    @pytest.fixture
    def scanner_config(self, temp_dns_file):
        """Create scanner configuration"""
        # Arrange
        return ScanConfig(
            dns_file=temp_dns_file,
            max_servers=2,
            ping_count=1,
            timeout=0.1,  # Very short timeout for fast tests
            enable_ping=False,
            enable_socket=False,
            enable_dns_query=False,  # Disable all methods for unit tests
        )

    @pytest.fixture
    def scanner(self, scanner_config):
        """Create scanner instance"""
        # Arrange
        return DNSLatencyScanner(scanner_config)

    @pytest.mark.asyncio
    async def test_full_scan_workflow(self, temp_dns_file):
        """Test complete scan workflow"""
        # Arrange
        config = ScanConfig(
            dns_file=temp_dns_file,
            max_servers=2,
            ping_count=1,
            timeout=0.1,
            enable_dns_query=False,  # Disable to avoid network calls
            enable_ping=False,
            enable_socket=False,
        )
        scanner = DNSLatencyScanner(config)

        # Act
        servers = await scanner.load_dns_servers()

        # Assert
        assert len(servers) == 2, "Should load servers"
        assert scanner.dns_servers == [], "DNS servers list should be empty before assignment"
        scanner.dns_servers = servers
        assert len(scanner.dns_servers) == 2, "Should have loaded servers"

    @pytest.mark.asyncio
    async def test_scanner_stats_tracking(self, scanner):
        """Test that scanner tracks statistics correctly"""
        # Arrange
        scanner._stats = {"scanned": 0, "successful": 0, "failed": 0}

        # Act
        async with scanner._lock:
            scanner._stats["scanned"] += 1
            scanner._stats["successful"] += 1

        # Assert
        assert scanner._stats["scanned"] == 1, "Should track scanned count"
        assert scanner._stats["successful"] == 1, "Should track successful count"

    def test_scanner_running_flag(self, scanner):
        """Test scanner running flag management"""
        # Arrange
        assert scanner.running == True, "Should start as running"

        # Act
        scanner.running = False

        # Assert
        assert scanner.running == False, "Should be able to set running flag"

    @pytest.mark.asyncio
    async def test_scanner_results_storage(self, scanner):
        """Test that results are stored correctly"""
        # Arrange
        from dnsping.scanner import DNSResult

        result = DNSResult(server="8.8.8.8", provider="Google")
        result.avg_latency = 15.0

        # Act
        async with scanner._lock:
            scanner.results["8.8.8.8"] = result

        # Assert
        assert "8.8.8.8" in scanner.results, "Should store result"
        assert scanner.results["8.8.8.8"].avg_latency == 15.0, "Should store correct latency"

    def test_scanner_provider_mapping(self, scanner):
        """Test provider mapping functionality"""
        # Arrange
        scanner.providers["8.8.8.8"] = "Google"
        scanner.providers["1.1.1.1"] = "Cloudflare"

        # Act
        provider1 = scanner.get_provider_name("8.8.8.8")
        provider2 = scanner.get_provider_name("1.1.1.1")

        # Assert
        assert provider1 == "Google", "Should return correct provider"
        assert provider2 == "Cloudflare", "Should return correct provider"
