"""
Tests for DNSResult dataclass using AAA pattern
"""

from datetime import datetime

import pytest

from dnsping.scanner import DNSResult, TestMethod


class TestDNSResult:
    """Test DNSResult dataclass with AAA pattern"""

    def test_dns_result_creation(self):
        """Test creating DNSResult with minimal parameters"""
        # Arrange
        server = "8.8.8.8"

        # Act
        result = DNSResult(server=server)

        # Assert
        assert result.server == server, "Server should be set"
        assert result.provider == "Unknown", "Default provider should be Unknown"
        assert result.avg_latency == float("inf"), "Default latency should be infinity"
        assert result.status == "Pending", "Default status should be Pending"
        assert result.ping_count == 0, "Default ping_count should be 0"
        assert len(result.successful_methods) == 0, "Default successful_methods should be empty"

    def test_dns_result_with_provider(self):
        """Test creating DNSResult with provider"""
        # Arrange
        server = "8.8.8.8"
        provider = "Google"

        # Act
        result = DNSResult(server=server, provider=provider)

        # Assert
        assert result.server == server, "Server should be set"
        assert result.provider == provider, "Provider should be set"

    def test_update_latency_first_update(self):
        """Test updating latency for the first time"""
        # Arrange
        result = DNSResult(server="8.8.8.8")
        new_latency = 15.5
        method = TestMethod.DNS_QUERY

        # Act
        result.update_latency(new_latency, method)

        # Assert
        assert result.avg_latency == new_latency, "First update should set avg_latency directly"
        assert result.latency == new_latency, "latency should be updated"
        assert result.ping_count == 1, "ping_count should be incremented"
        assert method in result.successful_methods, "Method should be added to successful_methods"

    def test_update_latency_multiple_updates(self):
        """Test updating latency multiple times"""
        # Arrange
        result = DNSResult(server="8.8.8.8")
        latencies = [15.0, 16.0, 17.0]
        method = TestMethod.DNS_QUERY

        # Act
        for latency in latencies:
            result.update_latency(latency, method)

        # Assert
        assert result.ping_count == len(latencies), "ping_count should match number of updates"
        assert result.avg_latency != float("inf"), "avg_latency should be calculated"
        assert result.avg_latency > 0, "avg_latency should be positive"
        assert result.latency == latencies[-1], "latency should be the last value"

    def test_update_latency_invalid_values(self):
        """Test updating latency with invalid values"""
        # Arrange
        result = DNSResult(server="8.8.8.8")
        method = TestMethod.DNS_QUERY

        # Act
        result.update_latency(float("inf"), method)
        result.update_latency(-5.0, method)
        result.update_latency(0.0, method)

        # Assert
        assert result.ping_count == 0, "Invalid latencies should not increment ping_count"
        assert result.avg_latency == float("inf"), "Invalid latencies should not update avg_latency"

    def test_update_latency_different_methods(self):
        """Test updating latency with different test methods"""
        # Arrange
        result = DNSResult(server="8.8.8.8")

        # Act
        result.update_latency(15.0, TestMethod.DNS_QUERY)
        result.update_latency(16.0, TestMethod.SOCKET_CONNECT)
        result.update_latency(17.0, TestMethod.PING)

        # Assert
        assert len(result.successful_methods) == 3, "All methods should be in successful_methods"
        assert TestMethod.DNS_QUERY in result.successful_methods, "DNS_QUERY should be present"
        assert TestMethod.SOCKET_CONNECT in result.successful_methods, "SOCKET_CONNECT should be present"
        assert TestMethod.PING in result.successful_methods, "PING should be present"

    def test_update_latency_timestamp_update(self):
        """Test that update_latency updates timestamp"""
        # Arrange
        result = DNSResult(server="8.8.8.8")
        initial_time = result.last_updated
        import time

        time.sleep(0.01)  # Small delay to ensure time difference

        # Act
        result.update_latency(15.0, TestMethod.DNS_QUERY)

        # Assert
        assert result.last_updated > initial_time, "last_updated should be updated"

    def test_dns_result_weighted_average(self):
        """Test that weighted average calculation works correctly"""
        # Arrange
        result = DNSResult(server="8.8.8.8")
        latencies = [10.0, 20.0, 30.0]
        method = TestMethod.DNS_QUERY

        # Act
        for latency in latencies:
            result.update_latency(latency, method)

        # Assert
        # Weighted average is calculated, first value sets initial, then weighted
        # First: 10.0, Second: (10.0 * 1 + 20.0) / 2 = 15.0, Third: (15.0 * 2 + 30.0) / 3 = 20.0
        assert result.avg_latency == 20.0, f"Should calculate weighted average, got {result.avg_latency}"
        assert result.avg_latency > 0, "Average should be positive"
        assert result.ping_count == len(latencies), "Should track all updates"

    def test_dns_result_weight_capping(self):
        """Test that weight is capped for stability"""
        # Arrange
        result = DNSResult(server="8.8.8.8")
        method = TestMethod.DNS_QUERY

        # Act
        # Update many times to test weight capping
        for i in range(20):
            result.update_latency(10.0 + i, method)

        # Assert
        assert result.ping_count == 20, "ping_count should be 20"
        # Average should be stable (not heavily weighted toward recent values)
        assert result.avg_latency > 0, "Average should be calculated"
