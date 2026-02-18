#!/usr/bin/env bash
# Simple load generator for the AI Observability demo API.
# It hits /health, /local-inference, and /stats for a configurable duration.

set -euo pipefail

# ---- Config (override via env or args) ----
DURATION_SECS="${1:-300}"          # default 5 minutes
BASE_URL="${BASE_URL:-http://localhost:8080}"

# Intervals (floats supported by macOS sleep)
HEALTH_INTERVAL="${HEALTH_INTERVAL:-0.5}"  # seconds between /health calls
INFER_INTERVAL="${INFER_INTERVAL:-3}"      # seconds between /local-inference calls
STATS_INTERVAL="${STATS_INTERVAL:-5}"      # seconds between /stats calls

# Payload for local inference (override PROMPT via env)
PROMPT="${PROMPT:-Write a short sentence about observability.}"
MAX_LENGTH="${MAX_LENGTH:-48}"
TEMPERATURE="${TEMPERATURE:-0.7}"
NUM_SEQUENCES="${NUM_SEQUENCES:-1}"

echo "Starting load generator:"
echo "  Duration:     ${DURATION_SECS}s"
echo "  Base URL:     ${BASE_URL}"
echo "  /health:      every ${HEALTH_INTERVAL}s"
echo "  /local-inference: every ${INFER_INTERVAL}s (prompt='${PROMPT}')"
echo "  /stats:       every ${STATS_INTERVAL}s"

end=$((SECONDS + DURATION_SECS))
pids=()

cleanup() {
  echo "\nStopping load generator..."
  for pid in "${pids[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait || true
}
trap cleanup INT TERM

# Loop: /health
(
  while [ $SECONDS -lt $end ]; do
    curl -sS -m 3 "${BASE_URL}/health" >/dev/null || true
    sleep "$HEALTH_INTERVAL"
  done
) & pids+=($!)

# Loop: /local-inference
(
  while [ $SECONDS -lt $end ]; do
    curl -sS -m 30 \
      -H 'Content-Type: application/json' \
      -d "{\"prompt\":\"${PROMPT}\",\"max_length\":${MAX_LENGTH},\"temperature\":${TEMPERATURE},\"num_sequences\":${NUM_SEQUENCES}}" \
      "${BASE_URL}/local-inference" >/dev/null || true
    sleep "$INFER_INTERVAL"
  done
) & pids+=($!)

# Loop: /stats (if present)
(
  while [ $SECONDS -lt $end ]; do
    curl -sS -m 5 "${BASE_URL}/stats" >/dev/null || true
    sleep "$STATS_INTERVAL"
  done
) & pids+=($!)

wait || true
echo "Load generation complete."
