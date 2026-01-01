#!/bin/bash
set -e

# Find wheel file dynamically
WHEEL_PATTERN="python-dist/reticulum_meshchatx-*-py3-none-any.whl"
WHEEL_FILES=($WHEEL_PATTERN)

if [ ${#WHEEL_FILES[@]} -eq 0 ]; then
    echo "Error: No wheel files found matching pattern: $WHEEL_PATTERN"
    echo "Make sure to run 'poetry build' or similar to create the wheel first."
    exit 1
elif [ ${#WHEEL_FILES[@]} -gt 1 ]; then
    echo "Error: Multiple wheel files found:"
    printf '  %s\n' "${WHEEL_FILES[@]}"
    echo "Please clean up old wheels or specify which one to use."
    exit 1
fi

WHEEL_PATH="${WHEEL_FILES[0]}"

if [ ! -f "$WHEEL_PATH" ]; then
    echo "Error: Wheel not found at $WHEEL_PATH"
    exit 1
fi

echo "Found wheel: $WHEEL_PATH"

echo "Creating test virtual environment..."
TEST_VENV=$(mktemp -d)/test-venv
python3 -m venv "$TEST_VENV"

echo "Installing wheel..."
"$TEST_VENV/bin/pip" install --upgrade pip
"$TEST_VENV/bin/pip" install "$WHEEL_PATH"

echo ""
echo "Checking installation..."
"$TEST_VENV/bin/python" << 'PYTHON_SCRIPT'
import meshchatx.meshchat as meshchat
import os
from pathlib import Path

# Check if meshchat module is importable
print(f'meshchat module location: {meshchat.__file__}')

# Check if public directory exists
meshchat_dir = os.path.dirname(meshchat.__file__)
public_path = os.path.join(meshchat_dir, 'public')
print(f'Checking for public at: {public_path}')
print(f'Exists: {os.path.exists(public_path)}')

# Try get_file_path
from meshchatx.meshchat import get_file_path
test_path = get_file_path('public')
print(f'get_file_path("public"): {test_path}')
print(f'Exists: {os.path.exists(test_path)}')

if os.path.exists(test_path):
    index_html = os.path.join(test_path, 'index.html')
    print(f'index.html exists: {os.path.exists(index_html)}')
else:
    print('WARNING: public directory not found!')
    print('Checking parent directories...')
    current = meshchat_dir
    for i in range(3):
        test = os.path.join(current, 'public')
        print(f'  {test}: {os.path.exists(test)}')
        current = os.path.dirname(current)
PYTHON_SCRIPT

echo ""
echo "Test complete. Virtual environment at: $TEST_VENV"
echo "To test running meshchat: $TEST_VENV/bin/meshchat --help"

