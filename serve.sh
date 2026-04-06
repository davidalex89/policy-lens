#!/usr/bin/env bash
# Serve policy-lens UI at http://localhost:8080
# Required because browsers send Origin: null for file:// pages, which Ollama blocks.
PORT=${1:-8080}
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "Serving policy-lens at http://localhost:${PORT}"
echo "Press Ctrl+C to stop."
open "http://localhost:${PORT}" 2>/dev/null || true
python3 -m http.server "$PORT" --directory "$ROOT"
