#!/bin/sh
# Ensure /usr/local/bin (go-task, etc.) is on PATH without shadowing actions/setup-node.
# ARM64 GitHub-hosted images may ship Node 20 in /usr/local/bin; prepending it breaks pnpm 11.
case ":${PATH}:" in
    *:/usr/local/bin:*) ;;
    *) PATH="${PATH}:/usr/local/bin" ;;
esac
export PATH
