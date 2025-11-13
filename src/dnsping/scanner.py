#!/usr/bin/env python3
"""
DNS Latency Scanner - Optimized Version
High-performance DNS server latency monitoring and ranking tool

Author: Milad
Version: 1.0.0
"""

import argparse
import asyncio
import ctypes
import importlib.resources
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from pathlib import Path
from typing import AsyncGenerator, Dict, Final, List, Optional, Set, Tuple

# Third-party imports
try:
    import dns.asyncresolver
    import dns.message
    import dns.query
    import dns.resolver

    _HAS_DNSPYTHON = True
except ImportError:
    _HAS_DNSPYTHON = False

HAS_DNSPYTHON: Final[bool] = _HAS_DNSPYTHON

# Performance Constants
SOCKET_TIMEOUT: Final[float] = 1.0
PING_TIMEOUT: Final[int] = 1000  # milliseconds
MAX_RETRIES: Final[int] = 2
POOL_SIZE: Final[int] = 10
BUFFER_SIZE: Final[int] = 8192


# Emoji-safe display for Windows compatibility
def safe_emoji(emoji: str, fallback: str) -> str:
    """Return emoji if supported, otherwise fallback text"""
    if os.name == "nt":  # Windows
        try:
            # Test if console supports Unicode
            emoji.encode("cp1252")
            return emoji
        except UnicodeEncodeError:
            return fallback
    return emoji


# Safe Unicode characters for Windows compatibility
def safe_unicode(char: str, fallback: str) -> str:
    """Return Unicode character if supported, otherwise fallback"""
    if os.name == "nt":  # Windows
        try:
            # Test if console supports Unicode
            char.encode("cp1252")
            return char
        except UnicodeEncodeError:
            return fallback
    return char


# Compiled regex for IP validation (performance optimization)
IP_REGEX: Final[re.Pattern] = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)


class LatencyLevel(IntEnum):
    """Latency performance thresholds in milliseconds"""

    EXCELLENT = 20
    GOOD = 50
    FAIR = 100
    POOR = 200


