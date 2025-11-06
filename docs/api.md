# API Reference

## 📚 Overview

DNSPing can be used both as a command-line tool and as a Python library. This document covers the programmatic API.

## 🚀 Quick Start (Library Usage)

```python
from dnsping import DNSLatencyScanner, ScanConfig

# Create configuration
config = ScanConfig(
    max_servers=20,
    ping_count=4,
    timeout=1.0,
    enable_dns_query=True,
    enable_socket=True,
    enable_ping=True
)

# Create scanner
scanner = DNSLatencyScanner(config)

# Run scan (async)
import asyncio

async def main():
    await scanner.run()

asyncio.run(main())

# Access results
for server, result in scanner.results.items():
    print(f"{server}: {result.avg_latency}ms")
```

## 📋 Classes

### `ScanConfig`

Configuration class for DNS scanning.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dns_file` | `Path` | `Path("dns_servers.txt")` | Path to DNS servers file |
| `max_servers` | `int` | `50` | Maximum servers to scan |
| `ping_count` | `int` | `4` | Number of tests per server |
| `timeout` | `float` | `1.0` | Timeout per test (seconds) |
| `max_workers` | `int` | `auto` | Concurrent workers (auto-detected) |
| `update_interval` | `float` | `0.5` | Live display update interval |
| `retry_count` | `int` | `2` | Retry attempts per test |
| `enable_dns_query` | `bool` | `True` | Enable DNS query tests |
| `enable_socket` | `bool` | `True` | Enable socket connection tests |
| `enable_ping` | `bool` | `True` | Enable ICMP ping tests |

#### Example

```python
from pathlib import Path
from dnsping import ScanConfig

config = ScanConfig(
    dns_file=Path("my_dns.txt"),
    max_servers=100,
    ping_count=8,
    timeout=2.0,
    enable_ping=False  # Disable ping tests
)
```

### `DNSLatencyScanner`

Main scanner class for performing DNS latency tests.

#### Constructor

```python
DNSLatencyScanner(config: ScanConfig)
```

#### Methods

##### `async run() -> None`

Run the DNS latency scan.

```python
scanner = DNSLatencyScanner(config)
await scanner.run()
```

##### `async load_dns_servers() -> List[str]`

Load DNS servers from the configured file.

```python
servers = await scanner.load_dns_servers()
print(f"Loaded {len(servers)} servers")
```

##### `get_provider_name(server: str) -> str`

Get the provider name for a DNS server.

```python
provider = scanner.get_provider_name("8.8.8.8")
print(provider)  # "Google Public DNS"
```

#### Properties

##### `results: Dict[str, DNSResult]`

Dictionary mapping server IPs to their test results.

```python
for server_ip, result in scanner.results.items():
    print(f"{server_ip}: {result.avg_latency}ms")
```

##### `dns_servers: List[str]`

List of DNS server IPs to test.

##### `providers: Dict[str, str]`

Dictionary mapping server IPs to provider names.

### `DNSResult`

Data class containing the results of DNS latency tests.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `server` | `str` | DNS server IP address |
| `provider` | `str` | DNS provider name |
| `latency` | `float` | Last measured latency (ms) |
| `avg_latency` | `float` | Average latency across all tests (ms) |
| `status` | `str` | Human-readable status string |
| `last_updated` | `datetime` | Timestamp of last update |
| `ping_count` | `int` | Number of successful tests |
| `successful_methods` | `Set[TestMethod]` | Set of successful test methods |

#### Example

```python
result = scanner.results["1.1.1.1"]
print(f"Server: {result.server}")
print(f"Provider: {result.provider}")
print(f"Average Latency: {result.avg_latency}ms")
print(f"Status: {result.status}")
print(f"Success Rate: {result.ping_count}/{config.ping_count}")
```

## 🔧 Enums and Constants

### `TestMethod`

Enumeration of available test methods.

```python
from dnsping.models import TestMethod

print(TestMethod.DNS_QUERY)      # DNS query test
print(TestMethod.SOCKET_CONNECT) # Socket connection test
print(TestMethod.PING)           # ICMP ping test
```

### `LatencyLevel`

Performance thresholds for latency classification.

```python
from dnsping.models import LatencyLevel

print(LatencyLevel.EXCELLENT)  # < 20ms
print(LatencyLevel.GOOD)       # < 50ms
print(LatencyLevel.FAIR)       # < 100ms
print(LatencyLevel.POOR)       # > 100ms
```

## 🎯 Advanced Usage

### Custom Test Configuration

```python
from dnsping import ScanConfig, DNSLatencyScanner

# Configure for high accuracy
config = ScanConfig(
    max_servers=10,
    ping_count=10,
    timeout=3.0,
    enable_dns_query=True,
    enable_socket=True,
    enable_ping=True
)

scanner = DNSLatencyScanner(config)
await scanner.run()

# Get top 3 performers
top_servers = sorted(
    scanner.results.values(),
    key=lambda r: r.avg_latency if r.avg_latency != float('inf') else 999999
)[:3]

for result in top_servers:
    print(f"{result.server} ({result.provider}): {result.avg_latency}ms")
```

### Real-time Monitoring

```python
import asyncio
from dnsping import ScanConfig, DNSLatencyScanner

async def monitor_dns():
    config = ScanConfig(max_servers=20, ping_count=2)
    scanner = DNSLatencyScanner(config)

    # Custom monitoring loop
    while True:
        await scanner.run()
        best_result = min(
            scanner.results.values(),
            key=lambda r: r.avg_latency if r.avg_latency != float('inf') else 999999
        )

        print(f"Best DNS: {best_result.server} - {best_result.avg_latency}ms")
        await asyncio.sleep(300)  # Check every 5 minutes

