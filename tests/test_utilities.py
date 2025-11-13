"""
Tests for utility functions using AAA pattern
"""

import os
from unittest.mock import patch

import pytest

from dnsping.scanner import LatencyLevel, TestMethod, safe_emoji, safe_unicode


class TestUtilityFunctions:
    """Test utility functions with AAA pattern"""

    def test_safe_emoji_windows_fallback(self):
        """Test safe_emoji on Windows with unsupported emoji"""
        # Arrange
        emoji = "🌐"
        fallback = "[DNS]"

        # Act
        with patch("os.name", "nt"):
            with patch("builtins.open", side_effect=UnicodeEncodeError("cp1252", "", 0, 1, "test")):
                result = safe_emoji(emoji, fallback)

        # Assert
        assert result == fallback, "Should return fallback on Windows when emoji fails"

    def test_safe_emoji_windows_success(self):
        """Test safe_emoji on Windows with supported emoji"""
        # Arrange
        emoji = "A"  # ASCII character
        fallback = "[A]"

        # Act
        with patch("os.name", "nt"):
            result = safe_emoji(emoji, fallback)

        # Assert
        assert result == emoji, "Should return emoji when supported"

    def test_safe_emoji_non_windows(self):
        """Test safe_emoji on non-Windows systems"""
        # Arrange
        emoji = "🌐"
        fallback = "[DNS]"

        # Act
        with patch("os.name", "posix"):
            result = safe_emoji(emoji, fallback)

        # Assert
        assert result == emoji, "Should return emoji on non-Windows systems"

    def test_safe_unicode_windows_fallback(self):
        """Test safe_unicode on Windows with unsupported character"""
        # Arrange
        char = "═"
        fallback = "="

        # Act
        with patch("os.name", "nt"):
            with patch("builtins.open", side_effect=UnicodeEncodeError("cp1252", "", 0, 1, "test")):
                result = safe_unicode(char, fallback)

        # Assert
        assert result == fallback, "Should return fallback on Windows when Unicode fails"

    def test_safe_unicode_windows_success(self):
        """Test safe_unicode on Windows with supported character"""
        # Arrange
        char = "-"
        fallback = "="

        # Act
        with patch("os.name", "nt"):
            result = safe_unicode(char, fallback)

        # Assert
        assert result == char, "Should return character when supported"

    def test_safe_unicode_non_windows(self):
        """Test safe_unicode on non-Windows systems"""
        # Arrange
        char = "═"
        fallback = "="

        # Act
        with patch("os.name", "posix"):
            result = safe_unicode(char, fallback)

        # Assert
        assert result == char, "Should return character on non-Windows systems"

    def test_latency_level_values(self):
        """Test LatencyLevel enum values"""
        # Arrange & Act
        excellent = LatencyLevel.EXCELLENT
        good = LatencyLevel.GOOD
        fair = LatencyLevel.FAIR
        poor = LatencyLevel.POOR

        # Assert
        assert excellent == 20, "EXCELLENT should be 20ms"
        assert good == 50, "GOOD should be 50ms"
        assert fair == 100, "FAIR should be 100ms"
        assert poor == 200, "POOR should be 200ms"

    def test_test_method_enum(self):
        """Test TestMethod enum"""
        # Arrange & Act
        dns_query = TestMethod.DNS_QUERY
        socket_connect = TestMethod.SOCKET_CONNECT
        ping = TestMethod.PING

        # Assert
        assert dns_query.display_name == "DNS", "DNS_QUERY should have display name DNS"
        assert socket_connect.display_name == "Socket", "SOCKET_CONNECT should have display name Socket"
        assert ping.display_name == "Ping", "PING should have display name Ping"
        assert dns_query.priority == 1, "DNS_QUERY should have priority 1"
        assert socket_connect.priority == 2, "SOCKET_CONNECT should have priority 2"
        assert ping.priority == 3, "PING should have priority 3"
