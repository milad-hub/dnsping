"""
Pytest configuration and fixtures
"""

import asyncio

import pytest

# Set up asyncio for pytest
pytestmark = pytest.mark.asyncio

# Ignore warnings about TestMethod enum being collected as test class
pytest_collection_modifyitems = pytest.hookimpl(tryfirst=True)


def pytest_collection_modifyitems(config, items):
    """Modify test collection to ignore TestMethod enum warnings"""
    # Filter out any items that are actually the TestMethod enum
    items[:] = [item for item in items if not (hasattr(item, "cls") and item.cls and item.cls.__name__ == "TestMethod")]


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
