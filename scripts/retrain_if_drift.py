"""
Скрипт для запуску адаптивного перенавчання.
"""
import subprocess


def main():
    print("Запуск адаптивного перенавчання...")
    subprocess.run(['python', 'training/adaptive_retrain.py'])


if __name__ == '__main__':
    main()
