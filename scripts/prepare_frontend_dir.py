import shutil
from pathlib import Path

TARGET = Path("meshchatx") / "public"

if not Path("pyproject.toml").exists():
    msg = "Must run from project root"
    raise RuntimeError(msg)

if TARGET.exists():
    if TARGET.is_symlink():
        msg = f"{TARGET} is a symlink, refusing to remove"
        raise RuntimeError(msg)
    shutil.rmtree(TARGET)

TARGET.mkdir(parents=True, exist_ok=True)
