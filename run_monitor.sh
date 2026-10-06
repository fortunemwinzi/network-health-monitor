#!/bin/bash
source "$HOME/.monitor_env"
cd "$HOME/network-health-monitor" || exit 1
/usr/bin/python3 monitor.py >> logs/cron.log 2>&1

