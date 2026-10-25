#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../slack-bridge"
python3 -m unittest -q test_bridge test_doctor test_mission_hub
