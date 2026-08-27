"""Put the conformance kit (run.py) on sys.path so tests can import it."""

import sys
from pathlib import Path

CONFORMANCE_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = CONFORMANCE_DIR / "fixtures"

if str(CONFORMANCE_DIR) not in sys.path:
    sys.path.insert(0, str(CONFORMANCE_DIR))
