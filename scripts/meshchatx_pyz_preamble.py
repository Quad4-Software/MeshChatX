import argparse
import os
import sys

archive = globals().get("archive") or (
    sys.argv[0] if sys.argv and not sys.argv[0].startswith("-") else ""
)
site_packages = globals().get("site_packages")

# runpy.run_path made argv[0] this preamble; the original PYZ args are in argv[1:].
# Restore the PYZ as argv[0] so argparse and child-process launchers see the right name.
sys.argv = [archive, *sys.argv[1:]]

if not getattr(sys, "frozen", False):
    sys.frozen = True

if archive and not archive.startswith("-"):
    sys.executable = os.path.abspath(archive)

# Python 3.14+ argparse defaults to "python <script>" for zip file __main__ specs.
# Force it to use only the PYZ basename so help output is clean.


def _patched_prog_name(prog=None):
    if prog is not None:
        return prog
    return os.path.basename(sys.argv[0])


argparse._prog_name = _patched_prog_name

# Point the web server at the bundled frontend assets inside the shiv cache.
if site_packages:
    public_dir = os.path.join(site_packages, "meshchatx", "public")
    os.environ.setdefault("MESHCHAT_PUBLIC_DIR", public_dir)
