#!/bin/bash
# Generate SHA256 checksums for release assets
# Usage: ./scripts/gen_checksums.sh [directory]

TARGET_DIR=${1:-"./dist"}

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory $TARGET_DIR does not exist."
    exit 1
fi

echo "Generating SHA256SUMS for assets in $TARGET_DIR..."
cd "$TARGET_DIR" || exit 1

# Exclude existing SHA256SUMS file if it exists
find . -maxdepth 1 -type f ! -name "SHA256SUMS" -exec sha256sum {} + > SHA256SUMS

echo "Done. SHA256SUMS created in $TARGET_DIR"
cat SHA256SUMS

