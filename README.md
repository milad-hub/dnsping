# 🚀 DNSPing

High-performance DNS server latency monitoring and ranking tool for Windows.

## ✨ Features

- ⚡ **Async Performance**: Lightning-fast concurrent DNS testing
- 📊 **Real-time Monitoring**: Live progress updates and statistics
- 🎯 **Multiple Test Methods**: DNS queries, socket connections, and ICMP ping
- 🔧 **System Integration**: Automatic DNS configuration for Windows
- 🌐 **100+ DNS Servers**: Comprehensive database of public DNS providers
- 💻 **Windows Optimized**: Designed specifically for Windows 11

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/milad-hub/dnsping.git
cd dnsping

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Usage

```bash
# Run DNS latency scan
dnsping

# Show help
dnsping --help

# Scan specific number of servers
dnsping -m 20

# Use development helper
dev run
```

## 📊 Sample Output

```
🌐 DNS Latency Scanner - Live Results
════════════════════════════════════════════════════════════════════════════════════════
📊 Progress: ████████████████████████████████████████ 100.0% (50/50)
🎯 Success Rate: 45/50 servers • 4 tests each
────────────────────────────────────────────────────────────────────────────────────────
Rank DNS Server       Provider               Latency      Visual       Status
🟢1   1.1.1.1          Cloudflare             12.3ms      ███░░░░░░░  OK (DNS/Socket)
🟢2   1.0.0.1          Cloudflare             15.7ms      ████░░░░░░  OK (DNS/Ping)
🟡3   8.8.8.8          Google Public DNS      28.4ms      ██████░░░░  OK (DNS/Socket)
```

## 🛠️ Development

### Setup Development Environment

```bash
# Install development dependencies
dev install-dev

# Run tests
dev test

# Format code
dev format

# Lint code
dev lint

# Run the application
dev run
```

### Available Commands

```bash
dev help         # Show all available commands
dev install-dev  # Install development dependencies
dev test         # Run tests
dev test-cov     # Run tests with coverage
dev format       # Format code
dev lint         # Run linters
dev clean        # Clean build artifacts
dev run          # Run the application
```

## 📋 Requirements

- Python 3.8 or higher
- Windows 11 (optimized for Windows)
- Internet connection

## 📖 Documentation

- [Installation Guide](docs/installation.md)
- [Usage Guide](docs/usage.md)
- [API Reference](docs/api.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with ❤️ for network performance enthusiasts
- Inspired by the classic `ping` command
- Powered by Python's asyncio for high performance

---

**⭐ Star this repository if you find it useful!**
