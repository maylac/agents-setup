#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../slack-bridge"
python3 -m unittest -q test_bridge
