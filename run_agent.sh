#!/bin/bash

# Autonomous Dev Agent Runner
# This script is designed to be run by cron

# Set up logging
LOG_DIR="/opt/autonomous-dev-agent/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/agent_$(date +%Y%m%d_%H%M%S).log"

echo "========================================" | tee -a "$LOG_FILE"
echo "Autonomous Dev Agent Run" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Configuration
AGENT_DIR="/opt/autonomous-dev-agent"
# Use first argument as config file, or default to family_run.yaml
CONFIG_FILE="${1:-$AGENT_DIR/config/family_run.yaml}"
PYTHON_BIN="$AGENT_DIR/venv/bin/python"

# Load API key from environment file if it exists
if [ -f "$AGENT_DIR/.env" ]; then
    export $(grep -v '^#' "$AGENT_DIR/.env" | xargs)
fi

# Change to agent directory
cd "$AGENT_DIR" || exit 1

# Run the orchestrator
echo "Executing orchestrator..." | tee -a "$LOG_FILE"
$PYTHON_BIN "$AGENT_DIR/agent/orchestrator.py" "$CONFIG_FILE" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=$?

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Completed: $(date)" | tee -a "$LOG_FILE"
echo "Exit code: $EXIT_CODE" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Keep only last 30 log files
find "$LOG_DIR" -name "agent_*.log" -type f | sort -r | tail -n +31 | xargs -r rm

exit $EXIT_CODE
