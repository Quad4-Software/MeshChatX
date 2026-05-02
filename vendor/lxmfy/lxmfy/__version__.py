import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

try:
    __version__ = version("lxmfy")
except PackageNotFoundError:
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                pyproject = tomllib.load(f)
            __version__ = pyproject["project"]["version"]
        else:
            __version__ = "1.6.2"
    except Exception:
        __version__ = "1.6.2"
