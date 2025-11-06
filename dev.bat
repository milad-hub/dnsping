@echo off
REM Development helper script for dnsping (like npm scripts)

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else if exist venv\bin\activate (
    call venv\bin\activate
)

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="install" goto install
if "%1"=="install-dev" goto install-dev
if "%1"=="test" goto test
if "%1"=="test-cov" goto test-cov
if "%1"=="lint" goto lint
if "%1"=="format" goto format
if "%1"=="clean" goto clean
if "%1"=="run" goto run
goto help

:help
echo.
echo Available commands:
echo   dev help         - Show this help message
echo   dev install      - Install runtime dependencies
echo   dev install-dev  - Install development dependencies
echo   dev test         - Run tests
echo   dev test-cov     - Run tests with coverage report
echo   dev lint         - Run linters (flake8, pylint, mypy)
echo   dev format       - Format code (black, isort)
echo   dev clean        - Clean build artifacts
echo   dev run          - Run the application
echo.
goto end

:install
echo Installing runtime dependencies...
pip install -r requirements.txt
echo Done!
goto end

:install-dev
echo Installing development dependencies...
pip install -r requirements-dev.txt
pip install -e .
echo Done! You can now run: dnsping
goto end

:test
echo Running tests...
pytest tests\ -v
goto end

:test-cov
echo Running tests with coverage...
pytest tests\ -v --cov=dnsping --cov-report=html --cov-report=term
echo Coverage report saved to htmlcov\index.html
goto end

:lint
echo Running linters...
flake8 src\dnsping
pylint src\dnsping
mypy src\dnsping
goto end

:format
echo Formatting code...
black src\dnsping tests
isort src\dnsping tests
echo Code formatted!
goto end

:clean
echo Cleaning build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.egg-info rmdir /s /q *.egg-info
if exist .pytest_cache rmdir /s /q .pytest_cache
if exist .coverage del .coverage
if exist htmlcov rmdir /s /q htmlcov
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
echo Cleaned!
goto end

:run
echo Running dnsping...
python -m dnsping
goto end

:end
