"""Shared test fixtures."""

import sys
from pathlib import Path

# Allow unit tests to import modules from /app (src/ in the repo)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
