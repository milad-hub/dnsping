"""
Tests for ScanConfig dataclass using AAA pattern
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from dnsping.scanner import ScanConfig


class TestScanConfig:
    """Test ScanConfig dataclass with AAA pattern"""

    def test_default_config(self):
        """Test ScanConfig with default values"""
        # Arrange & Act
        config = ScanConfig()

        # Assert
        assert config.dns_file == Path("dns_servers.txt"), "Default DNS file should be set"
        assert config.max_servers == 50, "Default max_servers should be 50"
        assert config.ping_count == 4, "Default ping_count should be 4"
        assert config.timeout == 1.0, "Default timeout should be 1.0"
        assert config.enable_ping == True, "Default enable_ping should be True"
        assert config.enable_socket == True, "Default enable_socket should be True"
        assert config.enable_dns_query == True, "Default enable_dns_query should be True"

    def test_custom_config(self):
        """Test ScanConfig with custom values"""
        # Arrange
        custom_file = Path("custom_dns.txt")
        custom_max = 100
        custom_pings = 6
        custom_timeout = 2.0

        # Act
        config = ScanConfig(
            dns_file=custom_file,
            max_servers=custom_max,
            ping_count=custom_pings,
            timeout=custom_timeout,
        )

        # Assert
        assert config.dns_file == custom_file, "Custom DNS file should be set"
        assert config.max_servers == custom_max, "Custom max_servers should be set"
        assert config.ping_count == custom_pings, "Custom ping_count should be set"
        assert config.timeout == custom_timeout, "Custom timeout should be set"

    def test_config_immutability(self):
        """Test that ScanConfig is immutable (frozen dataclass)"""
        # Arrange
        config = ScanConfig()

        # Act & Assert
        with pytest.raises(Exception):  # Should raise FrozenInstanceError or similar
            config.max_servers = 100

    def test_config_max_workers_calculation(self):
        """Test max_workers calculation with cpu_count"""
        # Arrange
        cpu_count = os.cpu_count() or 4

        # Act
        config = ScanConfig()

        # Assert
        expected_max = min(32, cpu_count * 4)
        assert config.max_workers == expected_max, f"max_workers should be {expected_max}"

    def test_config_max_workers_with_none_cpu_count(self):
        """Test max_workers when cpu_count returns None"""
        # Arrange
        original_cpu_count = os.cpu_count

        # Act
        with patch("os.cpu_count", return_value=None):
            # Should handle None gracefully
            config = ScanConfig()

        # Assert
        # Should not crash and should have a valid max_workers
        assert isinstance(config.max_workers, int), "max_workers should be integer"
        assert config.max_workers > 0, "max_workers should be positive"

    def test_config_disable_methods(self):
        """Test disabling specific test methods"""
        # Arrange
        # Act
        config = ScanConfig(enable_ping=False, enable_socket=False, enable_dns_query=True)

        # Assert
        assert config.enable_ping == False, "enable_ping should be False"
        assert config.enable_socket == False, "enable_socket should be False"
        assert config.enable_dns_query == True, "enable_dns_query should be True"

    def test_config_update_interval(self):
        """Test update_interval configuration"""
        # Arrange
        custom_interval = 1.0

        # Act
        config = ScanConfig(update_interval=custom_interval)

        # Assert
        assert config.update_interval == custom_interval, "update_interval should be set"

    def test_config_retry_count(self):
        """Test retry_count configuration"""
        # Arrange
        from dnsping.scanner import MAX_RETRIES

        # Act
        config = ScanConfig()

        # Assert
        assert config.retry_count == MAX_RETRIES, "retry_count should match MAX_RETRIES constant"
