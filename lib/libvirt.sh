#!/bin/bash

VM_STATE_TOOL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/vm_state.py"

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
