"""
Tests for scan workflow and server scanning using AAA pattern
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from dnsping.scanner import DNSLatencyScanner, DNSResult, ScanConfig, TestMethod


class TestScanWorkflow:
    """Test scanning workflow with AAA pattern"""

    @pytest.fixture
    def scanner_config(self, tmp_path):
        """Create scanner configuration"""
        # Arrange
        from pathlib import Path

        dns_file = tmp_path / "test_dns.txt"
        dns_file.write_text("# Test\n8.8.8.8\n1.1.1.1\n")
        return ScanConfig(
            dns_file=dns_file,
            max_servers=2,
            ping_count=2,
            timeout=0.1,
            enable_dns_query=False,
            enable_socket=False,
            enable_ping=False,
        )

    @pytest.fixture
    def scanner(self, scanner_config):
        """Create scanner instance"""
        # Arrange
        return DNSLatencyScanner(scanner_config)

    @pytest.mark.asyncio
    async def test_scan_server_multiple_success(self, scanner):
        """Test scanning server multiple times with success"""
        # Arrange
        server = "8.8.8.8"
        scanner.dns_servers = [server]
        scanner.providers[server] = "Test Provider"
        semaphore = asyncio.Semaphore(1)

        # Act
        with patch(
            "dnsping.scanner.DNSLatencyScanner._measure_server_latency", return_value=(15.0, {TestMethod.DNS_QUERY})
        ):
            await scanner._scan_server_multiple(server, semaphore)

        # Assert
        assert server in scanner.results, "Should store result"
        assert scanner.results[server].avg_latency == 15.0, "Should calculate average latency"
        assert scanner._stats["successful"] == 1, "Should increment successful count"

    @pytest.mark.asyncio
    async def test_scan_server_multiple_failure(self, scanner):
        """Test scanning server when all attempts fail"""
        # Arrange
        server = "8.8.8.8"
        scanner.dns_servers = [server]
        scanner.providers[server] = "Test Provider"
        semaphore = asyncio.Semaphore(1)

        # Act
        with patch("dnsping.scanner.DNSLatencyScanner._measure_server_latency", return_value=(float("inf"), set())):
            await scanner._scan_server_multiple(server, semaphore)

        # Assert
        assert server in scanner.results, "Should store result even on failure"
        assert scanner.results[server].avg_latency == float("inf"), "Should have infinite latency"
        assert scanner._stats["failed"] == 1, "Should increment failed count"

    @pytest.mark.asyncio
    async def test_scan_server_multiple_partial_success(self, scanner):
        """Test scanning server with partial success"""
        # Arrange
        import dataclasses

        server = "8.8.8.8"
        scanner.config = dataclasses.replace(scanner.config, ping_count=3)
        scanner.dns_servers = [server]
        scanner.providers[server] = "Test Provider"
        semaphore = asyncio.Semaphore(1)

        # Act
        with patch(
            "dnsping.scanner.DNSLatencyScanner._measure_server_latency",
            side_effect=[
                (15.0, {TestMethod.DNS_QUERY}),
                (float("inf"), set()),
                (20.0, {TestMethod.DNS_QUERY}),
            ],
        ):
            await scanner._scan_server_multiple(server, semaphore)

        # Assert
        assert scanner.results[server].avg_latency == 17.5, "Should calculate average from successful attempts"
        assert scanner.results[server].ping_count == 2, "Should track successful attempts"

    @pytest.mark.asyncio
    async def test_scan_server_multiple_exception_handling(self, scanner):
        """Test scanning server handles exceptions gracefully"""
        # Arrange
        server = "8.8.8.8"
        scanner.dns_servers = [server]
        scanner.providers[server] = "Test Provider"
        semaphore = asyncio.Semaphore(1)

        # Act
        with patch("dnsping.scanner.DNSLatencyScanner._measure_server_latency", side_effect=Exception("Network error")):
            await scanner._scan_server_multiple(server, semaphore)

        # Assert
        assert scanner._stats["failed"] == 1, "Should increment failed count on exception"

    @pytest.mark.asyncio
    async def test_scan_all_servers(self, scanner):
        """Test scanning all servers"""
        # Arrange
        scanner.dns_servers = ["8.8.8.8", "1.1.1.1"]
        scanner.providers = {"8.8.8.8": "Google", "1.1.1.1": "Cloudflare"}

        # Act
        with patch("dnsping.scanner.DNSLatencyScanner._scan_server_multiple", new_callable=AsyncMock) as mock_scan:
            with patch(
                "dnsping.scanner.DNSLatencyScanner._display_live_results", new_callable=AsyncMock
            ) as mock_display:
                mock_display.side_effect = asyncio.CancelledError()
                await scanner._scan_all_servers()

        # Assert
        assert mock_scan.call_count == 2, "Should scan all servers"
        assert scanner.running == False, "Should set running to False"

    @pytest.mark.asyncio
    async def test_scan_all_servers_display_cancellation(self, scanner):
        """Test that display task is properly cancelled"""
        # Arrange
        scanner.dns_servers = ["8.8.8.8"]
        scanner.running = True

        # Act
        with patch("dnsping.scanner.DNSLatencyScanner._scan_server_multiple", new_callable=AsyncMock):
            with patch(
                "dnsping.scanner.DNSLatencyScanner._display_live_results", new_callable=AsyncMock
            ) as mock_display:
                mock_display.side_effect = asyncio.CancelledError()
                await scanner._scan_all_servers()

        # Assert
        assert scanner.running == False, "Should set running to False"

    @pytest.mark.asyncio
    async def test_scan_all_servers_with_exceptions(self, scanner):
        """Test scanning all servers handles exceptions"""
        # Arrange
        scanner.dns_servers = ["8.8.8.8", "1.1.1.1"]

        # Act
        with patch("dnsping.scanner.DNSLatencyScanner._scan_server_multiple", side_effect=Exception("Error")):
            with patch(
                "dnsping.scanner.DNSLatencyScanner._display_live_results", new_callable=AsyncMock
            ) as mock_display:
                mock_display.side_effect = asyncio.CancelledError()
                await scanner._scan_all_servers()

        # Assert
        assert scanner.running == False, "Should handle exceptions gracefully"
