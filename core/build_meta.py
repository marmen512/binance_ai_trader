"""
Build Meta - побудова мета-двигуна з усіма доступними двигунами.
"""
from core.ensemble_engine import EnsembleEngine
from core.regime_model_engine import RegimeModelEngine
from core.adaptive_engine import AdaptiveEngine
from core.meta_engine import MetaEngine


def build_meta_engine():
    """
    Створює MetaEngine з усіма доступними двигунами.
    
    Returns:
        MetaEngine: мета-двигун з ensemble, regime та adaptive двигунами
    """
    engines = {}
    
    # Спробуємо додати кожен двигун
    try:
        engines['ensemble'] = EnsembleEngine()
        print("✅ EnsembleEngine додано")
    except Exception as e:
        print(f"⚠️ Не вдалось завантажити EnsembleEngine: {e}")
    
    try:
        engines['regime'] = RegimeModelEngine()
        print("✅ RegimeModelEngine додано")
    except Exception as e:
        print(f"⚠️ Не вдалось завантажити RegimeModelEngine: {e}")
    
    try:
        engines['adaptive'] = AdaptiveEngine()
        print("✅ AdaptiveEngine додано")
    except Exception as e:
        print(f"⚠️ Не вдалось завантажити AdaptiveEngine: {e}")
    
    if not engines:
        raise ValueError("Не вдалось завантажити жодного двигуна!")
    
    print(f"\nСтворено MetaEngine з {len(engines)} двигунами")
    return MetaEngine(engines)


if __name__ == '__main__':
    meta = build_meta_engine()
    print(f"Активні двигуни: {list(meta.engines.keys())}")
