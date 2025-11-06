# Usage Guide

## 🚀 Basic Usage

### Running DNSPing

```bash
# Basic scan (recommended settings)
dnsping

# Quick test with fewer servers
dnsping -m 10

# Comprehensive test
dnsping -m 100 -p 8

# Fast scan (less accurate but quick)
dnsping -t 0.5 -p 2
```

### Command Line Options

```bash
# Show help
dnsping --help

# Common options:
-m, --max-servers     # Maximum servers to test (default: 50)
-p, --pings          # Tests per server (default: 4)
-t, --timeout        # Timeout per test in seconds (default: 1.0)
-w, --workers        # Concurrent workers (default: auto)
```

## 📊 Understanding Results

### Output Format

```
🌐 DNS Latency Scanner - Final Results
══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
📊 Scanned 50 DNS servers • 4 tests per server
🕒 Completed: 2025-01-06 14:30:22
══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
Rank DNS Server       Provider               Latency      Visual       Status               Success
🟢1   1.1.1.1          Cloudflare             12.3ms      ███░░░░░░░  OK (DNS/Socket/Ping) 100%
🟢2   1.0.0.1          Cloudflare             15.7ms      ████░░░░░░  OK (DNS/Socket/Ping) 100%
🟡3   8.8.8.8          Google Public DNS      28.4ms      ██████░░░░  OK (DNS/Socket)      75%
```

### Performance Indicators

| Icon | Latency Range | Description |
|------|---------------|-------------|
| 🟢 | < 20ms | **Excellent** - Premium performance |
| 🟡 | 20-50ms | **Good** - Solid performance |
| 🟠 | 50-100ms | **Fair** - Acceptable performance |
| 🔴 | > 100ms | **Poor** - Slow performance |
| ❌ | Failed | **Unreachable** - Connection failed |

### Status Explanations

- **OK (DNS/Socket/Ping)**: All three test methods succeeded
- **OK (DNS/Socket)**: DNS query and socket connection worked
- **OK (Socket/Ping)**: Socket and ping tests succeeded
- **Failed**: Server is unreachable or unresponsive

## 🔧 Advanced Usage

### Test Method Selection

```bash
# Use only DNS queries (most accurate)
dnsping --no-socket --no-ping

# Use only socket connections
dnsping --no-dns --no-ping

# Use only ping (fastest)
dnsping --no-dns --no-socket
```

### Performance Tuning

```bash
# Maximum performance (resource intensive)
dnsping -m 100 -w 32 -p 8

# Balanced performance
dnsping -m 50 -w 16 -p 4

# Low resource usage
dnsping -m 20 -w 4 -p 2 -t 0.5
```

### Custom DNS File

```bash
# Use custom DNS servers file
dnsping custom_dns.txt

# Combine with other options
dnsping custom_dns.txt -m 20 -p 2
```

## 🔄 DNS Configuration

### Automatic Configuration

After running a scan, DNSPing can automatically configure your Windows DNS settings:

1. **Run the scan**: `dnsping`
2. **Review results**: Find the fastest server (ranked #1)
3. **Choose configuration**: Enter the rank number when prompted
4. **Approve UAC**: Click "Yes" when the User Account Control prompt appears

### Manual Configuration

If automatic configuration fails:

1. **Open Settings** → **Network & Internet** → **Wi-Fi** (or Ethernet)
2. **Click your connection** → **Properties**
3. **Edit IP assignment** → **Manual** → **IPv4 On**
4. **Set DNS servers** to your chosen fast servers

### Recommended Setup

- **Primary DNS**: Your fastest server (rank #1)
- **Secondary DNS**: Another fast server from same provider (rank #2)

## 📈 Performance Tips

### For Best Results

1. **Run during off-peak hours** (avoid network congestion)
2. **Close bandwidth-heavy applications** during testing
3. **Test multiple times** for consistent results
4. **Consider geographic location** of DNS servers

### Interpreting Results

- **Focus on < 50ms servers** for best experience
- **Test both IPv4 and IPv6** if available
- **Monitor performance over time** (DNS performance can change)
- **Consider backup servers** from different providers

## 🧪 Testing Commands

### Development Testing

```bash
# Run tests
dev test

# Run with coverage
dev test-cov

# Run specific test
pytest tests/test_scanner.py::test_specific_function -v
```

### Performance Testing

```bash
# Quick smoke test
dnsping -m 5 -p 1

# Full performance test
dnsping -m 100 -p 8 -w 32

# Network diagnostic
dnsping --no-dns --no-socket  # Pure ping test
```

## 📋 Custom DNS Server Format

Create a custom DNS servers file:

```txt
# My Custom DNS Servers
# Format: One IP address per line
# Comments start with #

# Cloudflare
1.1.1.1
1.0.0.1

# Google
8.8.8.8
8.8.4.4

# Quad9
9.9.9.9
149.112.112.112
```

Save as `my_dns.txt` and run: `dnsping my_dns.txt`

## 🆘 Troubleshooting

### Common Issues

#### "No results found"
- Check internet connection
- Try increasing timeout: `dnsping -t 2.0`
- Reduce concurrent workers: `dnsping -w 4`

#### "Permission denied"
- Run Command Prompt as Administrator
- For DNS configuration, UAC approval is required

#### "Slow performance"
- Reduce server count: `dnsping -m 20`
- Decrease test count: `dnsping -p 2`
- Use faster timeout: `dnsping -t 0.5`

### Debug Mode

```bash
# Enable debug output (when available)
set PYTHONPATH=src
python -m dnsping --debug
```

## 📊 Result Export

Future versions will support exporting results:

```bash
# Export to JSON (planned feature)
dnsping --export json --output results.json

# Export to CSV (planned feature)
dnsping --export csv --output results.csv
```

## 🎯 Use Cases

### For Home Users
- Find fastest DNS for gaming/streaming
- Improve browsing speed
- Test ISP DNS performance

### For Developers
- Benchmark network performance
- Test custom DNS configurations
- Monitor DNS server health

### For System Administrators
- Monitor DNS server performance
- Test failover configurations
- Generate performance reports

## 📞 Support

- **Documentation**: Check this guide first
- **Issues**: [GitHub Issues](https://github.com/milad-hub/dnsping/issues)
- **Discussions**: [GitHub Discussions](https://github.com/milad-hub/dnsping/discussions)
