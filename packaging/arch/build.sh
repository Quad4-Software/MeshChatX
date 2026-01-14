#!/bin/bash
set -e

# Fix permissions for the mounted volume
sudo chown -R build:build /home/build/project

# Navigate to the build directory
cd /home/build/project

# Run makepkg as the build user
sudo -u build makepkg -s --noconfirm

