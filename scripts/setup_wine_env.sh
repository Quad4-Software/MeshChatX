#!/bin/bash
set -e

# Wine Environment Setup Script
# This script prepares a Wine prefix with Python and Git for Windows

export WINEDEBUG=-all
export WINEARCH=win64
export WINEPREFIX=${WINEPREFIX:-$HOME/.wine}

PYTHON_VERSION="3.13.1"
PYTHON_EXE="python-${PYTHON_VERSION}-amd64.exe"
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_EXE}"

GIT_VERSION="2.52.0"
GIT_EXE="Git-${GIT_VERSION}-64-bit.exe"
GIT_URL="https://github.com/git-for-windows/git/releases/download/v${GIT_VERSION}.windows.1/${GIT_EXE}"

echo "Downloading Windows Python and Git..."
wget -q "$PYTHON_URL"
wget -q "$GIT_URL"

chmod +x *.exe

echo "Initializing Wine prefix in $WINEPREFIX..."
xvfb-run wine wineboot --init

echo "Installing Python $PYTHON_VERSION into Wine..."
xvfb-run wine "./$PYTHON_EXE" /quiet InstallAllUsers=1 TargetDir=C:\\Python313 PrependPath=1

echo "Installing Git into Wine..."
xvfb-run wine "./$GIT_EXE" /VERYSILENT /NORESTART

echo "Installing build dependencies in Wine Python..."
xvfb-run wine C:/Python313/python.exe -m pip install --upgrade pip
xvfb-run wine C:/Python313/python.exe -m pip install cx_Freeze poetry
if [ -f "requirements.txt" ]; then
    xvfb-run wine C:/Python313/python.exe -m pip install -r requirements.txt
fi

# Clean up installers
rm "$PYTHON_EXE" "$GIT_EXE"
