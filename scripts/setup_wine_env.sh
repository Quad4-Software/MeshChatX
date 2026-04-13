#!/bin/bash
set -e

# Wine Environment Setup Script
# This script prepares a Wine prefix with Python and Git for Windows

export WINEDEBUG=-all
export WINEARCH=win64
export WINEPREFIX=${WINEPREFIX:-$HOME/.wine}

# Latest Python 3.14.x Windows 64-bit installer (see https://www.python.org/downloads/release/python-3144/)
PYTHON_VERSION="3.14.4"
PYTHON_EXE="python-${PYTHON_VERSION}-amd64.exe"
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_EXE}"

GIT_VERSION="2.52.0"
GIT_EXE="Git-${GIT_VERSION}-64-bit.exe"
GIT_URL="https://github.com/git-for-windows/git/releases/download/v${GIT_VERSION}.windows.1/${GIT_EXE}"

wine_wrap() {
    if command -v xvfb-run >/dev/null 2>&1; then
        WINEDEBUG=-all xvfb-run -a "$@"
    else
        WINEDEBUG=-all "$@"
    fi
}

echo "Downloading Windows Python and Git..."
wget -q "$PYTHON_URL"
wget -q "$GIT_URL"

chmod +x *.exe

echo "Initializing Wine prefix in $WINEPREFIX..."
wine_wrap wine wineboot --init

echo "Installing Python $PYTHON_VERSION into Wine..."
wine_wrap wine "./$PYTHON_EXE" /quiet InstallAllUsers=1 TargetDir=C:\\Python314 PrependPath=1

echo "Installing Git into Wine..."
wine_wrap wine "./$GIT_EXE" /VERYSILENT /NORESTART

echo "Installing build dependencies in Wine Python..."
wine_wrap wine C:/Python314/python.exe -m pip install --upgrade pip
wine_wrap wine C:/Python314/python.exe -m pip install cx_Freeze poetry
if [ -f "requirements.txt" ]; then
    wine_wrap wine C:/Python314/python.exe -m pip install -r requirements.txt
fi

# Clean up installers
rm "$PYTHON_EXE" "$GIT_EXE"
