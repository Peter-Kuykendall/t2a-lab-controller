# T2A Lab Controller

Infrastructure automation for the Tech To All development lab.

Host baseline: Ubuntu 24.04-based system with 16 GiB RAM, approximately 256 GB physical storage, and libvirt/QEMU virtualization.

## Goals

- deterministic VM lifecycle management
- auditable operations
- safe automation
- declarative VM definitions
- future MCP integration

## Design principles

The controller manages **intent, not procedures**. VM definitions describe the desired operational state; small tools inspect reality, plan changes, and apply them through libvirt.

The project follows a UNIX-style model: small programs should do specific jobs well and be composable rather than growing into one large script.

## Safety model

The planned workflow separates observation from modification:

1. `t2a-vm inspect NAME` — report actual state
2. `t2a-vm plan NAME` — compare desired state with actual state
3. `t2a-vm apply NAME --yes` — perform an explicitly confirmed creation plan

Read-only inspection and planning come before mutation. Apply is currently creation-only: it is restricted to names in `ALLOWED_VMS`, requires `--yes`, refuses to reuse a pre-existing storage volume, verifies the created VM against desired state, rolls back a failed creation, and refuses to modify an existing VM that differs from its definition.

## Desired state

Declarative VM definitions live in `vm-definitions/`.

The first adopted VM is `t2a-sandbox`, an existing libvirt VM used to validate the controller against a known-good resource.

Current observed baseline:

- 2 vCPUs
- 2048 MB RAM
- 30 GiB qcow2 disk
- thin-provisioned storage in libvirt pool `default`
- libvirt network `default`

## Repository layout

```text
bin/             user-facing commands
config/          controller configuration
lib/             small reusable controller functions
logs/            local controller logs
vm-definitions/  declarative desired-state files
docs/            architecture and design documentation
```

## Current status

The repository has working read-only `list`, `inspect`, and `plan` commands plus a declarative definition for `t2a-sandbox`.

The first reconciliation test is successful: `t2a-vm plan t2a-sandbox` reports `No changes required.` against the existing VM.

`T2A-Builder` and `T2A-Deploy-Test` have now been created through the controller and post-create verification reports no differences from their declarative definitions. Both are currently shut off. Existing-VM configuration mutation is still intentionally disabled.

`T2A-Builder` now has a verified Linux Mint 22.3 MATE OEM installation baseline. OEM mode boots to a temporary technician environment with `Prepare for shipping to end user`, allowing configuration and testing before the recipient creates a permanent account.

Operational lab commands support guarded installation-media preparation, start, clean shutdown, explicit force-stop, offline snapshot create/list/revert, and standardized framebuffer capture. Mutating operations require `--yes`, remain restricted to `ALLOWED_VMS`, and take an exclusive per-VM lock to prevent overlapping mutations.

`T2A-Deploy-Test` also has a read-only `deploy-preflight` check. It verifies the target VM and inventories available boot media before any deployment mutation is attempted.

A mutation session is opened with `eval "$(./bin/t2a-vm session-new)"`. Opening a new session rotates a local capability token, so stale remote shells can still inspect the lab but can no longer change VM state.
