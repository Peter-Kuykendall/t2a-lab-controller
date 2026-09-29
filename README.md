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
3. `t2a-vm apply NAME` — perform an approved plan

Read-only inspection and planning come before mutation. Destructive actions will be guarded explicitly.

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

The first reconciliation test is successful: `t2a-vm plan t2a-sandbox` reports `No changes required.` against the existing VM. The next milestone is to add declarative definitions for the Builder and Deploy-Test VMs before any creation/apply logic is enabled.
