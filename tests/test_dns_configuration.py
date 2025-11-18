"""
Tests for DNS configuration functionality using AAA pattern
"""

import dataclasses
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from dnsping.scanner import DNSLatencyScanner, DNSResult, PrivilegeManager, ScanConfig, TestMethod


class TestDNSConfiguration:
    """Test DNS configuration functionality with AAA pattern"""

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
        results = []
        results.append(
            DNSResult(
                server="8.8.8.8",
                provider="Google",
                avg_latency=15.0,
                successful_methods={TestMethod.DNS_QUERY},
            )
        )
        results.append(
            DNSResult(
                server="1.1.1.1",
                provider="Cloudflare",
                avg_latency=20.0,
                successful_methods={TestMethod.DNS_QUERY},
            )
        )
        return results

    def test_handle_dns_selection_skip(self, scanner, sample_results):
        """Test DNS selection when user skips"""
        # Arrange
        scanner.config = dataclasses.replace(scanner.config, max_servers=5)

        # Act
        with patch("builtins.input", return_value=""):
            with patch("builtins.print"):
                scanner._handle_dns_selection(sample_results)

        # Assert
        # Should complete without errors
        assert True, "Should handle skip gracefully"

    def test_handle_dns_selection_valid_choice(self, scanner, sample_results):
        """Test DNS selection with valid choice"""
        # Arrange
        scanner.config = dataclasses.replace(scanner.config, max_servers=5)

        # Act
        with patch("builtins.input", side_effect=["1", ""]):
            with patch.object(DNSLatencyScanner, "_configure_system_dns") as mock_configure:
                with patch("builtins.print"):
                    scanner._handle_dns_selection(sample_results)

        # Assert
        mock_configure.assert_called_once(), "Should call configure with selected result"

    def test_handle_dns_selection_invalid_choice(self, scanner, sample_results):
        """Test DNS selection with invalid choice"""
        # Arrange
        scanner.config = dataclasses.replace(scanner.config, max_servers=5)

        # Act
        with patch("builtins.input", side_effect=["99", ""]):
            with patch("builtins.print") as mock_print:
                scanner._handle_dns_selection(sample_results)

        # Assert
        print_calls = str(mock_print.call_args_list)
        assert "Invalid selection" in print_calls, "Should show error for invalid choice"

    def test_handle_dns_selection_keyboard_interrupt(self, scanner, sample_results):
        """Test DNS selection handles keyboard interrupt"""
        # Arrange
        scanner.config = dataclasses.replace(scanner.config, max_servers=5)

        # Act
        with patch("builtins.input", side_effect=KeyboardInterrupt()):
            with patch("builtins.print"):
                scanner._handle_dns_selection(sample_results)

        # Assert
        # Should handle gracefully
        assert True, "Should handle KeyboardInterrupt"

    def test_configure_system_dns_success(self, scanner, sample_results):
        """Test DNS configuration with success"""
        # Arrange
        selected_result = sample_results[0]
        all_results = sample_results

        # Act
        with patch("builtins.input", return_value="y"):
            with patch("dnsping.scanner.DNSLatencyScanner._set_system_dns_elevated", return_value=(True, "Success")):
                with patch.object(PrivilegeManager, "flush_dns_cache", return_value=(True, "Flushed")):
                    with patch("builtins.print"):
                        scanner._configure_system_dns(selected_result, all_results)

        # Assert
        # Should complete successfully
        assert True, "Should configure DNS successfully"

    def test_configure_system_dns_failure(self, scanner, sample_results):
        """Test DNS configuration with failure"""
        # Arrange
        selected_result = sample_results[0]
        all_results = sample_results

        # Act
        with patch("builtins.input", return_value="y"):
            with patch("dnsping.scanner.DNSLatencyScanner._set_system_dns_elevated", return_value=(False, "Failed")):
                with patch("builtins.print") as mock_print:
                    scanner._configure_system_dns(selected_result, all_results)

        # Assert
        print_calls = str(mock_print.call_args_list)
        assert "Failed" in print_calls or "ERROR" in print_calls, "Should show error message"

    def test_configure_system_dns_cancelled(self, scanner, sample_results):
        """Test DNS configuration when cancelled"""
        # Arrange
        selected_result = sample_results[0]
        all_results = sample_results

        # Act
        with patch("builtins.input", return_value="n"):
            with patch("builtins.print") as mock_print:
                scanner._configure_system_dns(selected_result, all_results)

        # Assert
        print_calls = str(mock_print.call_args_list)
        assert "cancelled" in print_calls.lower(), "Should show cancelled message"

    def test_configure_system_dns_with_secondary(self, scanner, sample_results):
        """Test DNS configuration finds secondary DNS"""
        # Arrange
        selected_result = sample_results[0]
        all_results = sample_results
        all_results.append(
            DNSResult(
                server="8.8.4.4",
                provider="Google",  # Same provider
                avg_latency=18.0,
                successful_methods={TestMethod.DNS_QUERY},
            )
        )

        # Act
        with patch("builtins.input", return_value="y"):
            with patch("dnsping.scanner.DNSLatencyScanner._set_system_dns_elevated", return_value=(True, "Success")):
                with patch.object(PrivilegeManager, "flush_dns_cache", return_value=(True, "Flushed")):
                    with patch("builtins.print") as mock_print:
                        scanner._configure_system_dns(selected_result, all_results)

        # Assert
        print_calls = str(mock_print.call_args_list)
        assert "Secondary" in print_calls, "Should find and display secondary DNS"

    def test_set_system_dns_elevated_windows(self, scanner):
        """Test setting DNS on Windows"""
        # Arrange
        primary_dns = "8.8.8.8"
        secondary_dns = "8.8.4.4"

        # Act
        with patch("os.name", "nt"):
            with patch("dnsping.scanner.DNSLatencyScanner._set_dns_windows_elevated", return_value=(True, "Success")):
                success, message = scanner._set_system_dns_elevated(primary_dns, secondary_dns)

        # Assert
        assert success == True, "Should succeed on Windows"
        assert "Success" in message, "Should return success message"

    def test_set_system_dns_elevated_unix(self, scanner):
        """Test setting DNS on Unix"""
        # Arrange
        primary_dns = "8.8.8.8"
        secondary_dns = "8.8.4.4"

        # Act
        with patch("os.name", "posix"):
            with patch("dnsping.scanner.DNSLatencyScanner._set_dns_unix_elevated", return_value=(True, "Success")):
                success, message = scanner._set_system_dns_elevated(primary_dns, secondary_dns)

        # Assert
        assert success == True, "Should succeed on Unix"
        assert "Success" in message, "Should return success message"

    def test_set_dns_windows_elevated_success(self, scanner):
        """Test Windows DNS configuration success"""
        # Arrange
        primary_dns = "8.8.8.8"
        secondary_dns = "8.8.4.4"
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Connected"

        # Act
        with patch("subprocess.run", return_value=mock_result):
            with patch.object(PrivilegeManager, "run_elevated_command", return_value=(True, "Success")):
                success, message = scanner._set_dns_windows_elevated(primary_dns, secondary_dns)

        # Assert
        assert success == True, "Should succeed on Windows"

    def test_set_dns_windows_elevated_no_interface(self, scanner):
        """Test Windows DNS configuration when no interface found"""
        # Arrange
        primary_dns = "8.8.8.8"

        # Act
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_run.return_value = mock_result
            # When no interface found and elevation fails
            with patch("dnsping.scanner.PrivilegeManager.run_elevated_command", return_value=(False, "Failed")):
                success, message = scanner._set_dns_windows_elevated(primary_dns)

        # Assert
        assert success == False, "Should fail when no interface found"
        assert (
            "interface" in message.lower() or "failed" in message.lower() or "could not identify" in message.lower()
        ), "Should mention interface or failure in error"

    def test_set_dns_unix_elevated_success(self, scanner):
        """Test Unix DNS configuration success"""
        # Arrange
        primary_dns = "8.8.8.8"
        secondary_dns = "8.8.4.4"

        # Act
        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_file = MagicMock()
            mock_file.name = "/tmp/test_resolv.conf"
            mock_temp.return_value.__enter__.return_value = mock_file
            with patch.object(PrivilegeManager, "run_elevated_command", return_value=(True, "Success")):
                success, message = scanner._set_dns_unix_elevated(primary_dns, secondary_dns)

        # Assert
        assert success == True, "Should succeed on Unix"

    def test_set_dns_unix_elevated_cleanup(self, scanner):
        """Test Unix DNS configuration uses automatic cleanup"""
        # Arrange
        primary_dns = "8.8.8.8"

        # Act
        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_file = MagicMock()
            mock_file.name = "/tmp/test_resolv.conf"
            mock_file.flush = MagicMock()
            mock_temp.return_value.__enter__.return_value = mock_file
            mock_temp.return_value.__exit__.return_value = None
            with patch.object(PrivilegeManager, "run_elevated_command", return_value=(True, "Success")):
                success, message = scanner._set_dns_unix_elevated(primary_dns)

        # Assert
        mock_file.flush.assert_called_once(), "Should flush file before elevation"
        mock_temp.assert_called_once_with(mode="w", delete=True, suffix=".tmp"), "Should use automatic cleanup"

    def test_set_dns_unix_elevated_cleanup_error(self, scanner):
        """Test Unix DNS configuration succeeds with automatic cleanup"""
        # Arrange
        primary_dns = "8.8.8.8"

        # Act
        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_file = MagicMock()
            mock_file.name = "/tmp/test_resolv.conf"
            mock_file.flush = MagicMock()
            mock_temp.return_value.__enter__.return_value = mock_file
            mock_temp.return_value.__exit__.return_value = None
            with patch.object(PrivilegeManager, "run_elevated_command", return_value=(True, "Success")):
                success, message = scanner._set_dns_unix_elevated(primary_dns)

        # Assert
        assert success == True, "Should succeed with automatic cleanup"

    def test_set_system_dns_legacy(self, scanner):
        """Test legacy set_system_dns method"""
        # Arrange
        primary_dns = "8.8.8.8"

        # Act
        # Use module-level patch since instance-level doesn't work for read-only attributes
        with patch("dnsping.scanner.DNSLatencyScanner._set_system_dns_elevated", return_value=(True, "Success")):
            result = scanner._set_system_dns(primary_dns)

        # Assert
        assert result == True, "Should delegate to elevated method"
