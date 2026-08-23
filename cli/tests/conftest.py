"""Make `model_ledger` importable when pytest runs from the repo root (CI)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # cli/