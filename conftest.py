"""Ensure the repo root is importable so `app` resolves in tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
