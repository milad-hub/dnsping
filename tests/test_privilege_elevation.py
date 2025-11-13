"""
Tests for privilege elevation methods using AAA pattern
"""

import os
import subprocess
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

from dnsping.scanner import PrivilegeManager


class TestPrivilegeElevation:
    """Test privilege elevation methods with AAA pattern"""

    def setup_method(self):
        """Clear caches before each test"""
        # Arrange
        PrivilegeManager.clear_cache()

    def test_create_elevated_command_windows(self):
        """Test Windows elevated command creation"""
        # Arrange
        original_args = ["dnsping", "-m", "5", "-p", "1"]

        # Act
        with patch("sys.executable", "python.exe"):
            executable, params = PrivilegeManager._create_elevated_command_windows(original_args)

        # Assert
        assert executable == "python.exe", "Should return Python executable"
        assert "--elevated" in params, "Should add elevated flag"

    def test_create_elevated_command_windows_filters_dangerous(self):
        """Test Windows command creation filters dangerous args"""
        # Arrange
        dangerous_args = ["dnsping", "&", "rm", "-rf", "/"]

        # Act
        with patch("sys.executable", "python.exe"):
            executable, params = PrivilegeManager._create_elevated_command_windows(dangerous_args)

        # Assert
        assert "&" not in params, "Should filter dangerous characters"
        assert "rm" not in params, "Should filter dangerous commands"

    def test_create_elevated_command_unix(self):
        """Test Unix elevated command creation"""
        # Arrange
        original_args = ["dnsping", "-m", "5", "-p", "1"]

        # Act
        with patch("sys.executable", "/usr/bin/python3"):
            cmd = PrivilegeManager._create_elevated_command_unix(original_args)

        # Assert
        assert cmd[0] == "sudo", "Should start with sudo"
        assert "--elevated" in cmd, "Should add elevated flag"

    def test_request_admin_privileges_when_already_admin(self):
        """Test requesting admin privileges when already admin"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "is_admin", return_value=True):
            result = PrivilegeManager.request_admin_privileges()

        # Assert
        assert result == True, "Should return True when already admin"

    def test_request_admin_privileges_windows(self):
        """Test requesting admin privileges on Windows"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "is_admin", return_value=False):
            with patch.object(PrivilegeManager, "_is_windows", return_value=True):
                with patch.object(PrivilegeManager, "_request_admin_windows", return_value=True):
                    result = PrivilegeManager.request_admin_privileges()

        # Assert
        assert result == True, "Should request admin on Windows"

    def test_request_admin_privileges_unix(self):
        """Test requesting admin privileges on Unix"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "is_admin", return_value=False):
            with patch.object(PrivilegeManager, "_is_windows", return_value=False):
                with patch.object(PrivilegeManager, "_request_admin_unix", return_value=True):
                    result = PrivilegeManager.request_admin_privileges()

        # Assert
        assert result == True, "Should request admin on Unix"

    def test_request_admin_privileges_exception(self):
        """Test requesting admin privileges handles exceptions"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "is_admin", return_value=False):
            with patch.object(PrivilegeManager, "_is_windows", side_effect=Exception("Error")):
                result = PrivilegeManager.request_admin_privileges()

        # Assert
        assert result == False, "Should return False on exception"

    def test_request_admin_windows_success(self):
        """Test Windows admin request success"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch("sys.argv", ["dnsping", "-m", "5"]):
            with patch("sys.executable", "python.exe"):
                with patch("ctypes.windll.shell32.ShellExecuteW", return_value=33):  # > 32 = success
                    with patch("sys.exit") as mock_exit:
                        result = PrivilegeManager._request_admin_windows()

        # Assert
        mock_exit.assert_called_once(), "Should exit after elevation"

    def test_request_admin_windows_failure(self):
        """Test Windows admin request failure"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch("sys.argv", ["dnsping"]):
            with patch("sys.executable", "python.exe"):
                with patch("ctypes.windll.shell32.ShellExecuteW", return_value=0):  # Failure
                    result = PrivilegeManager._request_admin_windows()

        # Assert
        assert result == False, "Should return False on failure"

    def test_request_admin_windows_exception(self):
        """Test Windows admin request handles exceptions"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch("sys.argv", ["dnsping"]):
            with patch("ctypes.windll.shell32.ShellExecuteW", side_effect=AttributeError("No attribute")):
                result = PrivilegeManager._request_admin_windows()

        # Assert
        assert result == False, "Should return False on exception"

    def test_request_admin_unix_success(self):
        """Test Unix admin request success"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "_is_sudo_available", return_value=True):
            with patch("sys.argv", ["dnsping"]):
                with patch("sys.executable", "/usr/bin/python3"):
                    with patch("subprocess.run") as mock_run:
                        mock_result = Mock()
                        mock_result.returncode = 0
                        mock_run.return_value = mock_result
                        with patch("sys.exit") as mock_exit:
                            result = PrivilegeManager._request_admin_unix()

        # Assert
        mock_exit.assert_called_once(), "Should exit after elevation"

    def test_request_admin_unix_no_sudo(self):
        """Test Unix admin request when sudo unavailable"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "_is_sudo_available", return_value=False):
            result = PrivilegeManager._request_admin_unix()

        # Assert
        assert result == False, "Should return False when sudo unavailable"

    def test_request_admin_unix_timeout(self):
        """Test Unix admin request timeout"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "_is_sudo_available", return_value=True):
            with patch("sys.argv", ["dnsping"]):
                with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sudo", 60)):
                    result = PrivilegeManager._request_admin_unix()

        # Assert
        assert result == False, "Should return False on timeout"

    def test_run_elevated_command_windows(self):
        """Test running elevated command on Windows"""
        # Arrange
        command = ["ipconfig", "/flushdns"]

        # Act
        with patch.object(PrivilegeManager, "_is_windows", return_value=True):
            with patch.object(PrivilegeManager, "_run_elevated_command_windows", return_value=(True, "Success")):
                success, message = PrivilegeManager.run_elevated_command(command)

        # Assert
        assert success == True, "Should succeed on Windows"

    def test_run_elevated_command_unix(self):
        """Test running elevated command on Unix"""
        # Arrange
        command = ["systemctl", "restart", "systemd-resolved"]

        # Act
        with patch.object(PrivilegeManager, "_is_windows", return_value=False):
            with patch.object(PrivilegeManager, "_run_elevated_command_unix", return_value=(True, "Success")):
                success, message = PrivilegeManager.run_elevated_command(command)

        # Assert
        assert success == True, "Should succeed on Unix"

    def test_run_elevated_command_windows_implementation(self):
        """Test Windows elevated command implementation"""
        # Arrange
        command = ["ipconfig", "/flushdns"]

        # Act
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            success, message = PrivilegeManager._run_elevated_command_windows(command, timeout=5)

        # Assert
        assert success == True, "Should execute PowerShell command"

    def test_run_elevated_command_windows_timeout(self):
        """Test Windows elevated command timeout"""
        # Arrange
        command = ["ipconfig", "/flushdns"]

        # Act
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("powershell", 5)):
            success, message = PrivilegeManager._run_elevated_command_windows(command, timeout=5)

        # Assert
        assert success == False, "Should fail on timeout"
        assert "timeout" in message.lower() or "timed out" in message.lower(), "Should mention timeout"

    def test_run_elevated_command_unix_implementation(self):
        """Test Unix elevated command implementation"""
        # Arrange
        command = ["systemctl", "restart", "systemd-resolved"]

        # Act
        with patch.object(PrivilegeManager, "_is_sudo_available", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "Success"
                mock_run.return_value = mock_result
                success, message = PrivilegeManager._run_elevated_command_unix(command, timeout=5)

        # Assert
        assert success == True, "Should execute sudo command"

    def test_run_elevated_command_unix_no_sudo(self):
        """Test Unix elevated command when sudo unavailable"""
        # Arrange
        command = ["systemctl", "restart", "systemd-resolved"]

        # Act
        with patch.object(PrivilegeManager, "_is_sudo_available", return_value=False):
            success, message = PrivilegeManager._run_elevated_command_unix(command, timeout=5)

        # Assert
        assert success == False, "Should fail when sudo unavailable"
        assert "sudo" in message.lower(), "Should mention sudo"

    def test_run_elevated_command_unix_timeout(self):
        """Test Unix elevated command timeout"""
        # Arrange
        command = ["systemctl", "restart", "systemd-resolved"]

        # Act
        with patch.object(PrivilegeManager, "_is_sudo_available", return_value=True):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sudo", 5)):
                success, message = PrivilegeManager._run_elevated_command_unix(command, timeout=5)

        # Assert
        assert success == False, "Should fail on timeout"

    def test_run_elevated_command_unix_failure(self):
        """Test Unix elevated command failure"""
        # Arrange
        command = ["systemctl", "restart", "systemd-resolved"]

        # Act
        with patch.object(PrivilegeManager, "_is_sudo_available", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 1
                mock_result.stderr = "Permission denied"
                mock_run.return_value = mock_result
                success, message = PrivilegeManager._run_elevated_command_unix(command, timeout=5)

        # Assert
        assert success == False, "Should fail when command fails"
        assert "Permission denied" in message or "failed" in message.lower(), "Should include error message"