asyncio.run(monitor_dns())
```

### Error Handling

```python
from dnsping import ScanConfig, DNSLatencyScanner, DNSException

try:
    config = ScanConfig(dns_file=Path("nonexistent.txt"))
    scanner = DNSLatencyScanner(config)
    await scanner.run()

except DNSException as e:
    print(f"DNS Error: {e}")
except FileNotFoundError as e:
    print(f"Configuration file not found: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## 📊 Result Analysis

### Filtering Results

```python
# Get only successful results
successful = {
    server: result
    for server, result in scanner.results.items()
    if result.avg_latency != float('inf')
}

# Get results by provider
by_provider = {}
for server, result in scanner.results.items():
    provider = result.provider
    if provider not in by_provider:
        by_provider[provider] = []
    by_provider[provider].append(result)

# Find fastest server per provider
fastest_per_provider = {}
for provider, results in by_provider.items():
    if results:
        fastest = min(results, key=lambda r: r.avg_latency)
        fastest_per_provider[provider] = fastest
```

### Performance Statistics

```python
import statistics

latencies = [
    result.avg_latency
    for result in scanner.results.values()
    if result.avg_latency != float('inf')
]

if latencies:
    print(f"Average latency: {statistics.mean(latencies):.1f}ms")
    print(f"Median latency: {statistics.median(latencies):.1f}ms")
    print(f"Min latency: {min(latencies):.1f}ms")
    print(f"Max latency: {max(latencies):.1f}ms")
```

## 🔌 Integration Examples

### Flask Web Application

```python
from flask import Flask, jsonify
from dnsping import ScanConfig, DNSLatencyScanner
import asyncio

app = Flask(__name__)

@app.route('/dns-test')
def dns_test():
    # Run scan in thread pool
    config = ScanConfig(max_servers=10, ping_count=2)
    scanner = DNSLatencyScanner(config)

    # Note: In real Flask app, use proper async handling
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(scanner.run())

    results = {
        server: {
            'latency': result.avg_latency,
            'provider': result.provider,
            'status': result.status
        }
        for server, result in scanner.results.items()
    }

    return jsonify(results)

if __name__ == '__main__':
    app.run()
```

### Command-Line Tool with Custom Output

```python
#!/usr/bin/env python3

import argparse
import json
import csv
from pathlib import Path
from dnsping import ScanConfig, DNSLatencyScanner
import asyncio

async def main():
    parser = argparse.ArgumentParser(description='DNS Latency Tester')
    parser.add_argument('--format', choices=['json', 'csv', 'text'],
                       default='text', help='Output format')
    parser.add_argument('--output', type=Path,
                       help='Output file (default: stdout)')

    args = parser.parse_args()

    config = ScanConfig(max_servers=20)
    scanner = DNSLatencyScanner(config)
    await scanner.run()

    # Prepare results
    results = []
    for server, result in scanner.results.items():
        results.append({
            'server': server,
            'provider': result.provider,
            'latency': result.avg_latency if result.avg_latency != float('inf') else None,
            'status': result.status,
            'success_rate': f"{result.ping_count}/{config.ping_count}"
        })

    # Sort by latency
    results.sort(key=lambda x: x['latency'] if x['latency'] else 999999)

    # Output based on format
    if args.format == 'json':
        output = json.dumps(results, indent=2)
    elif args.format == 'csv':
        if results:
            output = []
            writer = csv.DictWriter(output, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
            output = '\n'.join(output)
    else:  # text
        output = "DNS Latency Test Results\n"
        output += "=" * 50 + "\n"
        for result in results[:10]:  # Top 10
            latency = f"{result['latency']:.1f}ms" if result['latency'] else "Failed"
            output += f"{result['server']} ({result['provider']}): {latency}\n"

    if args.output:
        args.output.write_text(output)
    else:
        print(output)

if __name__ == '__main__':
    asyncio.run(main())
```

## 🆘 Exception Handling

### Custom Exceptions

```python
from dnsping import DNSException, ConfigurationError, NetworkError

try:
    # DNS operations
    pass
except ConfigurationError:
    # Configuration file issues
    print("Configuration error")
except NetworkError:
    # Network connectivity issues
    print("Network error")
except DNSException:
    # General DNS issues
    print("DNS error")
```

## 📖 Type Hints

The library includes comprehensive type hints for better IDE support:

```python
from typing import Dict, List, Optional, Set
from pathlib import Path
from dnsping import DNSLatencyScanner, ScanConfig, DNSResult

def analyze_results(results: Dict[str, DNSResult]) -> List[str]:
    """Analyze DNS results and return recommendations."""
    # Function implementation
    pass
```

## 🔄 Async/Await Support

All major operations are async for high performance:

```python
import asyncio
from dnsping import DNSLatencyScanner, ScanConfig

async def batch_test_configs():
    configs = [
        ScanConfig(max_servers=10, enable_ping=False),
        ScanConfig(max_servers=20, enable_dns_query=False),
        ScanConfig(max_servers=30, enable_socket=False),
    ]

    for config in configs:
        scanner = DNSLatencyScanner(config)
        await scanner.run()

        # Process results
        best = min(scanner.results.values(),
                  key=lambda r: r.avg_latency if r.avg_latency != float('inf') else 999999)
        print(f"Config result: {best.server} - {best.avg_latency}ms")

asyncio.run(batch_test_configs())
```

## 📚 Additional Resources

- **Source Code**: [GitHub Repository](https://github.com/milad-hub/dnsping)
- **Issues**: [Report Bugs](https://github.com/milad-hub/dnsping/issues)
- **Discussions**: [Community Support](https://github.com/milad-hub/dnsping/discussions)
- **Documentation**: [Full Docs](https://github.com/milad-hub/dnsping/tree/main/docs)
