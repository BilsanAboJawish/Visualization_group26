"""Run with the project's installed Dash; catches incompatible component props at import time.
Usage: python tests/dash_runtime_check.py
"""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from dash import dcc
import app
assert app.app.layout is not None
assert app.app.title.startswith("PlantScope")
# Check the rendered sidebar search input uses props supported by installed Dash.
search = app.sidebar_search()
assert search.id == "plant-search"
print("[PASS] Dash imports and instantiates the complete PlantScope layout")
