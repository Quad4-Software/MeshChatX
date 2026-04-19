#!/bin/sh
set -e
if [ "$(id -u)" -eq 0 ]; then
    chown -R meshchat:meshchat /config
    exec su-exec meshchat "$@"
fi
exec "$@"
