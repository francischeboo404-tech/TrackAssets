import sys
import os

# Ensure the backend directory is on sys.path so `import app` resolves
BASE_DIR = os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
