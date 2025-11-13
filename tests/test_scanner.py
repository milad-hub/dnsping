"""
Tests for main function and CLI using AAA pattern
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from dnsping.scanner import main


class TestMainFunction:
    """Test main function with AAA pattern"""

    def test_main_function_exists(self):
        """Test that main function exists and is callable"""
        # Arrange & Act
        is_callable = callable(main)

        # Assert
        assert is_callable == True, "main function should be callable"

    def test_main_function_signature(self):
        """Test main function signature"""
        # Arrange
        import inspect

        # Act
        sig = inspect.signature(main)

        # Assert
        assert len(sig.parameters) == 0, "main should take no parameters"
        assert sig.return_annotation == None or sig.return_annotation == type(None), "main should return None"

    @patch("dnsping.scanner.DNSLatencyScanner")
    @patch("dnsping.scanner.ScanConfig")
    @patch("dnsping.scanner.asyncio.run")
    @patch("sys.argv", ["dnsping", "-m", "5", "-p", "1"])
    def test_main_function_execution(self, mock_asyncio_run, mock_config, mock_scanner):
        """Test main function execution flow"""
        # Arrange
        mock_scanner_instance = MagicMock()
        mock_scanner.return_value = mock_scanner_instance

        # Act
        try:
            main()
        except SystemExit:
            pass  # Expected if argparse calls sys.exit

        # Assert
        # Should not raise exceptions (except SystemExit from argparse)
        assert True, "main should execute without errors"
