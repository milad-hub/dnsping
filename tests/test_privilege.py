"""
Tests for privilege management convenience functions using AAA pattern
"""

from unittest.mock import patch

import pytest

from dnsping.scanner import PrivilegeManager, is_admin, request_admin_privileges


class TestPrivilegeConvenienceFunctions:
    """Test convenience functions for privilege management with AAA pattern"""

    def test_is_admin_function_exists(self):
        """Test that is_admin convenience function exists"""
        # Arrange & Act
        is_callable = callable(is_admin)

        # Assert
        assert is_callable == True, "is_admin should be callable"

    def test_is_admin_delegates_to_manager(self):
        """Test that is_admin delegates to PrivilegeManager"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "is_admin", return_value=True):
            result = is_admin()

        # Assert
        assert result == True, "is_admin should delegate to PrivilegeManager"

    def test_request_admin_privileges_function_exists(self):
        """Test that request_admin_privileges convenience function exists"""
        # Arrange & Act
        is_callable = callable(request_admin_privileges)

        # Assert
        assert is_callable == True, "request_admin_privileges should be callable"

    def test_request_admin_privileges_delegates_to_manager(self):
        """Test that request_admin_privileges delegates to PrivilegeManager"""
        # Arrange
        PrivilegeManager.clear_cache()

        # Act
        with patch.object(PrivilegeManager, "request_admin_privileges", return_value=False):
            result = request_admin_privileges()

        # Assert
        assert result == False, "request_admin_privileges should delegate to PrivilegeManager"
