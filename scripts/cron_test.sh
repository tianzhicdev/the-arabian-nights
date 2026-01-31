#!/bin/bash
#
# Simple cron test script - logs timestamp every execution
#

LOG_DIR="$HOME/cron_test_logs"
LOG_FILE="$LOG_DIR/cron_test.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log current timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S') - Cron test executed successfully" >> "$LOG_FILE"

# Also log some environment info for debugging
echo "  USER=$USER" >> "$LOG_FILE"
echo "  HOME=$HOME" >> "$LOG_FILE"
echo "  PATH=$PATH" >> "$LOG_FILE"
echo "  PWD=$PWD" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
