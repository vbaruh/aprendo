#!/usr/bin/env bash

set -e

if [ -z "$APRENDO_CSV_DIR" ]; then
    echo "Error: APRENDO_CSV_DIR environment variable is not set" >&2
    exit 1
fi

if [ ! -f "$APRENDO_CSV_DIR/translations.csv" ]; then
    echo "Error: Translations file not found at $APRENDO_CSV_DIR/translations.csv" >&2
    exit 1
fi

/home/aprendo/.venv/bin/python -m reflex run \
    --env prod \
    --backend-only \
    $APRENDO_BACKEND_ARGS