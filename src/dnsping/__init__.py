"""
DNSPing - High-performance DNS server latency monitoring
"""

__version__ = "1.0.0"
__author__ = "Milad"

# Import main components for easy access
from dnsping.scanner import (
    DNSLatencyScanner,
    ScanConfig,
    main,
)

__all__ = [
    "DNSLatencyScanner",
    "ScanConfig",
    "main",
    "__version__",
]
