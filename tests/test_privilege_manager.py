"""
Tests for PrivilegeManager class using AAA pattern
"""

import os
import subprocess
from unittest.mock import MagicMock, Mock, patch

import pytest

from dnsping.scanner import PrivilegeManager


class TestPrivilegeManager:
    """Test PrivilegeManager functionality with AAA pattern"""

    def setup_method(self):
        """Clear caches before each test"""
        # Arrange
        PrivilegeManager.clear_cache()

    def test_is_windows_caching(self):
        """Test that Windows detection is cached"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        result1 = PrivilegeManager._is_windows()
        result2 = PrivilegeManager._is_windows()

        # Assert
        assert result1 == result2, "Windows detection should be cached"
        assert isinstance(result1, bool), "Result should be boolean"

    def test_is_windows_detection(self):
        """Test Windows platform detection"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch("os.name", "nt"):
            result = PrivilegeManager._is_windows()

        # Assert
        assert result == True, "Should detect Windows when os.name is 'nt'"

    def test_is_windows_non_windows(self):
        """Test non-Windows platform detection"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch("os.name", "posix"):
            result = PrivilegeManager._is_windows()

        # Assert
        assert result == False, "Should detect non-Windows when os.name is not 'nt'"

    def test_is_admin_windows_success(self):
        """Test admin detection on Windows when admin"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "_is_windows", return_value=True):
            with patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=1):
                result = PrivilegeManager.is_admin()

        # Assert
        assert result == True, "Should detect admin privileges on Windows"

    def test_is_admin_windows_failure(self):
        """Test admin detection on Windows when not admin"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "_is_windows", return_value=True):
            with patch("ctypes.windll.shell32.IsUserAnAdmin", return_value=0):
                result = PrivilegeManager.is_admin()

        # Assert
        assert result == False, "Should detect non-admin on Windows"

    @pytest.mark.skipif(os.name == "nt", reason="Unix-specific test")
    def test_is_admin_unix_success(self):
        """Test admin detection on Unix when root"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "_is_windows", return_value=False):
            with patch("os.geteuid", return_value=0):
                result = PrivilegeManager.is_admin()

        # Assert
        assert result == True, "Should detect root privileges on Unix"

    @pytest.mark.skipif(os.name == "nt", reason="Unix-specific test")
    def test_is_admin_unix_failure(self):
        """Test admin detection on Unix when not root"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "_is_windows", return_value=False):
            with patch("os.geteuid", return_value=1000):
                result = PrivilegeManager.is_admin()

        # Assert
        assert result == False, "Should detect non-root on Unix"

    @pytest.mark.skipif(os.name == "nt", reason="Unix-specific test")
    def test_is_admin_caching(self):
        """Test that admin status is cached"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "_is_windows", return_value=False):
            with patch("os.geteuid", return_value=0):
                result1 = PrivilegeManager.is_admin()
                result2 = PrivilegeManager.is_admin()

        # Assert
        assert result1 == result2 == True, "Admin status should be cached"

    def test_is_admin_exception_handling(self):
        """Test admin detection handles exceptions gracefully"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "_is_windows", return_value=True):
            with patch("ctypes.windll.shell32.IsUserAnAdmin", side_effect=AttributeError("No attribute")):
                result = PrivilegeManager.is_admin()

        # Assert
        assert result == False, "Should return False on exception"

    def test_is_sudo_available_with_sudo(self):
        """Test sudo availability when sudo exists"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch("shutil.which", return_value="/usr/bin/sudo"):
            result = PrivilegeManager._is_sudo_available()

        # Assert
        assert result == True, "Should detect sudo when available"

    def test_is_sudo_available_without_sudo(self):
        """Test sudo availability when sudo doesn't exist"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch("shutil.which", return_value=None):
            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 1
                mock_run.return_value = mock_result
                result = PrivilegeManager._is_sudo_available()

        # Assert
        assert result == False, "Should detect no sudo when unavailable"

    def test_is_sudo_available_fallback(self):
        """Test sudo availability fallback method"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch("shutil.which", side_effect=OSError("Error")):
            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result
                result = PrivilegeManager._is_sudo_available()

        # Assert
        assert result == True, "Should use fallback method when shutil.which fails"

    def test_validate_arguments_safe_args(self):
        """Test argument validation with safe arguments"""
        # Arrange
        safe_args = ["-p", "4", "-m", "10", "dns_servers.txt"]

        # Act
        result = PrivilegeManager._validate_arguments(safe_args)

        # Assert
        assert len(result) > 0, "Should accept safe arguments"
        assert "-p" in result or "dns_servers.txt" in result, "Should preserve valid arguments"

    def test_validate_arguments_dangerous_args(self):
        """Test argument validation filters dangerous patterns"""
        # Arrange
        dangerous_args = ["-p", "4", "&", "rm", "-rf", "/", "|", "cat", "/etc/passwd"]

        # Act
        result = PrivilegeManager._validate_arguments(dangerous_args)

        # Assert
        assert "&" not in result, "Should filter shell operators"
        assert "|" not in result, "Should filter pipe operators"
        assert "rm" not in result or "-rf" not in result, "Should filter dangerous commands"

    def test_validate_arguments_numeric_validation(self):
        """Test argument validation validates numeric arguments"""
        # Arrange
        args_with_numeric = ["-p", "4", "-t", "1.5", "-m", "50"]

        # Act
        result = PrivilegeManager._validate_arguments(args_with_numeric)

        # Assert
        # Should preserve numeric arguments after flags
        assert len(result) >= 3, "Should preserve numeric arguments"

    def test_clear_cache(self):
        """Test that cache clearing works"""
        # Arrange
        PrivilegeManager._is_admin_cache = True
        PrivilegeManager._is_windows_cache = True
        PrivilegeManager._sudo_available_cache = True

        # Act
        PrivilegeManager.clear_cache()

        # Assert
        assert PrivilegeManager._is_admin_cache is None, "Admin cache should be cleared"
        assert PrivilegeManager._is_windows_cache is None, "Windows cache should be cleared"
        assert PrivilegeManager._sudo_available_cache is None, "Sudo cache should be cleared"

    def test_run_elevated_command_when_admin(self):
        """Test running command when already admin"""
        # Arrange
        command = ["echo", "test"]
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = ""

        # Act
        with patch.object(PrivilegeManager, "is_admin", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                success, message = PrivilegeManager.run_elevated_command(command, timeout=5)

        # Assert
        assert success == True, "Should succeed when already admin"
        mock_run.assert_called_once()

    def test_run_elevated_command_timeout(self):
        """Test elevated command timeout handling"""
        # Arrange
        command = ["sleep", "10"]

        # Act
        with patch.object(PrivilegeManager, "is_admin", return_value=True):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sleep", 5)):
                success, message = PrivilegeManager.run_elevated_command(command, timeout=5)

        # Assert
        assert success == False, "Should fail on timeout"
        assert "timed out" in message.lower() or "timeout" in message.lower(), "Message should mention timeout"

    def test_flush_dns_cache_windows(self):
        """Test DNS cache flushing on Windows"""
        # Arrange
        command = ["ipconfig", "/flushdns"]

        # Act
        with patch.object(PrivilegeManager, "_is_windows", return_value=True):
            with patch.object(PrivilegeManager, "run_elevated_command", return_value=(True, "Success")):
                success, message = PrivilegeManager.flush_dns_cache()

        # Assert
        assert success == True, "Should succeed on Windows"
        assert "Windows" in message, "Message should mention Windows"

    def test_flush_dns_cache_unix_success(self):
        """Test DNS cache flushing on Unix with success"""
        # Arrange
        commands_to_try = [
            (["systemd-resolve", "--flush-caches"], "DNS cache flushed (systemd-resolve)"),
        ]

        # Act
        with patch.object(PrivilegeManager, "_is_windows", return_value=False):
            with patch("shutil.which", return_value="/usr/bin/systemd-resolve"):
                with patch.object(PrivilegeManager, "run_elevated_command", return_value=(True, "Success")):
                    success, message = PrivilegeManager.flush_dns_cache()

        # Assert
        assert success == True, "Should succeed on Unix"

    def test_flush_dns_cache_unix_fallback(self):
        """Test DNS cache flushing fallback without elevation"""
        # Arrange
        mock_result = Mock()
        mock_result.returncode = 0

        # Act
        with patch.object(PrivilegeManager, "_is_windows", return_value=False):
            with patch("shutil.which", return_value=None):
                with patch("subprocess.run", return_value=mock_result):
                    success, message = PrivilegeManager.flush_dns_cache()

        # Assert
        # May succeed or fail depending on system, but should not crash
        assert isinstance(success, bool), "Should return boolean result"
