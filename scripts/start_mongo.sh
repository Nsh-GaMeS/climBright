#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DBPATH="$ROOT_DIR/db/mongo"
PORT="${1:-27017}"

mkdir -p "$DBPATH"

echo "Starting mongod with dbpath: $DBPATH"

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "mongod already appears to be running on port $PORT."
  echo "If you want to use this script-managed instance instead, stop the existing one first (e.g. 'brew services stop mongodb-community@7.0')."
  exit 0
fi

echo "If mongod isn't installed: brew install mongodb-community@7.0"

mongod \
  --dbpath "$DBPATH" \
  --bind_ip 127.0.0.1 \
  --port "$PORT"
