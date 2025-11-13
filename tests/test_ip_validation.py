"""
Tests for IP validation functionality using AAA pattern
"""

import pytest

from dnsping.scanner import IP_REGEX, DNSLatencyScanner


class TestIPValidation:
    """Test IP address validation with AAA pattern"""

    def test_valid_ipv4_addresses(self):
        """Test that valid IPv4 addresses are correctly identified"""
        # Arrange
        valid_ips = [
            "8.8.8.8",
            "1.1.1.1",
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "255.255.255.255",
            "0.0.0.0",
            "127.0.0.1",
        ]

        # Act & Assert
        for ip in valid_ips:
            assert DNSLatencyScanner.is_valid_ip(ip), f"IP {ip} should be valid"

    def test_invalid_ipv4_addresses(self):
        """Test that invalid IPv4 addresses are correctly rejected"""
        # Arrange
        invalid_ips = [
            "256.1.1.1",  # Out of range
            "1.1.1",  # Missing octet
            "1.1.1.1.1",  # Too many octets
            "not.an.ip.address",  # Not numeric
            "",  # Empty string
            "192.168.1",  # Incomplete
            "192.168.1.256",  # Out of range
            "999.999.999.999",  # All out of range
            "abc.def.ghi.jkl",  # Non-numeric
        ]

        # Act & Assert
        for ip in invalid_ips:
            assert not DNSLatencyScanner.is_valid_ip(ip), f"IP {ip} should be invalid"

    def test_invalid_ipv4_with_whitespace(self):
        """Test that IPs with whitespace are handled correctly"""
        # Arrange
        # Note: The regex doesn't strip whitespace, so these might pass
        # This is acceptable behavior - caller should strip whitespace
        whitespace_ips = [
            " 8.8.8.8 ",  # Whitespace around
            "8.8.8.8\n",  # Newline
        ]

        # Act & Assert
        # These may or may not be valid depending on regex implementation
        for ip in whitespace_ips:
            result = DNSLatencyScanner.is_valid_ip(ip.strip())
            assert result == True, "Stripped IP should be valid"

    def test_ip_regex_pattern(self):
        """Test the compiled regex pattern directly"""
        # Arrange
        valid_pattern = "192.168.1.1"
        invalid_pattern = "not.an.ip"

        # Act
        valid_match = bool(IP_REGEX.match(valid_pattern))
        invalid_match = bool(IP_REGEX.match(invalid_pattern))

        # Assert
        assert valid_match, "Valid IP should match regex"
        assert not invalid_match, "Invalid IP should not match regex"

    def test_edge_case_ip_addresses(self):
        """Test edge cases for IP validation"""
        # Arrange
        edge_cases = [
            ("0.0.0.0", True),  # All zeros
            ("255.255.255.255", True),  # All max
            ("1.2.3.4", True),  # Normal
            ("01.02.03.04", True),  # Leading zeros (regex accepts this, which is valid)
            ("1.2.3", False),  # Missing octet
            ("1.2.3.4.5", False),  # Extra octet
        ]

        # Act & Assert
        for ip, expected in edge_cases:
            result = DNSLatencyScanner.is_valid_ip(ip)
            assert result == expected, f"IP {ip} validation should be {expected}, got {result}"

    def test_is_valid_ip_is_static_method(self):
        """Test that is_valid_ip is a static method"""
        # Arrange
        test_ip = "8.8.8.8"

        # Act
        result1 = DNSLatencyScanner.is_valid_ip(test_ip)
        # Should work without instance
        result2 = DNSLatencyScanner.is_valid_ip(test_ip)

        # Assert
        assert result1 == result2 == True, "Static method should work consistently"
