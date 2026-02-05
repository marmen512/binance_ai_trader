"""
build_meta.py — створює MetaEngine з комбінацією движків.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.meta_engine import MetaEngine
from core.ensemble_engine import EnsembleEngine
from core.regime_model_engine import RegimeModelEngine
from core.adaptive_engine import AdaptiveEngine


def build_meta():
    """
    Створює MetaEngine з комбінацією движків.

    Returns:
        MetaEngine: Налаштований мета-движок
    """
    engines = {
        'ensemble': EnsembleEngine(),
        'regime': RegimeModelEngine(),
        'adaptive': AdaptiveEngine()
    }

    return MetaEngine(engines)
