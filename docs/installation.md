# Installation Guide

## 🚀 Quick Installation

### For Windows Users

```bash
# 1. Clone the repository
git clone https://github.com/milad-hub/dnsping.git
cd dnsping

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install the package
pip install -e .

# 4. Verify installation
dnsping --help
```

### For Development

```bash
# Install development dependencies
dev install-dev

# Run tests to verify everything works
dev test

# Run the application
dev run
```

## 📋 Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows 11 (optimized), Windows 10+ (supported)
- **Internet Connection**: Required for DNS testing
- **Administrator Privileges**: Required for DNS configuration changes

## 🛠️ Troubleshooting

### Common Installation Issues

#### "python is not recognized"
- Make sure Python 3.8+ is installed
- Add Python to your PATH environment variable
- Restart your terminal/command prompt

#### "pip is not recognized"
- Python should include pip automatically
- If not, install pip: `python -m ensurepip --upgrade`

#### "Permission denied" when installing
- Make sure you're not running as administrator unless necessary
- Try running in a regular command prompt

#### Virtual environment issues
- Delete the venv folder and recreate: `python -m venv venv`
- Make sure to activate with: `venv\Scripts\activate`

### Testing Installation

After installation, run these commands to verify everything works:

```bash
# Check if dnsping command is available
dnsping --help

# Run a quick test
dnsping -m 5 -p 1

# Check development tools
dev help
```

## 📦 Manual Installation

If you prefer not to use the automated setup:

1. **Download the code**
   - Download ZIP from GitHub
   - Or clone with git

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Verify**
   ```bash
   dnsping --version
   ```

## 🔧 System Requirements

### Minimum Requirements
- Windows 10 (64-bit)
- Python 3.8.0 or higher
- 100 MB free disk space
- 512 MB RAM

### Recommended Requirements
- Windows 11 (64-bit)
- Python 3.10 or higher
- 1 GB free disk space
- 2 GB RAM

## 📱 Supported Platforms

- ✅ **Windows 11** (Optimized)
- ✅ **Windows 10** (Supported)
- ⚠️ **Windows 8.1** (May work, not tested)
- ❌ **Windows 7 and earlier** (Not supported)

## 🆘 Getting Help

If you encounter issues:

1. Check this documentation
2. Run `dnsping --help` for command options
3. Check the [Issues](https://github.com/milad-hub/dnsping/issues) page
4. Create a new issue with your error details
