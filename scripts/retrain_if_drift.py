"""
Script to trigger retraining when drift is detected.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from training.adaptive_retrain import train_adaptive_model


if __name__ == '__main__':
    print("[RetainIfDrift] Triggering adaptive retraining...")
    train_adaptive_model()
    print("[RetainIfDrift] Retraining complete")
