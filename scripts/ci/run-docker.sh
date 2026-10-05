#!/usr/bin/env bash
# Run portable CI inside the CI container (podman or docker).
set -euo pipefail

. "$(dirname "$0")/env.sh"

job="${1:-pr}"
image="${CI_DOCKER_IMAGE:-meshchatx-ci:local}"

container="${CI_CONTAINER:-}"
if [ -z "$container" ]; then
	if command -v podman >/dev/null 2>&1; then
		container=podman
	elif command -v docker >/dev/null 2>&1; then
		container=docker
	else
		echo "run-docker.sh: need podman or docker on PATH (or set CI_CONTAINER)" >&2
		exit 1
	fi
fi

ignorefile="${CI_DOCKER_IGNOREFILE:-$ROOT/scripts/ci/ci.dockerignore}"

GOFLAGS= "$container" build --ignorefile "$ignorefile" -f "$ROOT/scripts/ci/Dockerfile.ci" -t "$image" "$ROOT"

git_mount=()
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	git_common="$(git -C "$ROOT" rev-parse --git-common-dir)"
	case "$git_common" in
	/*) ;;
	*) git_common="$ROOT/$git_common" ;;
	esac
	git_mount=(-v "${git_common}:/src/.git:ro,Z")
fi

exec "$container" run --rm \
	"${git_mount[@]}" \
	-e CI_SKIP_TREE_VERIFY="${CI_SKIP_TREE_VERIFY:-1}" \
	-e CI_SKIP_BOOTSTRAP=1 \
	-e CI_SKIP_SETUP=1 \
	-e RNS_INVENTORY_OUT="${RNS_INVENTORY_OUT:-}" \
	"$image" \
	bash scripts/ci/run.sh "$job"
