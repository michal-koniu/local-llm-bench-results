#!/usr/bin/env bash
# run-docker.sh <container-name> <launcher command...>
#
# For launchers that start ONE named container in the foreground themselves (e.g. Radiance's
# serve-tp2.sh): runs the launcher and, when llama-swap stops/swaps the model (SIGTERM), stops and
# removes that container. A leftover container with the same name (after a crash) is removed first.
set -u
name=$1; shift
stop() { docker stop -t 30 "$name" >/dev/null 2>&1; docker rm -f "$name" >/dev/null 2>&1; exit 0; }
trap stop TERM INT
docker rm -f "$name" >/dev/null 2>&1
"$@" &
wait $!
stop
