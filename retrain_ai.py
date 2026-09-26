"""
Retrain the mood classifier on your own feedback corrections only.

Equivalent to `python train_ai.py --labeled-only`; this is the same data
selection the app uses for its automatic retraining.
"""
import sys

import train_ai

if __name__ == "__main__":
    sys.exit(train_ai.main(["--labeled-only", *sys.argv[1:]]))
