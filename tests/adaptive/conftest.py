"""pytest configuration for adaptive tests"""
import sys
from pathlib import Path

# Add repository root to path so adaptive module can be imported
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))
