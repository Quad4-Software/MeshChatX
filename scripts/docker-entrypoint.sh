#!/bin/sh
set -e

# OCI runtimes (Kubernetes command/args, docker run image --flag) replace the
# image CMD, so argv can start with a flag instead of a program path. Prepend
# the server command so flag-style argv still reaches meshchatx.
if [ $# -eq 0 ] || [ "${1#-}" != "$1" ]; then
    set -- meshchatx "$@"
fi

if [ "$(id -u)" -eq 0 ]; then
    chown -R meshchat:meshchat /config
    exec su-exec meshchat "$@"
fi
exec "$@"
