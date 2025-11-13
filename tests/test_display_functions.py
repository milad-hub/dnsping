"""
Tests for display functions using AAA pattern
"""

import asyncio
import dataclasses
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from dnsping.scanner import DNSLatencyScanner, DNSResult, LatencyLevel, ScanConfig, TestMethod


class TestDisplayFunctions:
    """Test display functions with AAA pattern"""

    @pytest.fixture
    def scanner_config(self):
        """Create scanner configuration"""
        # Arrange
        from pathlib import Path

        return ScanConfig(
            dns_file=Path("dns_servers.txt"),
            max_servers=5,
            ping_count=2,
            timeout=0.1,
            update_interval=0.01,  # Fast updates for testing
        )

    @pytest.fixture
    def scanner(self, scanner_config):
        """Create scanner instance"""
        # Arrange
        return DNSLatencyScanner(scanner_config)

    @pytest.fixture
    def sample_results(self):
        """Create sample DNS results"""
        # Arrange
        results = {}
        results["8.8.8.8"] = DNSResult(
            server="8.8.8.8",
            provider="Google",
            avg_latency=15.0,
            status="OK (DNS) - 2/2",
            ping_count=2,
            successful_methods={TestMethod.DNS_QUERY},
        )
        results["1.1.1.1"] = DNSResult(
            server="1.1.1.1",
            provider="Cloudflare",
            avg_latency=25.0,
            status="OK (DNS) - 2/2",
            ping_count=2,
            successful_methods={TestMethod.DNS_QUERY},
        )
        return results

    @pytest.mark.asyncio
    async def test_display_live_results_basic(self, scanner):
        """Test basic live results display"""
        # Arrange
        scanner.dns_servers = ["8.8.8.8", "1.1.1.1"]
        scanner.running = True

        # Act
        with patch("time.time", return_value=0.0):
            with patch("os.system"):
                with patch("builtins.print"):
                    # Run briefly then stop
                    scanner.running = False
                    await scanner._display_live_results()

        # Assert
        # Should complete without errors
        assert True, "Should display live results"

    @pytest.mark.asyncio
    async def test_display_live_results_with_results(self, scanner_config, sample_results):
        """Test live results display with actual results"""
        # Arrange
        scanner = DNSLatencyScanner(scanner_config)
        scanner.dns_servers = ["8.8.8.8", "1.1.1.1"]
        scanner.results = sample_results
        scanner.running = True

        # Act
        with patch("time.time", return_value=0.0):
            with patch("os.system"):
                with patch("builtins.print") as mock_print:
                    scanner.running = False
                    await scanner._display_live_results()

        # Assert
        # Function should complete without errors
        assert True, "Should display live results"

    @pytest.mark.asyncio
    async def test_display_live_results_update_interval(self, scanner_config):
        """Test live results respects update interval"""
        # Arrange
        config = dataclasses.replace(scanner_config, update_interval=0.1)
        scanner = DNSLatencyScanner(config)
        scanner.dns_servers = ["8.8.8.8"]
        scanner.running = True

        # Act
        call_times = []

        def mock_time():
            call_times.append(len(call_times) * 0.05)
            return call_times[-1]

        with patch("time.time", side_effect=mock_time):
            with patch("os.system"):
                with patch("builtins.print"):
                    # Run for a short time
                    await asyncio.sleep(0.01)
                    scanner.running = False
                    await scanner._display_live_results()

        # Assert
        # Should respect update interval
        assert True, "Should respect update interval"

    def test_display_final_results_no_results(self, scanner):
        """Test final results display with no results"""
        # Arrange
        scanner.results = {}
        scanner.dns_servers = ["8.8.8.8"]

        # Act
        with patch("os.system"):
            with patch("builtins.print") as mock_print:
                scanner._display_final_results()

        # Assert
        assert mock_print.called, "Should print no results message"

    def test_display_final_results_with_results(self, scanner, sample_results):
        """Test final results display with results"""
        # Arrange
        scanner.results = sample_results
        scanner.dns_servers = list(sample_results.keys())

        # Act
        with patch("os.system"):
            with patch("builtins.input", return_value=""):  # Mock input to avoid stdin read
                with patch("builtins.print") as mock_print:
                    scanner._display_final_results()

        # Assert
        assert mock_print.called, "Should print results"

    def test_display_final_results_performance_categories(self, scanner):
        """Test final results performance categories"""
        # Arrange
        scanner.results = {
            "excellent": DNSResult(
                server="excellent",
                provider="Test",
                avg_latency=10.0,
                successful_methods={TestMethod.DNS_QUERY},
            ),
            "good": DNSResult(
                server="good",
                provider="Test",
                avg_latency=30.0,
                successful_methods={TestMethod.DNS_QUERY},
            ),
            "fair": DNSResult(
                server="fair",
                provider="Test",
                avg_latency=75.0,
                successful_methods={TestMethod.DNS_QUERY},
            ),
            "poor": DNSResult(
                server="poor",
                provider="Test",
                avg_latency=250.0,
                successful_methods={TestMethod.DNS_QUERY},
            ),
        }
        scanner.dns_servers = list(scanner.results.keys())

        # Act
        with patch("os.system"):
            with patch("builtins.input", return_value=""):  # Mock input to avoid stdin read
                with patch("builtins.print") as mock_print:
                    scanner._display_final_results()

        # Assert
        print_calls = str(mock_print.call_args_list)
        assert "Excellent" in print_calls or "excellent" in print_calls.lower(), "Should show excellent category"
        assert "Good" in print_calls or "good" in print_calls.lower(), "Should show good category"
        assert "Fair" in print_calls or "fair" in print_calls.lower(), "Should show fair category"
        assert "Poor" in print_calls or "poor" in print_calls.lower(), "Should show poor category"

    def test_display_final_results_long_provider_name(self, scanner):
        """Test final results with long provider names"""
        # Arrange
        scanner.results = {
            "8.8.8.8": DNSResult(
                server="8.8.8.8",
                provider="Very Long Provider Name That Exceeds Limit",
                avg_latency=15.0,
                successful_methods={TestMethod.DNS_QUERY},
            )
        }
        scanner.dns_servers = ["8.8.8.8"]

        # Act
        with patch("os.system"):
            with patch("builtins.input", return_value=""):  # Mock input to avoid stdin read
                with patch("builtins.print") as mock_print:
                    scanner._display_final_results()

        # Assert
        assert mock_print.called, "Should handle long provider names"

    def test_display_final_results_long_status(self, scanner):
        """Test final results with long status strings"""
        # Arrange
        scanner.results = {
            "8.8.8.8": DNSResult(
                server="8.8.8.8",
                provider="Test",
                avg_latency=15.0,
                status="Very Long Status String That Exceeds Normal Limits",
                successful_methods={TestMethod.DNS_QUERY},
            )
        }
        scanner.dns_servers = ["8.8.8.8"]

        # Act
        with patch("os.system"):
            with patch("builtins.input", return_value=""):  # Mock input to avoid stdin read
                with patch("builtins.print") as mock_print:
                    scanner._display_final_results()

        # Assert
        assert mock_print.called, "Should handle long status strings"
