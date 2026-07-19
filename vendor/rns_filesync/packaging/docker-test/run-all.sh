#!/bin/sh
# Build wheels and run packaging service tests in appropriate OS images.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

IMG_RUNIT="${IMG_RUNIT:-ghcr.io/void-linux/void-glibc-full:20240526R1}"

echo "==> bake wheel"
mkdir -p dist
make wheel
WHEEL="$(ls -1 dist/rns_filesync-*.whl | head -n1)"
test -n "$WHEEL"
echo "wheel=$WHEEL"

run_named() {
  name="$1"
  dockerfile="$2"
  base_hint="$3"
  testscript="$4"
  echo ""
  echo "======== TEST $name ($base_hint) ========"
  docker build -f "packaging/docker-test/$dockerfile" \
    -t "rns-filesync-svc-$name" \
    packaging/docker-test
  docker run --rm \
    -v "$ROOT/packaging:/packaging:ro" \
    -v "$ROOT/packaging/docker-test:/test:ro" \
    -v "$ROOT/dist:/wheels:ro" \
    "rns-filesync-svc-$name" \
    /bin/sh /test/"$testscript"
}

echo ""
echo "======== TEST systemd (debian bookworm + systemd) ========"
docker build -f packaging/docker-test/Dockerfile.systemd \
  -t rns-filesync-svc-systemd packaging/docker-test

cid="$(docker run -d --privileged --cgroupns=host \
  -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
  -v "$ROOT/packaging:/packaging:ro" \
  -v "$ROOT/packaging/docker-test:/test:ro" \
  -v "$ROOT/dist:/wheels:ro" \
  rns-filesync-svc-systemd)"
cleanup_systemd() {
  docker rm -f "$cid" >/dev/null 2>&1 || true
}
trap cleanup_systemd EXIT
i=0
while [ "$i" -lt 40 ]; do
  if docker exec "$cid" systemctl list-units >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 1
done
docker exec "$cid" /bin/sh /test/test-systemd.sh
cleanup_systemd
trap - EXIT
echo "PASS: systemd outer"

run_named openrc Dockerfile.openrc "alpine:3.21 + openrc" test-openrc.sh
run_named dinit Dockerfile.dinit "debian:bookworm (dinit service file)" test-dinit.sh

echo ""
echo "======== TEST runit ========"
if docker pull "$IMG_RUNIT" >/dev/null 2>&1 \
  && docker build -f packaging/docker-test/Dockerfile.runit \
       -t rns-filesync-svc-runit packaging/docker-test; then
  echo "using Void Linux runit image"
else
  echo "using Alpine runit fallback"
  docker build -f packaging/docker-test/Dockerfile.runit-alpine \
    -t rns-filesync-svc-runit packaging/docker-test
fi
docker run --rm \
  -v "$ROOT/packaging:/packaging:ro" \
  -v "$ROOT/packaging/docker-test:/test:ro" \
  -v "$ROOT/dist:/wheels:ro" \
  rns-filesync-svc-runit \
  /bin/sh /test/test-runit.sh

echo ""
echo "ALL SERVICE TESTS PASSED"
