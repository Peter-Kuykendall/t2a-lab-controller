#!/bin/bash

log_action() {
    local message="$1"
    local logfile="$(dirname "$0")/../logs/t2a-lab-controller.log"

    mkdir -p "$(dirname "$logfile")"

    printf '%s %s\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" \
        "$message" >> "$logfile"
}
