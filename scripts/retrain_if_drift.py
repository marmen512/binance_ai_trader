"""
retrain_if_drift.py — скрипт для запуску адаптивного перенавчання.
"""

import subprocess
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def retrain_if_drift():
    """Запускає адаптивне перенавчання."""
    print("Запуск адаптивного перенавчання...")
    
    # Викликаємо скрипт adaptive_retrain.py
    result = subprocess.run(
        ['python', 'training/adaptive_retrain.py'],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("Помилки:", result.stderr)
    
    if result.returncode == 0:
        print("Перенавчання успішне!")
    else:
        print("Помилка при перенавчанні")


if __name__ == '__main__':
    retrain_if_drift()
