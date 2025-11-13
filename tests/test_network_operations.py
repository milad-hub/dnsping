"""
Tests for network operations (DNS, socket, ping) using AAA pattern
"""

import asyncio
import dataclasses
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from dnsping.scanner import DNSLatencyScanner, ScanConfig, TestMethod


class TestNetworkOperations:
    """Test network measurement operations with AAA pattern"""

    @pytest.fixture
    def scanner_config(self):
        """Create scanner configuration"""
        # Arrange
        from pathlib import Path

        return ScanConfig(
            dns_file=Path("dns_servers.txt"),
            max_servers=2,
            ping_count=1,
            timeout=0.1,
            enable_dns_query=True,
            enable_socket=True,
            enable_ping=True,
        )

    @pytest.fixture
    def scanner(self, scanner_config):
        """Create scanner instance"""
        # Arrange
        return DNSLatencyScanner(scanner_config)

    @pytest.mark.asyncio
    async def test_get_dns_resolver_without_dnspython(self, scanner_config):
        """Test DNS resolver when dnspython is not available"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_dns_query=True)
        scanner = DNSLatencyScanner(config)

        # Act
        with patch("dnsping.scanner.HAS_DNSPYTHON", False):
            async with scanner._get_dns_resolver() as resolver:
                result = resolver

        # Assert
        assert result is None, "Should return None when dnspython not available"

    @pytest.mark.asyncio
    async def test_get_dns_resolver_with_dnspython_new(self, scanner):
        """Test DNS resolver creation when pool is empty"""
        # Arrange
        scanner._resolver_pool.clear()

        # Act
        with patch("dnsping.scanner.HAS_DNSPYTHON", True):
            with patch("dns.asyncresolver.Resolver") as mock_resolver_class:
                mock_resolver = MagicMock()
                mock_resolver_class.return_value = mock_resolver
                async with scanner._get_dns_resolver() as resolver:
                    result = resolver

        # Assert
        assert result is not None, "Should create new resolver when pool is empty"
        mock_resolver_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dns_resolver_with_pool(self, scanner):
        """Test DNS resolver retrieval from pool"""
        # Arrange
        mock_resolver = MagicMock()
        scanner._resolver_pool.append(mock_resolver)

        # Act
        with patch("dnsping.scanner.HAS_DNSPYTHON", True):
            async with scanner._get_dns_resolver() as resolver:
                result = resolver
                # Check pool is empty while resolver is in use
                assert len(scanner._resolver_pool) == 0, "Should remove resolver from pool during use"

        # Assert
        assert result == mock_resolver, "Should retrieve resolver from pool"
        # After context manager exits, resolver should be returned to pool
        assert len(scanner._resolver_pool) == 1, "Should return resolver to pool after use"

    @pytest.mark.asyncio
    async def test_get_dns_resolver_returns_to_pool(self, scanner):
        """Test DNS resolver is returned to pool after use"""
        # Arrange
        mock_resolver = MagicMock()
        scanner._resolver_pool.clear()

        # Act
        with patch("dnsping.scanner.HAS_DNSPYTHON", True):
            with patch("dns.asyncresolver.Resolver", return_value=mock_resolver):
                async with scanner._get_dns_resolver() as resolver:
                    pass  # Use resolver

        # Assert
        assert mock_resolver in scanner._resolver_pool, "Should return resolver to pool"

    @pytest.mark.asyncio
    async def test_get_dns_resolver_pool_size_limit(self, scanner):
        """Test DNS resolver pool size limit"""
        # Arrange
        from dnsping.scanner import POOL_SIZE

        # Fill pool to max
        for _ in range(POOL_SIZE):
            scanner._resolver_pool.append(MagicMock())
        mock_resolver = MagicMock()

        # Act
        with patch("dnsping.scanner.HAS_DNSPYTHON", True):
            with patch("dns.asyncresolver.Resolver", return_value=mock_resolver):
                async with scanner._get_dns_resolver() as resolver:
                    pass

        # Assert
        assert len(scanner._resolver_pool) == POOL_SIZE, "Should not exceed pool size"

    @pytest.mark.asyncio
    async def test_measure_dns_query_latency_disabled(self, scanner_config):
        """Test DNS query measurement when disabled"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_dns_query=False)
        scanner = DNSLatencyScanner(config)

        # Act
        result = await scanner._measure_dns_query_latency("8.8.8.8")

        # Assert
        assert result is None, "Should return None when DNS query is disabled"

    @pytest.mark.asyncio
    async def test_measure_dns_query_latency_no_dnspython(self, scanner_config):
        """Test DNS query measurement without dnspython"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_dns_query=True)
        scanner = DNSLatencyScanner(config)

        # Act
        with patch("dnsping.scanner.HAS_DNSPYTHON", False):
            result = await scanner._measure_dns_query_latency("8.8.8.8")

        # Assert
        assert result is None, "Should return None when dnspython not available"

    @pytest.mark.asyncio
    async def test_measure_dns_query_latency_success(self, scanner_config):
        """Test successful DNS query measurement"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_dns_query=True)
        scanner = DNSLatencyScanner(config)
        mock_resolver = AsyncMock()
        mock_resolver.resolve = AsyncMock()

        # Act
        with patch("dnsping.scanner.HAS_DNSPYTHON", True):
            with patch("dnsping.scanner.DNSLatencyScanner._get_dns_resolver") as mock_get_resolver:
                mock_get_resolver.return_value.__aenter__.return_value = mock_resolver
                mock_get_resolver.return_value.__aexit__.return_value = None
                with patch("time.perf_counter", side_effect=[0.0, 0.015]):  # 15ms latency
                    result = await scanner._measure_dns_query_latency("8.8.8.8")

        # Assert
        assert result == 15.0, "Should return latency in milliseconds"
        mock_resolver.resolve.assert_called_once()

    @pytest.mark.asyncio
    async def test_measure_dns_query_latency_timeout(self, scanner_config):
        """Test DNS query measurement timeout"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_dns_query=True)
        scanner = DNSLatencyScanner(config)
        mock_resolver = AsyncMock()
        mock_resolver.resolve = AsyncMock(side_effect=asyncio.TimeoutError())

        # Act
        with patch("dnsping.scanner.HAS_DNSPYTHON", True):
            with patch("dnsping.scanner.DNSLatencyScanner._get_dns_resolver") as mock_get_resolver:
                mock_get_resolver.return_value.__aenter__.return_value = mock_resolver
                mock_get_resolver.return_value.__aexit__.return_value = None
                result = await scanner._measure_dns_query_latency("8.8.8.8")

        # Assert
        assert result is None, "Should return None on timeout"

    @pytest.mark.asyncio
    async def test_measure_dns_query_latency_high_latency(self, scanner_config):
        """Test DNS query measurement with high latency (>5000ms)"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_dns_query=True)
        scanner = DNSLatencyScanner(config)
        mock_resolver = AsyncMock()
        mock_resolver.resolve = AsyncMock()

        # Act
        with patch("dnsping.scanner.HAS_DNSPYTHON", True):
            with patch("dnsping.scanner.DNSLatencyScanner._get_dns_resolver") as mock_get_resolver:
                mock_get_resolver.return_value.__aenter__.return_value = mock_resolver
                mock_get_resolver.return_value.__aexit__.return_value = None
                with patch("time.perf_counter", side_effect=[0.0, 6.0]):  # 6000ms latency
                    result = await scanner._measure_dns_query_latency("8.8.8.8")

        # Assert
        assert result is None, "Should return None for latency > 5000ms"

    @pytest.mark.asyncio
    async def test_measure_socket_latency_disabled(self, scanner_config):
        """Test socket latency measurement when disabled"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_socket=False)
        scanner = DNSLatencyScanner(config)

        # Act
        result = await scanner._measure_socket_latency("8.8.8.8")

        # Assert
        assert result is None, "Should return None when socket is disabled"

    @pytest.mark.asyncio
    async def test_measure_socket_latency_success(self, scanner_config):
        """Test successful socket latency measurement"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_socket=True)
        scanner = DNSLatencyScanner(config)
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        # Act
        with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
            with patch("asyncio.wait_for") as mock_wait:
                mock_wait.return_value = (mock_reader, mock_writer)
                with patch("time.perf_counter", side_effect=[0.0, 0.020]):  # 20ms latency
                    result = await scanner._measure_socket_latency("8.8.8.8")

        # Assert
        assert result == 20.0, "Should return latency in milliseconds"
        mock_writer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_measure_socket_latency_timeout(self, scanner_config):
        """Test socket latency measurement timeout"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_socket=True)
        scanner = DNSLatencyScanner(config)

        # Act
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
            result = await scanner._measure_socket_latency("8.8.8.8")

        # Assert
        assert result is None, "Should return None on timeout"

    @pytest.mark.asyncio
    async def test_measure_socket_latency_high_latency(self, scanner_config):
        """Test socket latency measurement with high latency"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_socket=True)
        scanner = DNSLatencyScanner(config)
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        # Act
        with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
            with patch("asyncio.wait_for") as mock_wait:
                mock_wait.return_value = (mock_reader, mock_writer)
                with patch("time.perf_counter", side_effect=[0.0, 6.0]):  # 6000ms latency
                    result = await scanner._measure_socket_latency("8.8.8.8")

        # Assert
        assert result is None, "Should return None for latency > 5000ms"

    @pytest.mark.asyncio
    async def test_measure_ping_latency_disabled(self, scanner_config):
        """Test ping latency measurement when disabled"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_ping=False)
        scanner = DNSLatencyScanner(config)

        # Act
        result = await scanner._measure_ping_latency("8.8.8.8")

        # Assert
        assert result is None, "Should return None when ping is disabled"

    @pytest.mark.asyncio
    async def test_measure_ping_latency_windows_success(self, scanner_config):
        """Test successful ping measurement on Windows"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_ping=True)
        scanner = DNSLatencyScanner(config)
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Average = 15ms", b""))

        # Act
        with patch("os.name", "nt"):
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with patch("asyncio.wait_for") as mock_wait:
                    mock_wait.return_value = (b"Average = 15ms", b"")
                    result = await scanner._measure_ping_latency("8.8.8.8")

        # Assert
        assert result == 15.0, "Should extract latency from Windows ping output"

    @pytest.mark.asyncio
    async def test_measure_ping_latency_windows_time_format(self, scanner_config):
        """Test ping measurement with Windows time= format"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_ping=True)
        scanner = DNSLatencyScanner(config)
        mock_process = AsyncMock()
        mock_process.returncode = 0
        output = b"Reply from 8.8.8.8: bytes=32 time=12ms TTL=118"

        # Act
        with patch("os.name", "nt"):
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with patch("asyncio.wait_for", return_value=(output, b"")):
                    result = await scanner._measure_ping_latency("8.8.8.8")

        # Assert
        assert result == 12.0, "Should extract latency from time= format"

    @pytest.mark.asyncio
    async def test_measure_ping_latency_linux_success(self, scanner_config):
        """Test successful ping measurement on Linux"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_ping=True)
        scanner = DNSLatencyScanner(config)
        mock_process = AsyncMock()
        mock_process.returncode = 0
        output = b"rtt min/avg/max/mdev = 10.123/15.456/20.789/2.345 ms"

        # Act
        with patch("os.name", "posix"):
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with patch("asyncio.wait_for", return_value=(output, b"")):
                    result = await scanner._measure_ping_latency("8.8.8.8")

        # Assert
        assert result == 15.456, "Should extract latency from Linux ping output"

    @pytest.mark.asyncio
    async def test_measure_ping_latency_failure(self, scanner_config):
        """Test ping measurement when ping fails"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_ping=True)
        scanner = DNSLatencyScanner(config)
        mock_process = AsyncMock()
        mock_process.returncode = 1

        # Act
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("asyncio.wait_for", return_value=(b"", b"")):
                result = await scanner._measure_ping_latency("8.8.8.8")

        # Assert
        assert result is None, "Should return None when ping fails"

    @pytest.mark.asyncio
    async def test_measure_ping_latency_timeout(self, scanner_config):
        """Test ping measurement timeout"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_ping=True)
        scanner = DNSLatencyScanner(config)

        # Act
        with patch("asyncio.create_subprocess_exec", side_effect=asyncio.TimeoutError()):
            result = await scanner._measure_ping_latency("8.8.8.8")

        # Assert
        assert result is None, "Should return None on timeout"

    @pytest.mark.asyncio
    async def test_measure_server_latency_all_methods(self, scanner_config):
        """Test server latency measurement with all methods"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_dns_query=True, enable_socket=True, enable_ping=True)
        scanner = DNSLatencyScanner(config)

        # Act
        with patch("dnsping.scanner.HAS_DNSPYTHON", True):
            with patch("dnsping.scanner.DNSLatencyScanner._measure_dns_query_latency", return_value=15.0):
                with patch("dnsping.scanner.DNSLatencyScanner._measure_socket_latency", return_value=20.0):
                    with patch("dnsping.scanner.DNSLatencyScanner._measure_ping_latency", return_value=18.0):
                        latency, methods = await scanner._measure_server_latency("8.8.8.8")

        # Assert
        assert latency != float("inf"), "Should return valid latency"
        assert len(methods) == 3, "Should use all three methods"
        assert TestMethod.DNS_QUERY in methods, "Should include DNS query"
        assert TestMethod.SOCKET_CONNECT in methods, "Should include socket"
        assert TestMethod.PING in methods, "Should include ping"

    @pytest.mark.asyncio
    async def test_measure_server_latency_no_methods_enabled(self, scanner_config):
        """Test server latency measurement with no methods enabled"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_dns_query=False, enable_socket=False, enable_ping=False)
        scanner = DNSLatencyScanner(config)

        # Act
        latency, methods = await scanner._measure_server_latency("8.8.8.8")

        # Assert
        assert latency == float("inf"), "Should return infinity when no methods enabled"
        assert len(methods) == 0, "Should return empty methods set"

    @pytest.mark.asyncio
    async def test_measure_server_latency_exceptions(self, scanner_config):
        """Test server latency measurement with exceptions"""
        # Arrange
        # Disable all methods except DNS query to test exception handling
        config = dataclasses.replace(scanner_config, enable_dns_query=True, enable_socket=False, enable_ping=False)
        scanner = DNSLatencyScanner(config)

        # Act
        with patch("dnsping.scanner.HAS_DNSPYTHON", True):
            # Mock the method to return None (simulating failure)
            # This is more realistic as the actual code catches exceptions and returns None
            with patch("dnsping.scanner.DNSLatencyScanner._measure_dns_query_latency", return_value=None):
                latency, methods = await scanner._measure_server_latency("8.8.8.8")

        # Assert
        assert latency == float("inf"), "Should return infinity when all methods fail"
        assert len(methods) == 0, "Should return empty methods set"

    @pytest.mark.asyncio
    async def test_measure_server_latency_median_calculation(self, scanner_config):
        """Test server latency median calculation"""
        # Arrange
        config = dataclasses.replace(scanner_config, enable_dns_query=True, enable_socket=True, enable_ping=True)
        scanner = DNSLatencyScanner(config)

        # Act
        with patch("dnsping.scanner.HAS_DNSPYTHON", True):
            with patch("dnsping.scanner.DNSLatencyScanner._measure_dns_query_latency", return_value=30.0):
                with patch("dnsping.scanner.DNSLatencyScanner._measure_socket_latency", return_value=10.0):
                    with patch("dnsping.scanner.DNSLatencyScanner._measure_ping_latency", return_value=20.0):
                        latency, methods = await scanner._measure_server_latency("8.8.8.8")

        # Assert
        # Median of [10, 20, 30] should be 20
        assert latency == 20.0, "Should return median latency"
