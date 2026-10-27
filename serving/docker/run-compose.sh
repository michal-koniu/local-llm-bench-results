#!/usr/bin/env bash
# run-compose.sh <file.compose.yml> [VAR=value ...]
#
# Lets llama-swap treat a docker-compose model (e.g. vLLM) like a normal foreground process:
#   - starts the container (VAR=value pairs become compose variables: PORT, NAME, GPUS, TP, ...),
#   - with CHAT_MODEL=<llama-swap id>, also starts front.compose.yml (link in llama-swap -> Open WebUI chat),
#   - streams its log to stdout, so it shows up in llama-swap's log view,
#   - removes the container when llama-swap stops/swaps the model (SIGTERM) or when it dies.
# llama-swap runs as mkoniu, who is in the "docker" group.
set -u
f=$1; shift
for kv in "$@"; do export "$kv"; done
export NAME=${NAME:-$(basename "$f" .compose.yml)}
files=(-f "$f")
if [ -n "${CHAT_MODEL:-}" ]; then          # vLLM: nginx front (front.compose.yml) on PORT, the engine on BPORT
  export BPORT=$((PORT + 10000))
  files+=(-f "$(dirname "$0")/front.compose.yml")
else
  export BPORT=$PORT
fi
dc() { docker compose "${files[@]}" "$@"; }
down() { dc down -t 20 >/dev/null 2>&1; exit 0; }
trap down TERM INT
dc down -t 5 >/dev/null 2>&1          # remove a leftover container from a crash
dc up -d || exit 1
docker logs -f "$NAME" 2>&1 &
wait $!
down
