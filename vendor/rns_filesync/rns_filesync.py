#!/usr/bin/env python3
"""Compatibility shim for python rns_filesync.py."""

from rns_filesync.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
