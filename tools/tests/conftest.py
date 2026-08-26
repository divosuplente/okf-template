import sys
from pathlib import Path

# Make tools/okf.py importable as `okf` from the tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
