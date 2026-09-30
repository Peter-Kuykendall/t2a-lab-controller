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
- Keep privileged operations narrow; normal controller work should run as the non-root `tech` user whenever possible.
- `apply` requires explicit `--yes` confirmation.
- `apply` is restricted to VM names in `ALLOWED_VMS`.
- Creation refuses to reuse a pre-existing volume.
- Failed creation attempts roll back the newly defined domain and newly created volume.
- Post-create verification must match declared state.
- Existing-VM configuration reconciliation is intentionally disabled; a drifted existing VM is reported but not changed.
- Narrow operational mutations are separate commands: installation-media preparation, power control, and snapshots.
- Normal shutdown allows up to 120 seconds for a graceful guest power-off and never escalates automatically to a force-stop; `force-stop` is a separate command with explicit `--yes`.
- Every mutating controller operation takes an exclusive per-VM lock; overlapping mutation attempts fail without changing the VM.
- Mutating operations also require the current controller-session capability. `session-new` rotates that capability so stale remote shells lose mutation authority while read-only inspection remains available.
- Framebuffer capture is read-only with respect to the VM and provides image evidence for semantic boot-state inspection.

## Lab VM roles

The two primary lab VMs are now defined and created:

- `T2A-Image-Builder` — builds and configures Linux Mint golden images. Observed state: shut off, 2 vCPUs, 4096 MB RAM, 30 GiB thin qcow2 disk on pool `default`, network `default`.
- `T2A-Deploy-Test` — validates deployment, restore, boot, snapshot, rollback, and regression behavior. Observed state: shut off, 2 vCPUs, 4096 MB RAM, 30 GiB thin qcow2 disk on pool `default`, network `default`.

Both were created through `t2a-vm apply NAME --yes` and immediately reconciled to `No changes required.`

`T2A-Image-Builder` has since completed the installation-media/boot validation cycle using the Linux Mint 22.3 MATE ISO. The validation used a pre-change snapshot, attached the ISO, changed boot order to CD-ROM then disk, started the VM, confirmed a SPICE display and graphical framebuffer, then reverted the snapshot. Revert restored the original disk-only configuration and hard-disk boot order.

The Builder has also completed a full Linux Mint 22.3 MATE OEM installation. The installed OEM environment boots to the temporary technician account and exposes `Prepare for shipping to end user`, proving that configuration and lab testing can occur before the recipient creates a permanent account. The known-good recovery point is `oem-installed-baseline-20260928`.

## Near-term roadmap

1. Keep `t2a-vm list`, `inspect`, and `plan` as read-only commands.
2. Reconcile `t2a-sandbox` and confirm a no-change plan. **Completed.**
3. Add declarative definitions for Builder and Deploy-Test. **Completed.**
4. Extend planning to represent a missing VM as a proposed creation without changing anything. **Completed.**
5. Add guarded creation-only `apply`. **Completed.**
6. Validate ISO attachment, graphical console path, boot, snapshots, and rollback. **Completed.**
7. Define policy for any future declarative existing-VM configuration modification before implementing it.
8. Validate OEM installation workflow inside `T2A-Image-Builder`. **Completed.**
9. Validate deployment/regression workflow inside `T2A-Deploy-Test`. **In progress: verified J source is present, qcow2 M working overlay is created, and the standard Clonezilla Rev M runtime is reconstructed and hash-verified. Waiting only for the approved T2A-specific Rev L reference files before J -> M migration.**
10. Expose stable controller operations through MCP.


## Virtual provisioning-stick fixture

The Deploy-Test lab uses an immutable raw J image plus a qcow2 copy-on-write overlay presented as USB storage. This preserves the production migration engine's USB-transport guard while making J -> M experiments disposable and repeatable. See `docs/virtual-provisioning-stick.md`.