# Optimized privilege elevation utilities with caching and best practices
class PrivilegeManager:
    """High-performance privilege management with caching and lazy loading"""

    _is_admin_cache: Optional[bool] = None
    _is_windows_cache: Optional[bool] = None
    _sudo_available_cache: Optional[bool] = None

    @classmethod
    def _is_windows(cls) -> bool:
        """Cached Windows platform detection"""
        if cls._is_windows_cache is None:
            cls._is_windows_cache = os.name == "nt"
        return cls._is_windows_cache

    @classmethod
    def is_admin(cls) -> bool:
        """
        High-performance admin privilege detection with caching

        Returns:
            bool: True if running with administrator/root privileges
        """
        if cls._is_admin_cache is not None:
            return cls._is_admin_cache

        try:
            if cls._is_windows():
                # Windows: Use ctypes for maximum performance
                cls._is_admin_cache = bool(ctypes.windll.shell32.IsUserAnAdmin())
            else:
                # Unix-like: Check effective user ID
                cls._is_admin_cache = os.geteuid() == 0  # type: ignore[attr-defined]
        except (AttributeError, OSError, ImportError):
            # Fallback for edge cases or missing modules
            cls._is_admin_cache = False
        except Exception:
            # Ultimate fallback
            cls._is_admin_cache = False

        return cls._is_admin_cache

    @classmethod
    def _is_sudo_available(cls) -> bool:
        """Cached sudo availability check"""
        if cls._sudo_available_cache is not None:
            return cls._sudo_available_cache

        try:
            # Fast path: check if sudo executable exists
            cls._sudo_available_cache = shutil.which("sudo") is not None
        except (OSError, AttributeError):
            # Fallback method
            try:
                result = subprocess.run(
                    ["which", "sudo"],
                    capture_output=True,
                    timeout=2,
                    check=False,
                )
                cls._sudo_available_cache = result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                cls._sudo_available_cache = False

        return cls._sudo_available_cache

    @classmethod
    def _validate_arguments(cls, args: List[str]) -> List[str]:
        """
        Security-focused argument validation and sanitization

        Args:
            args: Command line arguments to validate

        Returns:
            List[str]: Sanitized arguments
        """
        # Filter out potentially dangerous arguments while preserving functionality
        safe_args = []
        skip_next = False

        for i, arg in enumerate(args):
            if skip_next:
                skip_next = False
                continue

            # Skip dangerous patterns
            if any(
                dangerous in arg.lower()
                for dangerous in [
                    "&",
                    "|",
                    ";",
                    "`",
                    "$",
                    ">",
                    "<",
                    "*",
                    "?",
                    "[",
                    "]",
                ]
            ):
                continue

            # Handle file arguments safely
            if arg.startswith("-") or arg.endswith(".py") or arg.endswith(".txt"):
                safe_args.append(arg)
            elif i > 0 and args[i - 1] in [
                "-t",
                "--timeout",
                "-p",
                "--pings",
                "-m",
                "--max-servers",
                "-w",
                "--workers",
            ]:
                # Numeric arguments
                try:
                    float(arg)  # Validate numeric
                    safe_args.append(arg)
                except ValueError:
                    continue

        return safe_args

    @classmethod
    def _create_elevated_command_windows(cls, original_args: List[str]) -> Tuple[str, str]:
        """
        Create secure elevated command for Windows

        Args:
            original_args: Original command line arguments

        Returns:
            Tuple[str, str]: (executable, parameters)
        """
        # Sanitize and validate arguments
        safe_args = cls._validate_arguments(original_args)

        # Add elevation marker if not present
        if "--elevated" not in safe_args:
            safe_args.append("--elevated")

        # Use secure parameter formatting
        params = " ".join(f'"{arg.replace('"', '""')}"' for arg in safe_args)

        return sys.executable, params

    @classmethod
    def _create_elevated_command_unix(cls, original_args: List[str]) -> List[str]:
        """
        Create secure elevated command for Unix-like systems

        Args:
            original_args: Original command line arguments

        Returns:
            List[str]: Sudo command with arguments
        """
        # Sanitize and validate arguments
        safe_args = cls._validate_arguments(original_args)

        # Add elevation marker if not present
        if "--elevated" not in safe_args:
            safe_args.append("--elevated")

        return ["sudo", sys.executable] + safe_args

    @classmethod
    def request_admin_privileges(cls) -> bool:
        """
        High-performance privilege elevation with security best practices

        Returns:
            bool: True if elevation was successful, False otherwise
        """
        # Fast path: already admin
        if cls.is_admin():
            return True

        try:
            if cls._is_windows():
                return cls._request_admin_windows()
            else:
                return cls._request_admin_unix()
        except Exception as e:
            logging.error(f"Privilege elevation failed: {e}")
            return False

    @classmethod
    def _request_admin_windows(cls) -> bool:
        """Windows-specific privilege elevation using UAC"""
        try:
            executable, params = cls._create_elevated_command_windows(sys.argv)

            # Use ShellExecuteW for UAC prompt
            result = ctypes.windll.shell32.ShellExecuteW(
                None,  # hwnd
                "runas",  # lpVerb (run as administrator)
                executable,  # lpFile
                params,  # lpParameters
                None,  # lpDirectory
                1,  # nShowCmd (SW_SHOWNORMAL)
            )

            # ShellExecuteW returns > 32 on success
            if result > 32:
                # Success: elevated process will start, exit current
                sys.exit(0)
            else:
                # Failed: user declined UAC or other error
                return False

        except (AttributeError, OSError) as e:
            logging.error(f"Windows elevation error: {e}")
            return False

    @classmethod
    def _request_admin_unix(cls) -> bool:
        """Unix-like system privilege elevation using sudo"""
        if not cls._is_sudo_available():
            logging.error("sudo not available for privilege elevation")
            return False

        try:
            elevated_cmd = cls._create_elevated_command_unix(sys.argv)

            # Use sudo with timeout for better UX
            result = subprocess.run(elevated_cmd, timeout=60, check=False)  # 60 second timeout for password entry

            # Success: elevated process ran, exit current
            sys.exit(result.returncode)

        except subprocess.TimeoutExpired:
            logging.error("sudo timeout: password not entered in time")
            return False
        except (FileNotFoundError, OSError) as e:
            logging.error(f"Unix elevation error: {e}")
            return False

    @classmethod
    def run_elevated_command(cls, command: List[str], timeout: int = 30) -> Tuple[bool, str]:
        """
        Run a specific command with elevated privileges without restarting script

        Args:
            command: Command to run with elevated privileges
            timeout: Command timeout in seconds

        Returns:
            Tuple[bool, str]: (success, output/error_message)
        """
        if cls.is_admin():
            # Already have privileges, run directly
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                return result.returncode == 0, result.stdout or result.stderr
            except subprocess.TimeoutExpired:
                return False, f"Command timed out after {timeout} seconds"
            except Exception as e:
                return False, str(e)

        # Need elevation
        try:
            if cls._is_windows():
                return cls._run_elevated_command_windows(command, timeout)
            else:
                return cls._run_elevated_command_unix(command, timeout)
        except Exception as e:
            logging.error(f"Elevated command execution failed: {e}")
            return False, str(e)

    @classmethod
    def _run_elevated_command_windows(cls, command: List[str], timeout: int) -> Tuple[bool, str]:
        """Run elevated command on Windows using PowerShell with UAC"""
        try:
            # Create a PowerShell command that will show UAC prompt
            ps_command = [
                "powershell",
                "-Command",
                f'Start-Process -FilePath "{command[0]}" -ArgumentList "{" ".join(command[1:])}" -Verb RunAs -Wait -WindowStyle Hidden',
            ]

            result = subprocess.run(
                ps_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

            # PowerShell Start-Process -Wait will return 0 if the elevated process completed
            if result.returncode == 0:
                return (
                    True,
                    "Command executed successfully with elevated privileges",
                )
            else:
                return (
                    False,
                    result.stderr or "User declined UAC prompt or command failed",
                )

        except subprocess.TimeoutExpired:
            return False, f"Elevation prompt timed out after {timeout} seconds"
        except Exception as e:
            return False, f"Windows elevation error: {e}"

    @classmethod
    def _run_elevated_command_unix(cls, command: List[str], timeout: int) -> Tuple[bool, str]:
        """Run elevated command on Unix-like systems using sudo"""
        if not cls._is_sudo_available():
            return False, "sudo not available for privilege elevation"

        try:
            sudo_command = ["sudo"] + command
            result = subprocess.run(
                sudo_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

            if result.returncode == 0:
                return True, result.stdout or "Command executed successfully"
            else:
                return (
                    False,
                    result.stderr or f"Command failed with exit code {result.returncode}",
                )

        except subprocess.TimeoutExpired:
            return False, f"sudo command timed out after {timeout} seconds"
        except Exception as e:
            return False, f"Unix elevation error: {e}"

    @classmethod
    def flush_dns_cache(cls) -> Tuple[bool, str]:
        """
        Flush DNS cache across all platforms with automatic privilege elevation

        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if cls._is_windows():
                # Windows: ipconfig /flushdns
                command = ["ipconfig", "/flushdns"]
                success, message = cls.run_elevated_command(command, timeout=15)
                if success:
                    return True, "DNS cache flushed successfully (Windows)"
                else:
                    return False, f"Failed to flush DNS cache: {message}"

            else:
                # Try multiple methods for Unix-like systems
                commands_to_try = [
                    # systemd-resolve (Ubuntu/Debian with systemd)
                    (
                        ["systemd-resolve", "--flush-caches"],
                        "DNS cache flushed (systemd-resolve)",
                    ),
                    # systemctl restart systemd-resolved
                    (
                        ["systemctl", "restart", "systemd-resolved"],
                        "DNS cache flushed (systemd-resolved restart)",
                    ),
                    # nscd restart (older systems)
                    (
                        ["service", "nscd", "restart"],
                        "DNS cache flushed (nscd restart)",
                    ),
                    # dscacheutil (macOS)
                    (
                        ["dscacheutil", "-flushcache"],
                        "DNS cache flushed (macOS dscacheutil)",
                    ),
                    # mDNSResponder restart (macOS alternative)
                    (
                        ["killall", "-HUP", "mDNSResponder"],
                        "DNS cache flushed (macOS mDNSResponder)",
                    ),
                ]

                for command, success_message in commands_to_try:
                    # Check if command exists
                    if shutil.which(command[0]):
                        success, message = cls.run_elevated_command(command, timeout=15)
                        if success:
                            return True, success_message

                # If no standard methods worked, try without elevation
                try:
                    # Some systems allow flushing without root
                    result = subprocess.run(
                        ["systemd-resolve", "--flush-caches"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                    )
                    if result.returncode == 0:
                        return (
                            True,
                            "DNS cache flushed (systemd-resolve, no elevation needed)",
                        )
                except (
                    subprocess.TimeoutExpired,
                    FileNotFoundError,
                    OSError,
                ) as e:
                    # Log debug message for failed attempt without elevation
                    logger = logging.getLogger(__name__)
                    logger.debug(f"Failed to flush DNS without elevation: {e}")
                    pass

                return (
                    False,
                    "No suitable DNS flush method found for this system",
                )

        except Exception as e:
            return False, f"DNS cache flush error: {e}"

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached privilege information (for testing/debugging)"""
        cls._is_admin_cache = None
        cls._is_windows_cache = None
        cls._sudo_available_cache = None


# Convenience functions for backward compatibility and clean API
def is_admin() -> bool:
    """Check if running with administrator/root privileges (cached)"""
    return PrivilegeManager.is_admin()


def request_admin_privileges() -> bool:
    """Request administrator/root privileges with security best practices"""
    return PrivilegeManager.request_admin_privileges()


class TestMethod(Enum):
    """DNS testing methods with priority ordering"""

    DNS_QUERY = ("DNS", 1)
    SOCKET_CONNECT = ("Socket", 2)
    PING = ("Ping", 3)

    def __init__(self, display_name: str, priority: int):
        self.display_name = display_name
        self.priority = priority


class Color(Enum):
    """ANSI color codes for optimized terminal output"""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    ORANGE = "\033[91m"
    RED = "\033[31m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    PURPLE = "\033[95m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RESET = "\033[0m"


@dataclass(frozen=True)
class ScanConfig:
    """Immutable scanner configuration with performance defaults"""

    dns_file: Path = Path("dns_servers.txt")
    max_servers: int = 50
    ping_count: int = 4
    timeout: float = 1.0
    max_workers: int = min(32, (os.cpu_count() or 1) * 4)  # Optimize for system
    update_interval: float = 0.5
    retry_count: int = MAX_RETRIES
    enable_ping: bool = True
    enable_socket: bool = True
    enable_dns_query: bool = True


@dataclass
class DNSResult:
    """Memory-optimized DNS test result with __slots__"""

    server: str
    provider: str = "Unknown"
    latency: float = float("inf")
    avg_latency: float = float("inf")
    status: str = "Pending"
    last_updated: datetime = field(default_factory=datetime.now)
    ping_count: int = 0
    successful_methods: Set[TestMethod] = field(default_factory=set)

    def update_latency(self, new_latency: float, method: TestMethod) -> None:
        """Update latency with running average - optimized calculation"""
        if new_latency != float("inf") and new_latency > 0:
            self.ping_count += 1
            if self.avg_latency == float("inf"):
                self.avg_latency = new_latency
            else:
                # Weighted average for better accuracy
                weight = min(self.ping_count, 10)  # Cap weight for stability
                self.avg_latency = ((self.avg_latency * (weight - 1)) + new_latency) / weight

            self.latency = new_latency
            self.successful_methods.add(method)
            self.last_updated = datetime.now()


class DNSException(Exception):
    """Base exception for DNS operations"""


class ConfigurationError(DNSException):
    """Configuration related errors"""


class NetworkError(DNSException):
    """Network related errors"""


class DNSLatencyScanner:
    """High-performance async DNS latency scanner"""

    __slots__ = (
        "config",
        "dns_servers",
        "providers",
        "results",
        "running",
        "logger",
        "_resolver_pool",
        "_lock",
        "_stats",
    )

    def __init__(self, config: ScanConfig):
        self.config = config
        self.dns_servers: List[str] = []
        self.providers: Dict[str, str] = {}
        self.results: Dict[str, DNSResult] = {}
        self.running = True
        self.logger = self._setup_logging()
        self._resolver_pool: deque = deque(maxlen=POOL_SIZE)
        self._lock = asyncio.Lock()
        self._stats = {"scanned": 0, "successful": 0, "failed": 0}

    def _setup_logging(self) -> logging.Logger:
        """Setup performance-optimized logging"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.WARNING)

        # Use efficient formatter
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(levelname)s: %(message)s", datefmt="%H:%M:%S")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        """Optimized IP validation using compiled regex"""
        return bool(IP_REGEX.match(ip))

    async def _async_file_reader(self, file_path: Path) -> AsyncGenerator[str, None]:
        """Memory-efficient async file reader"""
        try:

            def _read_file():
                with file_path.open("r", encoding="utf-8", buffering=BUFFER_SIZE) as f:
                    return f.readlines()

            lines = await asyncio.to_thread(_read_file)
            for line in lines:
                yield line.strip()
        except Exception as exc:
            raise ConfigurationError(f"Error reading file {file_path}: {exc}") from exc

    async def load_dns_servers(self) -> List[str]:
        """Optimized DNS server loading with provider mapping"""
        servers = []
        current_provider = "Unknown Provider"

        # Determine the actual file path to use
        dns_file_path = self.config.dns_file
        if str(dns_file_path) == "dns_servers.txt" and not dns_file_path.exists():
            # Use package resource for default file when it doesn't exist
            try:
                resource_path = importlib.resources.files("dnsping") / "dns_servers.txt"
                dns_file_path = Path(str(resource_path))
            except (ImportError, AttributeError):
                # Fallback for older Python versions
                try:
                    import pkg_resources  # type: ignore[import-not-found]  # noqa: PLC0415

                    dns_file_path = Path(pkg_resources.resource_filename("dnsping", "dns_servers.txt"))
                except ImportError:
                    # If pkg_resources not available, use original path
                    pass

        try:
            async for line in self._async_file_reader(dns_file_path):
                if not line or line.startswith("//"):  # Skip empty and comment lines
                    continue
                elif line.startswith("#"):
                    current_provider = line[1:].strip()
                elif self.is_valid_ip(line):
                    servers.append(line)
                    self.providers[line] = current_provider

                    if len(servers) >= self.config.max_servers:
                        break

            self.logger.info(f"Loaded {len(servers)} DNS servers with {len(set(self.providers.values()))} providers")
            return servers

        except FileNotFoundError as exc:
            raise ConfigurationError(f"DNS servers file not found: {dns_file_path}") from exc
        except Exception as exc:
            raise ConfigurationError(f"Failed to load DNS servers: {exc}") from exc

    def get_provider_name(self, server: str) -> str:
        """Fast provider name lookup with caching"""
        return self.providers.get(server, "Unknown Provider")

    @asynccontextmanager
    async def _get_dns_resolver(self):
        """High-performance DNS resolver pool manager"""
        if not HAS_DNSPYTHON:
            yield None
            return

        resolver = None
        try:
            if self._resolver_pool:
                resolver = self._resolver_pool.popleft()
            else:
                resolver = dns.asyncresolver.Resolver()
                resolver.timeout = self.config.timeout
                resolver.lifetime = self.config.timeout

            yield resolver

        finally:
            if resolver and len(self._resolver_pool) < POOL_SIZE:
                self._resolver_pool.append(resolver)

    async def _measure_dns_query_latency(self, server: str) -> Optional[float]:
        """Optimized async DNS query measurement"""
        if not self.config.enable_dns_query or not HAS_DNSPYTHON:
            return None

        try:
            async with self._get_dns_resolver() as resolver:
                if resolver is None:
                    return None

                resolver.nameservers = [server]
                start_time = time.perf_counter()
                await resolver.resolve("google.com", "A")
                end_time = time.perf_counter()

                latency = (end_time - start_time) * 1000
                return latency if latency < 5000 else None  # Sanity check

        except Exception:
            return None

    async def _measure_socket_latency(self, server: str) -> Optional[float]:
        """Optimized async socket connection measurement"""
        if not self.config.enable_socket:
            return None

        try:
            start_time = time.perf_counter()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(server, 53),
                timeout=self.config.timeout,
            )
            end_time = time.perf_counter()

            writer.close()
            await writer.wait_closed()

            latency = (end_time - start_time) * 1000
            return latency if latency < 5000 else None  # Sanity check

        except Exception:
            return None

    async def _measure_ping_latency(self, server: str) -> Optional[float]:
        """Optimized async ping measurement"""
        if not self.config.enable_ping:
            return None

        try:
            if os.name == "nt":  # Windows
                cmd = ["ping", "-n", "1", "-w", str(PING_TIMEOUT), server]
            else:  # Linux/Mac
                cmd = ["ping", "-c", "1", "-W", "1", server]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )

            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=self.config.timeout + 0.5)

            if process.returncode != 0:
                return None

            output = stdout.decode()

            # Optimized latency extraction
            if os.name == "nt":
                if "Average =" in output:
                    # Windows average format
                    for line in output.split("\n"):
                        if "Average =" in line:
                            try:
                                return float(line.split("=")[-1].replace("ms", "").strip())
                            except ValueError:
                                continue
                elif "time=" in output:
                    # Windows individual ping format
                    for line in output.split("\n"):
                        if "time=" in line:
                            try:
                                time_part = line.split("time=")[1].split("ms")[0]
                                return float(time_part)
                            except (ValueError, IndexError):
                                continue
            else:
                # Linux/Mac format
                if "avg" in output:
                    for line in output.split("\n"):
                        if "avg" in line:
                            try:
                                return float(line.split("/")[4])
                            except (ValueError, IndexError):
                                continue

            return None

        except Exception:
            return None

    async def _measure_server_latency(self, server: str) -> Tuple[float, Set[TestMethod]]:
        """Comprehensive latency measurement with all methods"""
        measurements = []
        successful_methods = set()

        # Create tasks for concurrent measurement
        tasks = []
        methods = []

        if self.config.enable_dns_query and HAS_DNSPYTHON:
            tasks.append(self._measure_dns_query_latency(server))
            methods.append(TestMethod.DNS_QUERY)

        if self.config.enable_socket:
            tasks.append(self._measure_socket_latency(server))
            methods.append(TestMethod.SOCKET_CONNECT)

        if self.config.enable_ping:
            tasks.append(self._measure_ping_latency(server))
            methods.append(TestMethod.PING)

        if not tasks:
            return float("inf"), set()

        # Execute all methods concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result, method in zip(results, methods):
            if isinstance(result, (int, float)) and result != float("inf"):
                measurements.append(result)
                successful_methods.add(method)

        if measurements:
            # Return median for better accuracy
            measurements.sort()
            median_idx = len(measurements) // 2
            best_latency = measurements[median_idx]
            return best_latency, successful_methods

        return float("inf"), set()

    async def _scan_server_multiple(self, server: str, semaphore: asyncio.Semaphore) -> None:
        """Scan server multiple times with retry logic"""
        async with semaphore:
            result = DNSResult(server=server, provider=self.get_provider_name(server))

            successful_tests = 0
            total_latency: float = 0.0
            all_methods = set()

            # Perform multiple measurements
            for attempt in range(self.config.ping_count):
                try:
                    latency, methods = await self._measure_server_latency(server)

                    if latency != float("inf") and methods:
                        total_latency += latency
                        successful_tests += 1
                        all_methods.update(methods)
                        result.update_latency(latency, next(iter(methods)))

                    # Brief pause between attempts to avoid overwhelming servers
                    if attempt < self.config.ping_count - 1:
                        await asyncio.sleep(0.02)

                except Exception as e:
                    self.logger.debug(f"Test failed for {server}: {e}")
                    continue

            # Calculate final results
            if successful_tests > 0:
                result.avg_latency = total_latency / successful_tests
                method_names = "/".join(sorted(m.display_name for m in all_methods))
                result.status = f"OK ({method_names}) - {successful_tests}/{self.config.ping_count}"
                self._stats["successful"] += 1
            else:
                result.status = f"Failed - 0/{self.config.ping_count}"
                self._stats["failed"] += 1

            # Store result atomically
            async with self._lock:
                self.results[server] = result
                self._stats["scanned"] += 1

    def _get_latency_color(self, latency: float) -> str:
        """Get optimal color for latency value"""
        if latency < LatencyLevel.EXCELLENT:
            return Color.GREEN.value
        elif latency < LatencyLevel.GOOD:
            return Color.YELLOW.value
        elif latency < LatencyLevel.FAIR:
            return Color.ORANGE.value
        else:
            return Color.RED.value

    def _create_progress_bar(self, current: int, total: int, width: int = 40) -> str:
        """Create optimized progress bar with caching"""
        if total == 0:
            return f"{Color.CYAN.value}{safe_unicode('░', '-') * width}{Color.RESET.value} 0.0% (0/0)"

        percentage = (current / total) * 100
        filled_width = int((current / total) * width)
        bar = safe_unicode("█", "#") * filled_width + safe_unicode("░", "-") * (width - filled_width)

        return f"{Color.CYAN.value}{bar}{Color.RESET.value} {percentage:.1f}% ({current}/{total})"

    def _create_latency_bar(self, latency: float, max_latency: float = 300, width: int = 10) -> str:
        """Create optimized latency visualization"""
        if latency == float("inf"):
            return safe_emoji("❌", "[FAIL]")

        filled = min(int((latency / max_latency) * width), width)
        filled = max(1, filled)

        color = self._get_latency_color(latency)
        bar = safe_unicode("█", "#") * filled + safe_unicode("░", "-") * (width - filled)
        return f"{color}{bar}{Color.RESET.value}"

    def _get_status_icon(self, latency: float) -> str:
        """Get status icon based on latency"""
        if latency == float("inf"):
            return safe_emoji("❌", "[FAIL]")
        elif latency < LatencyLevel.EXCELLENT:
            return safe_emoji("🟢", "[EXC]")
        elif latency < LatencyLevel.GOOD:
            return safe_emoji("🟡", "[GOOD]")
        elif latency < LatencyLevel.FAIR:
            return safe_emoji("🟠", "[FAIR]")
        else:
            return safe_emoji("🔴", "[POOR]")

    async def _display_live_results(self) -> None:
        """Optimized real-time results display"""
        last_update = 0.0
        display_buffer: List[str] = []

        while self.running:
            current_time = time.time()
            if current_time - last_update < self.config.update_interval:
                await asyncio.sleep(0.1)
                continue

            last_update = current_time

            # Build display buffer for atomic output
            display_buffer.clear()

            # Header
            display_buffer.extend(
                [
                    f"{Color.BOLD.value}{Color.CYAN.value}{safe_emoji('🌐', '[DNS]')} DNS Latency Scanner - Live Results{Color.RESET.value}",
                    f"{Color.BLUE.value}{safe_unicode('═', '=') * 100}{Color.RESET.value}",
                ]
            )

            # Progress and stats
            async with self._lock:
                scanned = self._stats["scanned"]
                successful = self._stats["successful"]
                total = len(self.dns_servers)

                progress_bar = self._create_progress_bar(scanned, total)
                display_buffer.extend(
                    [
                        f"{Color.PURPLE.value}{safe_emoji('📊', '[PROGRESS]')} Progress: {progress_bar}{Color.RESET.value}",
                        f"{Color.PURPLE.value}{safe_emoji('🎯', '[SUCCESS]')} Success Rate: {successful}/{scanned} servers {safe_unicode('•', '*')} {self.config.ping_count} tests each{Color.RESET.value}",
                        f"{Color.CYAN.value}{safe_unicode('─', '-') * 100}{Color.RESET.value}",
                    ]
                )

                if self.results:
                    # Sort and display top results
                    sorted_results = sorted(
                        self.results.values(),
                        key=lambda x: (x.avg_latency if x.avg_latency != float("inf") else 999999),
                    )

                    display_buffer.extend(
                        [
                            f"{Color.BOLD.value}{'Rank':<4} {'DNS Server':<15} {'Provider':<18} {'Latency':<10} {'Visual':<12} {'Status':<15}{Color.RESET.value}",
                            f"{Color.CYAN.value}{safe_unicode('─', '-') * 100}{Color.RESET.value}",
                        ]
                    )

                    # Show top 15 results
                    for i, result in enumerate(sorted_results[:15], 1):
                        if result.avg_latency != float("inf"):
                            latency_str = f"{result.avg_latency:.1f}ms"
                            colored_latency = (
                                f"{self._get_latency_color(result.avg_latency)}{latency_str}{Color.RESET.value}"
                            )
                        else:
                            colored_latency = f"{Color.RED.value}Failed{Color.RESET.value}"

                        provider = result.provider[:15] + "..." if len(result.provider) > 18 else result.provider
                        status_icon = self._get_status_icon(result.avg_latency)
                        mini_bar = self._create_latency_bar(result.avg_latency, 200, 8)
                        status = result.status[:12] + "..." if len(result.status) > 15 else result.status

                        display_buffer.append(
                            f"{status_icon}{i:<3} {result.server:<15} {provider:<18} {colored_latency:<18} {mini_bar:<20} {status:<15}"
                        )

                    if len(sorted_results) > 15:
                        remaining = len(sorted_results) - 15
                        display_buffer.append(
                            f"{Color.PURPLE.value}... and {remaining} more servers{Color.RESET.value}"
                        )
                else:
                    display_buffer.append(
                        f"{Color.YELLOW.value}{safe_emoji('⏳', '[STARTING]')} Starting tests...{Color.RESET.value}"
                    )

            display_buffer.extend(
                [
                    f"{Color.BLUE.value}{safe_unicode('═', '=') * 100}{Color.RESET.value}",
                    f"{Color.CYAN.value}{safe_emoji('💡', '[TIP]')} Press Ctrl+C to stop scanning{Color.RESET.value}",
                ]
            )

            # Clear screen and display atomically
            os.system("cls" if os.name == "nt" else "clear")
            print("\n".join(display_buffer))

    async def _scan_all_servers(self) -> None:
        """Main scanning orchestrator with optimized concurrency"""
        # Create semaphore for controlled concurrency
        semaphore = asyncio.Semaphore(self.config.max_workers)

        # Start live display
        display_task = asyncio.create_task(self._display_live_results())

        try:
            # Create all scanning tasks
            scan_tasks = [self._scan_server_multiple(server, semaphore) for server in self.dns_servers]

            # Execute all scans concurrently
            await asyncio.gather(*scan_tasks, return_exceptions=True)

            # Brief pause to show final live results
            await asyncio.sleep(1.5)

        finally:
            self.running = False
            display_task.cancel()

            try:
                await display_task
            except asyncio.CancelledError:
                pass

    def _display_final_results(self) -> None:
        """Display comprehensive final results"""
        os.system("cls" if os.name == "nt" else "clear")

        print(
            f"\n{Color.BOLD.value}{Color.CYAN.value}{safe_emoji('🌐', '[DNS]')} DNS Latency Scanner - Final Results{Color.RESET.value}"
        )
        print(f"{Color.BLUE.value}{safe_unicode('═', '=') * 130}{Color.RESET.value}")
        print(
            f"{Color.PURPLE.value}{safe_emoji('📊', '[STATS]')} Scanned {len(self.dns_servers)} DNS servers {safe_unicode('•', '*')} {self.config.ping_count} tests per server{Color.RESET.value}"
        )
        print(
            f"{Color.PURPLE.value}{safe_emoji('🕒', '[TIME]')} Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Color.RESET.value}"
        )
        print(f"{Color.BLUE.value}{safe_unicode('═', '=') * 130}{Color.RESET.value}")

        if not self.results:
            print(f"{Color.RED.value}{safe_emoji('❌', '[ERROR]')} No results available{Color.RESET.value}")
            return

        # Sort results by performance
        sorted_results = sorted(
            self.results.values(),
            key=lambda x: (
                x.avg_latency if x.avg_latency != float("inf") else 999999.0,
                -len(x.successful_methods),
            ),
        )

        # Display results table
        print(
            f"{Color.BOLD.value}{'Rank':<4} {'DNS Server':<16} {'Provider':<22} {'Latency':<12} {'Visual':<12} {'Status':<20} {'Success':<8}{Color.RESET.value}"
        )
        print(f"{Color.CYAN.value}{safe_unicode('─', '-') * 130}{Color.RESET.value}")

        successful_count = 0
        total_latency: float = 0.0

        for i, result in enumerate(sorted_results[: self.config.max_servers], 1):
            if result.avg_latency != float("inf"):
                successful_count += 1
                total_latency += result.avg_latency
                latency_str = f"{result.avg_latency:.1f}ms"
                colored_latency = f"{self._get_latency_color(result.avg_latency)}{latency_str}{Color.RESET.value}"
            else:
                colored_latency = f"{Color.RED.value}Failed{Color.RESET.value}"

            provider = result.provider[:19] + "..." if len(result.provider) > 22 else result.provider
            status_icon = self._get_status_icon(result.avg_latency)
            latency_bar = self._create_latency_bar(result.avg_latency)
            status = result.status[:17] + "..." if len(result.status) > 20 else result.status

            success_rate = f"{(result.ping_count/self.config.ping_count*100):.0f}%" if result.ping_count > 0 else "0%"

            print(
                f"{status_icon}{i:<3} {result.server:<16} {provider:<22} {colored_latency:<20} {latency_bar:<20} {status:<20} {success_rate:<8}"
            )

        print(f"{Color.BLUE.value}{safe_unicode('═', '=') * 130}{Color.RESET.value}")

        # Enhanced summary statistics
        if successful_count > 0:
            print(
                f"\n{Color.BOLD.value}{Color.GREEN.value}{safe_emoji('📊', '[SUMMARY]')} PERFORMANCE SUMMARY{Color.RESET.value}"
            )
            print(
                f"{Color.GREEN.value}{safe_emoji('✅', '[OK]')} Successful servers: {successful_count}/{len(self.results)}{Color.RESET.value}"
            )

            # Best performer
            best_result = sorted_results[0]
            if best_result.avg_latency != float("inf"):
                best_colored = f"{self._get_latency_color(best_result.avg_latency)}{best_result.avg_latency:.1f}ms{Color.RESET.value}"
                print(
                    f"{Color.YELLOW.value}{safe_emoji('🏆', '[BEST]')} Best DNS: {Color.BOLD.value}{best_result.server}{Color.RESET.value} {Color.CYAN.value}({best_result.provider}){Color.RESET.value} - {best_colored}"
                )

                # Performance categories
                excellent = sum(1 for r in sorted_results if r.avg_latency < LatencyLevel.EXCELLENT)
                good = sum(1 for r in sorted_results if LatencyLevel.EXCELLENT <= r.avg_latency < LatencyLevel.GOOD)
                fair = sum(1 for r in sorted_results if LatencyLevel.GOOD <= r.avg_latency < LatencyLevel.FAIR)
                poor = sum(1 for r in sorted_results if LatencyLevel.FAIR <= r.avg_latency < float("inf"))

                print(
                    f"{Color.GREEN.value}{safe_emoji('🚀', '[EXCELLENT]')} Excellent (<20ms): {excellent}{Color.RESET.value}"
                )
                print(f"{Color.YELLOW.value}{safe_emoji('👍', '[GOOD]')} Good (20-50ms): {good}{Color.RESET.value}")
                print(f"{Color.ORANGE.value}{safe_emoji('👌', '[FAIR]')} Fair (50-100ms): {fair}{Color.RESET.value}")
                print(f"{Color.RED.value}{safe_emoji('👎', '[POOR]')} Poor (>100ms): {poor}{Color.RESET.value}")

        print(f"{Color.BLUE.value}{safe_unicode('═', '=') * 130}{Color.RESET.value}")

        # DNS configuration
        if successful_count > 0:
            self._handle_dns_selection(sorted_results)

    def _handle_dns_selection(self, sorted_results: List[DNSResult]) -> None:
        """Optimized DNS selection and configuration"""
        print(
            f"\n{Color.BOLD.value}{Color.GREEN.value}{safe_emoji('🔧', '[CONFIG]')} DNS Configuration{Color.RESET.value}"
        )
        print(f"{Color.CYAN.value}{safe_unicode('─', '-') * 70}{Color.RESET.value}")
        print(f"{Color.YELLOW.value}Configure one of the tested DNS servers on your system?{Color.RESET.value}")
        print(
            f"{Color.PURPLE.value}Enter rank number (1-{min(len(sorted_results), self.config.max_servers)}) or press Enter to skip:{Color.RESET.value}"
        )

        try:
            choice = input(f"{Color.CYAN.value}Your choice: {Color.RESET.value}").strip()

            if not choice:
                print(f"{Color.YELLOW.value}{safe_emoji('⏭️', '[SKIP]')} DNS configuration skipped{Color.RESET.value}")
            else:
                rank = int(choice)
                valid_results = [r for r in sorted_results if r.avg_latency != float("inf")]

                if 1 <= rank <= len(valid_results):
                    selected_result = valid_results[rank - 1]
                    self._configure_system_dns(selected_result, valid_results)
                else:
                    print(
                        f"{Color.RED.value}{safe_emoji('❌', '[ERROR]')} Invalid selection. Choose 1-{len(valid_results)}{Color.RESET.value}"
                    )

        except (ValueError, KeyboardInterrupt, EOFError):
            print(f"{Color.YELLOW.value}{safe_emoji('⏭️', '[CANCEL]')} Operation cancelled{Color.RESET.value}")

        print(f"\n{Color.CYAN.value}{safe_emoji('💡', '[TIP]')} Press Enter to exit...{Color.RESET.value}")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass

    def _configure_system_dns(self, selected_result: DNSResult, all_results: List[DNSResult]) -> None:
        """Configure system DNS with selected server"""
        print(f"\n{Color.YELLOW.value}{safe_emoji('📋', '[CONFIG]')} Selected Configuration:{Color.RESET.value}")
        print(
            f"   Primary: {Color.BOLD.value}{selected_result.server}{Color.RESET.value} ({Color.CYAN.value}{selected_result.provider}{Color.RESET.value})"
        )
        print(
            f"   Latency: {self._get_latency_color(selected_result.avg_latency)}{selected_result.avg_latency:.1f}ms{Color.RESET.value}"
        )

        # Find optimal secondary DNS from same provider
        secondary_dns = None
        for result in all_results:
            if (
                result.server != selected_result.server
                and result.provider == selected_result.provider
                and result.avg_latency != float("inf")
            ):
                secondary_dns = result.server
                break

        if secondary_dns:
            print(
                f"   Secondary: {Color.BOLD.value}{secondary_dns}{Color.RESET.value} ({Color.CYAN.value}{selected_result.provider}{Color.RESET.value})"
            )

        print(
            f"\n{Color.RED.value}{safe_emoji('⚠️', '[WARN]')} This will modify your system DNS configuration{Color.RESET.value}"
        )
        print(f"{Color.YELLOW.value}Note: Administrator/root privileges required{Color.RESET.value}")

        try:
            confirm = (
                input(f"\n{Color.CYAN.value}Proceed with DNS configuration? (y/N): {Color.RESET.value}").strip().lower()
            )
        except (KeyboardInterrupt, EOFError):
            confirm = "n"

        if confirm in ["y", "yes"]:
            print(
                f"\n{Color.YELLOW.value}{safe_emoji('🔄', '[CONFIGURING]')} Configuring DNS servers...{Color.RESET.value}"
            )

            # Inform user about potential privilege elevation
            if not is_admin():
                print(
                    f"{Color.YELLOW.value}{safe_emoji('🔐', '[ADMIN]')} Administrator privileges may be required{Color.RESET.value}"
                )
                if os.name == "nt":  # Windows
                    print(
                        f"{Color.CYAN.value}   A UAC prompt may appear - please click 'Yes' if prompted{Color.RESET.value}"
                    )
                else:  # Linux/Mac
                    print(f"{Color.CYAN.value}   You may be prompted to enter your password{Color.RESET.value}")

            # Use the new targeted elevation approach
            success, message = self._set_system_dns_elevated(selected_result.server, secondary_dns)

            if success:
                print(f"{Color.GREEN.value}{safe_emoji('✅', '[OK]')} {message}{Color.RESET.value}")
                print(f"   Primary: {Color.BOLD.value}{selected_result.server}{Color.RESET.value}")
                if secondary_dns:
                    print(f"   Secondary: {Color.BOLD.value}{secondary_dns}{Color.RESET.value}")

                # Automatic DNS flushing
                print(
                    f"\n{Color.YELLOW.value}{safe_emoji('🔄', '[FLUSHING]')} Flushing DNS cache...{Color.RESET.value}"
                )
                flush_success, flush_message = PrivilegeManager.flush_dns_cache()

                if flush_success:
                    print(f"{Color.GREEN.value}{safe_emoji('✅', '[OK]')} {flush_message}{Color.RESET.value}")
                else:
                    print(f"{Color.YELLOW.value}{safe_emoji('⚠️', '[WARN]')} {flush_message}{Color.RESET.value}")
                    # Show manual flush instructions as fallback
                    if os.name == "nt":
                        print(f"{Color.CYAN.value}   Manual flush: ipconfig /flushdns{Color.RESET.value}")
                    else:
                        print(
                            f"{Color.CYAN.value}   Manual flush: sudo systemd-resolve --flush-caches{Color.RESET.value}"
                        )

                print(
                    f"\n{Color.PURPLE.value}{safe_emoji('💡', '[TIP]')} Configuration complete! Additional recommendations:{Color.RESET.value}"
                )
                print(f"{Color.CYAN.value}   • Restart web browsers for best results{Color.RESET.value}")
                print(f"{Color.CYAN.value}   • Test connectivity to ensure everything works{Color.RESET.value}")
                print(f"{Color.CYAN.value}   • Monitor performance over the next few minutes{Color.RESET.value}")

            else:
                print(f"{Color.RED.value}{safe_emoji('❌', '[ERROR]')} {message}{Color.RESET.value}")
                print(f"{Color.YELLOW.value}{safe_emoji('💡', '[TIP]')} This can happen if:{Color.RESET.value}")
                print(f"{Color.CYAN.value}   • You declined the privilege elevation prompt{Color.RESET.value}")
                print(f"{Color.CYAN.value}   • Network interface could not be identified{Color.RESET.value}")
                print(f"{Color.CYAN.value}   • System policies prevent DNS modification{Color.RESET.value}")

                print(
                    f"\n{Color.YELLOW.value}{safe_emoji('📋', '[MANUAL]')} Manual configuration instructions:{Color.RESET.value}"
                )
                print(f"{Color.CYAN.value}   Primary DNS: {selected_result.server}{Color.RESET.value}")
                if secondary_dns:
                    print(f"{Color.CYAN.value}   Secondary DNS: {secondary_dns}{Color.RESET.value}")

                if os.name == "nt":
                    print(f"\n{Color.PURPLE.value}Windows Manual Steps:{Color.RESET.value}")
                    print(
                        f"{Color.CYAN.value}   1. Open Settings > Network & Internet > Wi-Fi (or Ethernet){Color.RESET.value}"
                    )
                    print(f"{Color.CYAN.value}   2. Click your connection > Properties{Color.RESET.value}")
                    print(f"{Color.CYAN.value}   3. Edit IP assignment > Manual > IPv4 On{Color.RESET.value}")
                    print(f"{Color.CYAN.value}   4. Set DNS servers as shown above{Color.RESET.value}")
                else:
                    print(f"\n{Color.PURPLE.value}Linux/Mac Manual Steps:{Color.RESET.value}")
                    print(
                        f"{Color.CYAN.value}   1. Edit /etc/resolv.conf with administrator privileges{Color.RESET.value}"
                    )
                    print(f"{Color.CYAN.value}   2. Add the nameserver entries as shown above{Color.RESET.value}")
                    print(f"{Color.CYAN.value}   3. Save and restart network services{Color.RESET.value}")
        else:
            print(
                f"{Color.YELLOW.value}{safe_emoji('⏭️', '[CANCELLED]')} DNS configuration cancelled{Color.RESET.value}"
            )

    def _set_system_dns_elevated(self, primary_dns: str, secondary_dns: Optional[str] = None) -> Tuple[bool, str]:
        """
        Set system DNS using targeted privilege elevation and automatic flushing

        Args:
            primary_dns: Primary DNS server IP
            secondary_dns: Optional secondary DNS server IP

        Returns:
            Tuple[bool, str]: (success, detailed_message)
        """
        try:
            if os.name == "nt":  # Windows
                return self._set_dns_windows_elevated(primary_dns, secondary_dns)
            else:  # Linux/Mac
                return self._set_dns_unix_elevated(primary_dns, secondary_dns)
        except Exception as e:
            error_msg = f"DNS configuration failed: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def _set_dns_windows_elevated(self, primary_dns: str, secondary_dns: Optional[str] = None) -> Tuple[bool, str]:
        """Set DNS on Windows with targeted elevation"""
        try:
            # Find active network interface first (no elevation needed)
            interface_result = subprocess.run(
                ["netsh", "interface", "show", "interface"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            interface_name = None
            if interface_result.returncode == 0:
                for line in interface_result.stdout.split("\n"):
                    if "Connected" in line and "Dedicated" in line:
                        parts = line.split()
                        if len(parts) > 3:
                            interface_name = " ".join(parts[3:])
                            break

            # Fallback to common interface names
            if not interface_name:
                common_interfaces = [
                    "Wi-Fi",
                    "Ethernet",
                    "Local Area Connection",
                    "Wireless Network Connection",
                ]
                interface_name = common_interfaces[0]  # Default to Wi-Fi

            if interface_name:
                # Set primary DNS with elevation
                primary_cmd = [
                    "netsh",
                    "interface",
                    "ip",
                    "set",
                    "dns",
                    interface_name,
                    "static",
                    primary_dns,
                ]
                success, message = PrivilegeManager.run_elevated_command(primary_cmd, timeout=30)

                if not success:
                    return False, f"Failed to set primary DNS: {message}"

                # Set secondary DNS with elevation (if provided)
                if secondary_dns:
                    secondary_cmd = [
                        "netsh",
                        "interface",
                        "ip",
                        "add",
                        "dns",
                        interface_name,
                        secondary_dns,
                        "index=2",
                    ]
                    sec_success, sec_message = PrivilegeManager.run_elevated_command(secondary_cmd, timeout=30)
                    if not sec_success:
                        self.logger.warning(f"Secondary DNS setting failed: {sec_message}")

                return (
                    True,
                    f"DNS configured successfully on interface '{interface_name}'",
                )
            else:
                return False, "Could not identify active network interface"

        except Exception as e:
            return False, f"Windows DNS configuration error: {e}"

    def _set_dns_unix_elevated(self, primary_dns: str, secondary_dns: Optional[str] = None) -> Tuple[bool, str]:
        """Set DNS on Unix-like systems with targeted elevation"""
        try:
            # Prepare resolv.conf content
            resolv_conf_content = f"nameserver {primary_dns}\n"
            if secondary_dns:
                resolv_conf_content += f"nameserver {secondary_dns}\n"

            # Create temporary file with new content
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp") as tmp_file:
                tmp_file.write(resolv_conf_content)
                tmp_file_path = tmp_file.name

            try:
                # Copy temporary file to /etc/resolv.conf with elevation
                copy_cmd = ["cp", tmp_file_path, "/etc/resolv.conf"]
                success, message = PrivilegeManager.run_elevated_command(copy_cmd, timeout=30)

                if success:
                    return (
                        True,
                        "DNS configured successfully in /etc/resolv.conf",
                    )
                else:
                    return False, f"Failed to update resolv.conf: {message}"

            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_file_path)
                except (FileNotFoundError, PermissionError, OSError) as e:
                    # Log debug message for cleanup failure (non-critical)
                    logger = logging.getLogger(__name__)
                    logger.debug(f"Failed to clean up temporary file {tmp_file_path}: {e}")
                    pass

        except Exception as e:
            return False, f"Unix DNS configuration error: {e}"

    def _set_system_dns(self, primary_dns: str, secondary_dns: Optional[str] = None) -> bool:
        """Legacy method - now uses elevated approach"""
        success, _ = self._set_system_dns_elevated(primary_dns, secondary_dns)
        return success

    async def run(self) -> None:
        """Main execution with comprehensive error handling"""
        try:
            # Initialize display
            os.system("cls" if os.name == "nt" else "clear")

            print(
                f"{Color.BOLD.value}{Color.CYAN.value}{safe_emoji('🌐', '[DNS]')} DNS Latency Scanner v1.0.0 (Optimized){Color.RESET.value}"
            )
            if is_admin():
                print(
                    f"{Color.GREEN.value}{safe_emoji('🔐', '[ADMIN]')} Running with administrator privileges{Color.RESET.value}"
                )
            print(f"{Color.BLUE.value}{safe_unicode('═', '=') * 80}{Color.RESET.value}")

            # Load DNS servers
            print(f"{Color.YELLOW.value}{safe_emoji('⏳', '[LOADING]')} Loading DNS servers...{Color.RESET.value}")
            self.dns_servers = await self.load_dns_servers()

            print(
                f"{Color.GREEN.value}{safe_emoji('✅', '[OK]')} Loaded {len(self.dns_servers)} servers from {self.config.dns_file.name}{Color.RESET.value}"
            )
            print(
                f"{Color.PURPLE.value}{safe_emoji('🔧', '[WORKERS]')} Using {self.config.max_workers} concurrent workers{Color.RESET.value}"
            )
            print(f"{Color.BLUE.value}{safe_unicode('═', '=') * 80}{Color.RESET.value}")

            # Check dependencies
            if not HAS_DNSPYTHON:
                print(
                    f"{Color.YELLOW.value}{safe_emoji('⚠️', '[WARN]')} dnspython not available - using fallback methods{Color.RESET.value}"
                )
                print(f"{Color.CYAN.value}   Install with: pip install dnspython{Color.RESET.value}")
                print()

            # Start scanning
            print(
                f"{Color.CYAN.value}{safe_emoji('🚀', '[START]')} Starting high-performance DNS scan...{Color.RESET.value}"
            )
            await asyncio.sleep(1)

            await self._scan_all_servers()

            # Display results
            self._display_final_results()

        except ConfigurationError as e:
            print(f"{Color.RED.value}{safe_emoji('❌', '[ERROR]')} Configuration Error: {e}{Color.RESET.value}")
        except KeyboardInterrupt:
            print(f"\n{Color.YELLOW.value}{safe_emoji('🛑', '[STOP]')} Scan interrupted by user{Color.RESET.value}")
        except Exception as e:
            print(f"{Color.RED.value}{safe_emoji('❌', '[ERROR]')} Unexpected error: {e}{Color.RESET.value}")
            self.logger.error("Unexpected error", exc_info=True)
        finally:
            self.running = False


def main() -> None:
    """Optimized main function with comprehensive CLI"""
    parser = argparse.ArgumentParser(
        description="DNS Latency Scanner v1.0.0 - High Performance Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Basic scan with defaults
  %(prog)s -p 6 -m 100 -w 16           # 6 pings, 100 servers, 16 workers
  %(prog)s custom_dns.txt -t 2.0       # Custom file with 2s timeout
  %(prog)s --no-ping --no-socket       # DNS queries only
        """,
    )

    parser.add_argument(
        "dns_file",
        nargs="?",
        default="dns_servers.txt",
        help="DNS servers file (default: dns_servers.txt)",
    )
    parser.add_argument(
        "-p",
        "--pings",
        type=int,
        default=4,
        help="Tests per server (default: 4)",
    )
    parser.add_argument(
        "-m",
        "--max-servers",
        type=int,
        default=50,
        help="Maximum servers to scan (default: 50)",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=1.0,
        help="Timeout per test in seconds (default: 1.0)",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=0,
        help="Concurrent workers (default: auto-detect)",
    )
    parser.add_argument(
        "-u",
        "--update-interval",
        type=float,
        default=0.5,
        help="Live display update interval (default: 0.5s)",
    )
    parser.add_argument("--no-dns", action="store_true", help="Disable DNS query method")
    parser.add_argument(
        "--no-socket",
        action="store_true",
        help="Disable socket connection method",
    )
    parser.add_argument("--no-ping", action="store_true", help="Disable ping method")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--version", action="version", version="DNSPing v1.0.0")
    parser.add_argument("--elevated", action="store_true", help=argparse.SUPPRESS)  # Hidden flag for elevated runs

    args = parser.parse_args()

    # Configure logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
        )

    # Determine optimal worker count
    if args.workers <= 0:
        cpu_count = os.cpu_count() or 1
        args.workers = min(32, max(8, cpu_count * 4))

    # Create optimized configuration
    config = ScanConfig(
        dns_file=Path(args.dns_file),
        max_servers=args.max_servers,
        ping_count=args.pings,
        timeout=args.timeout,
        max_workers=args.workers,
        update_interval=args.update_interval,
        enable_dns_query=not args.no_dns and HAS_DNSPYTHON,
        enable_socket=not args.no_socket,
        enable_ping=not args.no_ping,
    )

    # Validate configuration
    if not any([config.enable_dns_query, config.enable_socket, config.enable_ping]):
        print(
            f"{Color.RED.value}{safe_emoji('❌', '[ERROR]')} Error: At least one test method must be enabled{Color.RESET.value}"
        )
        sys.exit(1)

    # Run scanner
    scanner = DNSLatencyScanner(config)

    try:
        # Use optimal event loop policy
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        asyncio.run(scanner.run())

    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW.value}{safe_emoji('👋', '[BYE]')} Scan cancelled - goodbye!{Color.RESET.value}")
    except Exception as e:
        print(f"{Color.RED.value}{safe_emoji('❌', '[ERROR]')} Critical error: {e}{Color.RESET.value}")
        sys.exit(1)


if __name__ == "__main__":
    main()
