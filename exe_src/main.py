"""EXE 入口。"""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from gidmg.ui.app import run

if __name__ == "__main__":
    sys.exit(run())
