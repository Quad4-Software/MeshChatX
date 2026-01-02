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

# Copy built assets from root public/ to meshchatx/public/
SOURCE = Path("public")
if SOURCE.exists():
    print(f"Copying assets from {SOURCE} to {TARGET}...")
    for item in SOURCE.iterdir():
        if item.is_dir():
            shutil.copytree(item, TARGET / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, TARGET / item.name)
else:
    print(f"Warning: Source directory {SOURCE} not found!")
