"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory for all tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create required subdirectories
        (tmpdir_path / "raw").mkdir(exist_ok=True)
        (tmpdir_path / "processed").mkdir(exist_ok=True)
        (tmpdir_path / "insights").mkdir(exist_ok=True)
        (tmpdir_path / "logs").mkdir(exist_ok=True)
        
        yield tmpdir_path
