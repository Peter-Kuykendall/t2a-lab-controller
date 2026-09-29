# T2A Lab Controller Validation

## 2026-09-28 — VM operational workflow

The first end-to-end operational validation used `T2A-Builder`.

### Installation media

The Linux Mint 22.3 MATE ISO is present in both lab ISO pools. The two copies were verified byte-for-byte by SHA-256:

`7609294da613b75eea89bb918292125e9f06418a368136fb190466e15bf8c373`

The canonical installation intent for `T2A-Builder` uses the `iso` pool volume:

`linuxmint-22.3-mate-64bit.iso`

The controller validates the configured checksum before attaching the ISO.
### Snapshot before mutation

Before changing the VM configuration, the controller created the offline snapshot:

`pre-install-media-20260928`

The VM was shut off when the snapshot was created.

### Media and boot preparation

`t2a-vm prepare-install T2A-Builder --yes` successfully:

- attached the ISO as read-only CD-ROM `sda`
- set boot order to `cdrom, hd`
- re-read libvirt XML and verified both settings

The command is restricted to `ALLOWED_VMS` and requires explicit `--yes`.
### Boot and graphical console path

`t2a-vm start T2A-Builder --yes` started the VM and libvirt reported:

`spice://127.0.0.1:5900`

A libvirt screenshot confirmed an active 1280×800 graphical framebuffer. An early capture contained only two colors; after approximately 50 seconds the framebuffer contained 3,555 unique colors, showing that graphical boot output had progressed substantially.

No unattended installation or guest-disk modification was initiated.

### Shutdown behavior

A normal ACPI shutdown request was attempted first. The live environment did not power off within the controller's 60-second timeout.

The controller intentionally did not escalate automatically. A direct `virsh destroy` was used for this one validation recovery because the guest was booted from live media and the target disk remained unused.
A separate guarded `t2a-vm force-stop NAME --yes` operation was then added and validated against the empty `T2A-Deploy-Test` VM. Normal shutdown and force-stop remain separate operations.

### Snapshot rollback

After the Builder VM was shut off, the controller reverted:

`pre-install-media-20260928`

Post-revert verification showed:

- the CD-ROM device was removed
- boot order returned to hard disk only
- `t2a-vm plan T2A-Builder` again reported `No changes required.`

This validates offline snapshot creation and configuration rollback in addition to qcow2 disk rollback.

The validation snapshot remains available for now as a known pre-installation recovery point.
