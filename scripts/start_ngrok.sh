#!/usr/bin/env bash
set -euo pipefail

# Install: brew install ngrok/ngrok/ngrok
# One-time: ngrok config add-authtoken <YOUR_TOKEN>

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Starting ngrok for FastAPI tunnel on port 9000"
ngrok http 9000
