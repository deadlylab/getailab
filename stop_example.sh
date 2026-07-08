#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "Stopping example lab..."
pkill -f "scientists/forges/example/" 2>/dev/null || true
pkill -f "LAB_ID=example.*app_oracle" 2>/dev/null || true
pkill -f "LAB_ID=example.*app_lab" 2>/dev/null || true
fuser -k 5124/tcp 5135/tcp 5125/tcp 5126/tcp 2>/dev/null || true
echo "Done."