import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tools import draft_patch; import inspect; print(type(draft_patch)); print(dir(draft_patch))