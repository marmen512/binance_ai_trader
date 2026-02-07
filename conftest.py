"""pytest configuration for binance_ai_trader tests"""
import sys
from pathlib import Path

# Ensure repository root is in Python path
repo_root = Path(__file__).parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
