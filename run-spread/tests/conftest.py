"""Test configuration for the run-spread tests."""

import sys
from pathlib import Path

# `run-spread` isn't a valid package name, so make the converter importable directly.
sys.path.insert(0, str(Path(__file__).parent.parent))
