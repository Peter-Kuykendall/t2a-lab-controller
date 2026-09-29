#!/bin/bash

log_action() {
    local message="$1"
    local lib_dir
    local logfile

    lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    logfile="$lib_dir/../logs/t2a-lab-controller.log"

    mkdir -p "$(dirname "$logfile")"

    printf '%s %s\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" \
        "$message" >> "$logfile"
}
