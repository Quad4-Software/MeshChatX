#!/bin/sh
# Install Trivy .deb for CI (same package as scan / docker workflows).
set -eu

curl -fsSL -o /tmp/trivy.deb https://git.quad4.io/Quad4-Software/Trivy-Assets/raw/commit/fdfe96b77d2f7b7f5a90cea00af5024c9f728f17/trivy_0.69.3_Linux-64bit.deb
sh scripts/ci/exec-priv.sh dpkg -i /tmp/trivy.deb || sh scripts/ci/exec-priv.sh apt-get install -f -y
trivy --version
