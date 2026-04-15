"""Move Poetry-built wheels from ``dist/`` into ``python-dist/``.

Avoids filename clashes with Electron build outputs.
"""

import shutil
from pathlib import Path

dist = Path("dist")
target = Path("python-dist")
target.mkdir(parents=True, exist_ok=True)

for wheel in dist.glob("*.whl"):
    shutil.move(str(wheel), target / wheel.name)
