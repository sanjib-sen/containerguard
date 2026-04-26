#!/usr/bin/env bash
# Seeds a baseline set of alert + compliance rules for demo purposes.
# Idempotent — skips rules that already exist by name.

BASE="${BASE:-http://localhost:8002}" python3 "$(dirname "$0")/seed-rules.py"
