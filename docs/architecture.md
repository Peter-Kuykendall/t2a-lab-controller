# T2A Lab Controller Architecture

## Purpose

The T2A Lab Controller manages the Tech To All virtualization lab. It is intentionally separate from `t2a-provisioning`.

`t2a-provisioning` owns deployment logic and artifacts. `t2a-lab-controller` owns the engineering environment used to build, test, snapshot, and regress those artifacts.

## Architectural intent

The controller follows a declarative model.

- **Desired state** is stored in human-readable VM definition files.
- **Actual state** is read from libvirt.
- **Plan** compares desired with actual and reports required changes.
- **Apply** executes an approved plan through small, focused tools.

This is analogous to commander's intent: the desired outcome and constraints are explicit, while implementation details remain inside the controller.

## Control flow

```text
Git
 |
 v
vm-definitions/*.yaml
 |
 v
t2a-lab-controller
 |
 +--> inspect actual state
 +--> compare desired vs actual
 +--> produce plan
 +--> apply approved changes
 |
 v
libvirt
 |
 v
QEMU/KVM virtual machines
```

The AI/MCP layer is deliberately not the system of record. It is another interface to the controller.

```text
ChatGPT / MCP
      |
      v
t2a-lab-controller
      |
      v
libvirt
```

## Host baseline

Current lab host observations:

- Hostname: `t2a-lab`
- Ubuntu 24.04-based host
- libvirt 10.0.0
- QEMU 8.2.2
- 16 GiB physical RAM installed and online
- Linux reports 16,244,240 kB MemTotal (about 15.5 GiB usable)
- default libvirt NAT network active
- default storage pool at `/var/lib/libvirt/images`
- default pool capacity approximately 232 GiB
- approximately 213 GiB free at initial inspection

The host has a single approximately 256 GB physical drive, so virtual disks should be sized conservatively.

## Storage policy

qcow2 is the default virtual-disk format.

VM definitions express virtual capacity and intent, not host file paths. Thin provisioning is preferred so a 30 GiB virtual disk consumes host space only as blocks are written.

A 30 GiB virtual disk is the current default assumption for lab VMs unless a specific workload requires more.

## Existing VM adoption

The initial validation resource is `t2a-sandbox`, created before this controller project.

Observed state:

- 2 vCPUs
- 2048 MB RAM
- 30 GiB qcow2 disk
- storage pool `default`
- discard/unmap enabled
- libvirt network `default`

Its desired state is recorded in:

`vm-definitions/t2a-sandbox.yaml`

The first reconciliation test should report no differences. This allows the controller's inspect/plan logic to be validated against an existing known-good VM before any creation logic is enabled.

## Safety principles

- Observe before modifying.
- Separate desired state from observed state.
- Plan before apply.
- Keep configuration in declarative files instead of burying parameters in scripts.
- Prefer small composable tools over monolithic scripts.
- Log controller actions.
- Add destructive operations only with explicit guardrails.
- Keep privileged operations narrow; normal controller work should run as the non-root `tech` user whenever possible.

## Planned VM roles

Two primary lab VMs are defined but not yet created:

- `T2A-Builder` — builds and configures Linux Mint golden images. Current definition: 2 vCPUs, 4096 MB RAM, 30 GiB thin qcow2 disk on pool `default`, network `default`.
- `T2A-Deploy-Test` — validates deployment, restore, boot, snapshot, rollback, and regression behavior. Current definition: 2 vCPUs, 4096 MB RAM, 30 GiB thin qcow2 disk on pool `default`, network `default`.

These conservative defaults fit the current 16 GiB host while leaving substantial memory for the host OS and controller. They can be revised from observed workload needs before VM creation.

## Near-term roadmap

1. Keep `t2a-vm list`, `inspect`, and `plan` as read-only commands.
2. Reconcile `t2a-sandbox` and confirm a no-change plan. **Completed.**
3. Add declarative definitions for Builder and Deploy-Test. **Completed.**
4. Extend planning to represent a missing VM as a proposed creation without changing anything. **Completed.**
5. Add `apply` only after creation planning is trustworthy.
6. Add snapshot/rollback operations.
7. Expose stable controller operations through MCP.
