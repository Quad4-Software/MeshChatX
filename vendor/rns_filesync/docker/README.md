# Docker images for RNS FileSync

Rootless multi-stage runtime and a separate wheel builder.

## Runtime image (rootless)

Build:

```bash
docker build -f docker/Dockerfile -t rns-filesync:1.0.0 .
```

Prepare host dirs owned by uid 1000:

```bash
mkdir -p ./fs-config ./fs-data ./fs-reticulum
```

Put FileSync config under ./fs-config (config file named config),
Reticulum config under ./fs-reticulum, and the sync tree under ./fs-data.

Run (rootless-friendly, drop capabilities):

```bash
docker run --rm -d \
  --name rns-filesync \
  --user=1000:1000 \
  --read-only \
  --tmpfs /tmp:rw,size=64m \
  --security-opt no-new-privileges \
  --cap-drop ALL \
  -v "$PWD/fs-config:/config:rw" \
  -v "$PWD/fs-data:/data:rw" \
  -v "$PWD/fs-reticulum:/reticulum:rw" \
  rns-filesync:1.0.0
```

Override peers or flags:

```bash
docker run --rm --user=1000:1000 \
  -v "$PWD/fs-config:/config" \
  -v "$PWD/fs-data:/data" \
  -v "$PWD/fs-reticulum:/reticulum" \
  rns-filesync:1.0.0 \
  --config /config --rnsconfig /reticulum -d /data --no-repl -p PEER_HASH
```

Check version:

```bash
docker run --rm rns-filesync:1.0.0 -v
```

## Wheel builder

Build wheels inside the image and copy them out:

```bash
mkdir -p dist
docker build -f docker/Dockerfile.build -t rns-filesync-build .
docker run --rm -v "$PWD/dist:/output" rns-filesync-build \
  sh -c 'cp -a /output/. /output/ 2>/dev/null; ls -la /output'
```

If the image already wrote wheels under /output during build, extract with:

```bash
cid=$(docker create rns-filesync-build)
docker cp "$cid":/output/. ./dist/
docker rm "$cid"
```

Install a built wheel:

```bash
pipx install dist/rns_filesync-*.whl
```

## Notes

- The runtime user is filesync (uid 1000). Match host volume ownership.
- Network is required for Reticulum interfaces you enable in /reticulum/config.
- Prefer --no-repl for containers and service managers.
