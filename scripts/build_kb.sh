#!/usr/bin/env bash
# Rebuild the ALERTE knowledge base (phase 1) from the documents listed in knowledge/manifest.csv.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY -W ignore -m alerte.kb.extract   # uses knowledge/ocr/ for scanned documents
$PY -m alerte.kb.chunk
$PY -m alerte.kb.index build
$PY -m alerte.kb.check_quotes
