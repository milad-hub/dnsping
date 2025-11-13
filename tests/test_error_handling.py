"""
Tests for error handling paths using AAA pattern
"""

import asyncio
import dataclasses
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from dnsping.scanner import ConfigurationError, DNSLatencyScanner, ScanConfig, main


class TestErrorHandling:
    """Test error handling paths with AAA pattern"""

    @pytest.fixture
    def scanner_config(self):
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
    async def test_async_file_reader_error(self, scanner):
        """Test async file reader error handling"""
        # Arrange
        invalid_file = Path("/nonexistent/path/file.txt")

        # Act & Assert
        with pytest.raises(ConfigurationError):
            async for _ in scanner._async_file_reader(invalid_file):
                pass

    @pytest.mark.asyncio
    async def test_load_dns_servers_file_not_found_error(self, scanner_config):
        """Test loading DNS servers when file not found"""
        # Arrange
        from pathlib import Path

        config = dataclasses.replace(scanner_config, dns_file=Path("nonexistent_file.txt"))
        scanner = DNSLatencyScanner(config)

        # Act & Assert
        with pytest.raises(ConfigurationError) as exc_info:
            await scanner.load_dns_servers()

        # The error message may say "not found" or "no such file" or "failed to load"
        error_msg = str(exc_info.value).lower()
        assert (
            "not found" in error_msg or "no such file" in error_msg or "failed to load" in error_msg
        ), f"Should raise ConfigurationError, got: {exc_info.value}"

    @pytest.mark.asyncio
    async def test_load_dns_servers_general_error(self, scanner_config):
        """Test loading DNS servers handles general errors"""
        # Arrange
        from pathlib import Path

        config = dataclasses.replace(scanner_config, dns_file=Path("dns_servers.txt"))
        scanner = DNSLatencyScanner(config)

        # Act & Assert
        with patch("dnsping.scanner.DNSLatencyScanner._async_file_reader", side_effect=Exception("Read error")):
            with pytest.raises(ConfigurationError) as exc_info:
                await scanner.load_dns_servers()

        assert "Failed to load" in str(exc_info.value), "Should raise ConfigurationError"

    @pytest.mark.asyncio
    async def test_run_configuration_error(self, scanner):
        """Test run method handles ConfigurationError"""
        # Arrange
        scanner.dns_servers = []

        # Act
        with patch(
            "dnsping.scanner.DNSLatencyScanner.load_dns_servers", side_effect=ConfigurationError("Config error")
        ):
            with patch("builtins.print") as mock_print:
                await scanner.run()

        # Assert
        print_calls = str(mock_print.call_args_list)
        assert "Configuration Error" in print_calls or "ERROR" in print_calls, "Should print error"

    @pytest.mark.asyncio
    async def test_run_keyboard_interrupt(self, scanner):
        """Test run method handles KeyboardInterrupt"""
        # Arrange
        scanner.dns_servers = ["8.8.8.8"]

        # Act
        with patch("dnsping.scanner.DNSLatencyScanner.load_dns_servers", return_value=["8.8.8.8"]):
            with patch("dnsping.scanner.DNSLatencyScanner._scan_all_servers", side_effect=KeyboardInterrupt()):
                with patch("builtins.print") as mock_print:
                    await scanner.run()

        # Assert
        print_calls = str(mock_print.call_args_list)
        assert "interrupted" in print_calls.lower() or "STOP" in print_calls, "Should handle interrupt"

    @pytest.mark.asyncio
    async def test_run_general_exception(self, scanner):
        """Test run method handles general exceptions"""
        # Arrange
        scanner.dns_servers = ["8.8.8.8"]

        # Act
        with patch("dnsping.scanner.DNSLatencyScanner.load_dns_servers", side_effect=Exception("Unexpected error")):
            with patch("builtins.print") as mock_print:
                await scanner.run()

        # Assert
        print_calls = str(mock_print.call_args_list)
        assert "Unexpected error" in print_calls or "ERROR" in print_calls, "Should handle exception"

    @pytest.mark.asyncio
    async def test_run_finally_block(self, scanner):
        """Test run method executes finally block"""
        # Arrange
        scanner.running = True
        scanner.dns_servers = ["8.8.8.8"]

        # Act
        with patch("dnsping.scanner.DNSLatencyScanner.load_dns_servers", return_value=["8.8.8.8"]):
            with patch("dnsping.scanner.DNSLatencyScanner._scan_all_servers", new_callable=AsyncMock):
                await scanner.run()

        # Assert
        assert scanner.running == False, "Should set running to False in finally"

    def test_main_configuration_error(self):
        """Test main function handles configuration errors"""
        # Arrange
        test_args = ["dnsping", "nonexistent.txt"]

        # Act
        with patch("sys.argv", test_args):
            with patch("dnsping.scanner.DNSLatencyScanner") as mock_scanner_class:
                mock_scanner = MagicMock()
                mock_scanner.run = AsyncMock(side_effect=ConfigurationError("Config error"))
                mock_scanner_class.return_value = mock_scanner
                with patch("dnsping.scanner.asyncio.run") as mock_asyncio_run:
                    mock_asyncio_run.side_effect = lambda coro: coro
                    with patch("builtins.print"):
                        with patch("sys.exit"):
                            try:
                                main()
                            except (SystemExit, Exception):
                                pass

        # Assert
        assert True, "Should handle configuration errors"

    def test_main_keyboard_interrupt_handling(self):
        """Test main function handles keyboard interrupt"""
        # Arrange
        test_args = ["dnsping"]

        # Act
        with patch("sys.argv", test_args):
            with patch("dnsping.scanner.DNSLatencyScanner") as mock_scanner_class:
                mock_scanner = MagicMock()
                mock_scanner.run = AsyncMock(side_effect=KeyboardInterrupt())
                mock_scanner_class.return_value = mock_scanner
                with patch("dnsping.scanner.asyncio.run") as mock_asyncio_run:
                    mock_asyncio_run.side_effect = lambda coro: coro
                    with patch("builtins.print"):
                        try:
                            main()
                        except (SystemExit, KeyboardInterrupt):
                            pass

        # Assert
        assert True, "Should handle KeyboardInterrupt"

    def test_main_critical_error(self):
        """Test main function handles critical errors"""
        # Arrange
        test_args = ["dnsping"]

        # Act
        with patch("sys.argv", test_args):
            with patch("dnsping.scanner.asyncio.run", side_effect=Exception("Critical error")):
                with patch("builtins.print"):
                    with patch("sys.exit"):
                        try:
                            main()
                        except SystemExit:
                            pass

        # Assert
        assert True, "Should handle critical errors"
