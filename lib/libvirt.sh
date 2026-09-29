#!/bin/bash

VM_STATE_TOOL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/vm_state.py"
VM_OPS_TOOL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/vm_ops.py"

list_vms() {
    virsh list --all
}

inspect_vm() {
    local name="$1"
    python3 "$VM_STATE_TOOL" inspect "$name"
}

plan_vm() {
    local name="$1"
    local definition="$2"
    python3 "$VM_STATE_TOOL" plan "$name" "$definition"
}

apply_vm() {
    local name="$1"
    local definition="$2"
    python3 "$VM_STATE_TOOL" apply "$name" "$definition"
}

prepare_install_vm() {
    python3 "$VM_OPS_TOOL" prepare-install "$1" "$2"
}

start_vm() {
    python3 "$VM_OPS_TOOL" start "$1"
}

shutdown_vm() {
    python3 "$VM_OPS_TOOL" shutdown "$1"
}

force_stop_vm() {
    python3 "$VM_OPS_TOOL" force-stop "$1"
}

snapshot_create_vm() {
    python3 "$VM_OPS_TOOL" snapshot-create "$1" "$2"
}

snapshot_revert_vm() {
    python3 "$VM_OPS_TOOL" snapshot-revert "$1" "$2"
}

snapshot_list_vm() {
    python3 "$VM_OPS_TOOL" snapshot-list "$1"
}

capture_screen_vm() {
    python3 "$VM_OPS_TOOL" capture-screen "$1" "$2"
}
