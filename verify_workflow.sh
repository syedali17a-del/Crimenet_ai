#!/usr/bin/env bash
# Thin shim: the canonical verification script lives at backend/verify_workflow.sh
exec bash "$(dirname "$0")/backend/verify_workflow.sh" "$@"
