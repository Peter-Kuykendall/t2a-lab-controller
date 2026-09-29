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

The later framebuffer was also inspected visually rather than relying only on color complexity. It shows the expected Linux Mint MATE live graphical environment rather than a GRUB prompt, kernel panic, initramfs shell, or text-mode boot failure. This visual classification is now the preferred validation method; color-counting remains only a coarse fallback signal.

No unattended installation or guest-disk modification was initiated.

### Shutdown behavior

A normal ACPI shutdown request was attempted first. The live environment did not power off within the controller's 60-second timeout.

The controller intentionally did not escalate automatically. A direct `virsh destroy` was used for this one validation recovery because the guest was booted from live media and the target disk remained unused.
A separate guarded `t2a-vm force-stop NAME --yes` operation was then added and validated against the empty `T2A-Deploy-Test` VM. Normal shutdown and force-stop remain separate operations.

The installed OEM Builder was later observed to shut down cleanly, but just after the original 60-second controller timeout. The graceful-shutdown wait was therefore increased to 120 seconds. This does not change the safety rule: timeout still reports failure and never escalates automatically to `force-stop`.

A subsequent OEM Builder start/shutdown validation completed cleanly through the controller with exit code 0; the guest powered off about three seconds after the shutdown request. The longer timeout is therefore headroom for variable guest behavior rather than a forced delay.

### Snapshot rollback

After the Builder VM was shut off, the controller reverted:

`pre-install-media-20260928`

Post-revert verification showed:

- the CD-ROM device was removed
- boot order returned to hard disk only
- `t2a-vm plan T2A-Builder` again reported `No changes required.`

This validates offline snapshot creation and configuration rollback in addition to qcow2 disk rollback.

The validation snapshot remains available for now as a known pre-installation recovery point.

## 2026-09-28 — OEM installation workflow

Linux Mint 22.3 MATE was installed successfully in `T2A-Builder` using the ISO's documented GRUB entry:

`OEM install (for manufacturers)`

The ISO boot entry passes `oem-config/enable=true` and `only-ubiquity`, confirming that the installer intentionally supports manufacturer/OEM preparation.

The installation used English (US), Chicago time zone, the blank virtual disk, and the installer's multimedia-codecs option. The OEM batch name was recorded as `T2A-2026-09-28`. No permanent end-user account was created.

After installation, the ISO was ejected before the required restart and persistent boot order was returned to hard disk only.

The installed system then booted successfully into the OEM technician desktop. Visual inspection confirmed:

- Linux Mint 22.3 MATE Welcome screen
- the `OEM Configuration (temporary user)` environment
- desktop icon `Prepare for shipping to end user`

This proves that T2A can configure and test the installed system before invoking the final end-user account setup.

An offline recovery point was created after successful OEM installation:

`oem-installed-baseline-20260928`

The snapshot was restored and visually verified to return to the same OEM technician desktop. It is therefore the current known-good Builder installation baseline.

### Visual boot-state validation

Framebuffer screenshots are now treated as semantic evidence, not merely as pixel activity. A captured screen can be classified against expected stages such as:

- GRUB menu or GRUB command line
- Mint splash / normal boot
- initramfs or emergency shell
- kernel or filesystem error text
- live MATE desktop
- OEM installer
- installed OEM technician desktop

The earlier unique-color count remains useful only as a coarse indication that a display changed.

A standardized capture made with `t2a-vm capture-screen T2A-Builder oem-semantic-validation` was ingested directly and visually classified as the expected installed Linux Mint MATE OEM technician environment rather than a bootloader, emergency shell, or text error state.

### Concurrent-operation guard

During OEM validation, overlapping remote controller sessions were detected manipulating the same VM. The affected sessions were stopped and the Builder was restored from the known-good OEM snapshot.

The controller now uses two complementary guards for every mutating operation:

- a non-blocking exclusive per-VM lock; an overlapping mutation exits with code 3
- a controller-session capability; `session-new` rotates the local token and invalidates stale mutation shells, which then exit with code 4

The session file is mode 600. A stale-session start attempt against `T2A-Deploy-Test` was refused with exit code 4 and the VM remained shut off.

The lock was then validated with the current session capability by deliberately holding the `T2A-Deploy-Test` lock and attempting to start that VM. The controller refused the start with exit code 3 and the VM remained shut off.

This protects both against simultaneously overlapping commands and against old remote shells issuing later queued mutations. Read-only inspection remains available without a mutation session.

### Standard framebuffer capture

The controller now exposes `t2a-vm capture-screen NAME LABEL`. It writes a labeled PNG under `logs/validation/` without changing guest or VM configuration. These images can be ingested for semantic classification of expected Mint screens or failure states such as GRUB, initramfs, kernel, filesystem, or display-manager errors.

## 2026-09-28 — Deploy-Test preflight

The controller now exposes the read-only command:

`t2a-vm deploy-preflight T2A-Deploy-Test`

The initial preflight verified:

- `T2A-Deploy-Test` is shut off
- target disk `vda` exists at 30 GiB and is essentially empty/thin
- boot order is hard disk only
- no deployment snapshots exist yet
- no USB storage device is attached to the host
- the only virtual boot media currently present are Linux Mint ISO copies

The preflight intentionally reports **BLOCKED** because no bootable provisioning USB/disk image is available. Rev M production media uses the three-partition `USB-DATA` / `Live-usb` / `LIVE-UEFI` layout, so the Mint ISO is not treated as an equivalent deployment test source.

A real deployment/regression run therefore waits for either a full bootable Rev M provisioning-stick image on the lab host or a physical Rev M stick connected for controlled passthrough.

## 2026-09-28 — Virtual J -> M fixture

The verified 32 GiB `J-usb.img` archive is now present on `t2a-lab`; its supplied SHA1 was confirmed before use. Inspection verified the legacy three-partition J layout and the J-era Clonezilla 2.6.7-28-i686 runtime.

A writable M candidate was created as `M-usb.qcow2`, a qcow2 overlay backed by the immutable raw J image. The overlay has a 32 GiB virtual size but initially consumes only a few hundred KiB. Failed migrations can therefore be discarded without recopying or modifying the J master.

A dry libvirt XML generation confirmed that the qcow2 overlay can be attached to a VM with `bus=usb`, allowing the guest to report the provisioning medium as USB storage. This preserves the production upgrader's `TRAN=usb` guard instead of creating a lab-only bypass.

The official Clonezilla 3.3.3-15 amd64 ZIP was downloaded and extracted locally. SHA256 checks of `vmlinuz`, `initrd.img`, and `filesystem.squashfs` exactly matched the known-good hashes embedded in the validated T2A J -> M migration script.

The remaining blocker is limited to three T2A-specific approved reference files: `t2a-revl.sh`, `go.sh`, and the provisioning private SSH key. Once those are copied from the known-good T2A reference tree, the next step is a dry-run of the production J -> M upgrader against the virtual USB overlay.

See `docs/virtual-provisioning-stick.md` for the complete workflow and safety rules.

### Successful J -> M dry-run

`T2A-Stick-Builder`, a temporary Ubuntu cloud helper VM, was used to run the real production migration engine against the J-backed qcow2 USB overlay. Guest inspection confirmed `TRAN=usb`.

The final dry-run exited 0. It verified `J_LAYOUT_32G`, Clonezilla 2.6.7-28-i686, golden-image presence, the modern Clonezilla 3.3.3-15 reference, clean Rev M repo state, and the known Rev M code fixes. The target partitions were mounted read-only and cleanup left no `/dev/sda*` mounts or `/tmp/t2a-j2m.*` directories.

The apply phase remains intentionally unstarted pending the next explicit step.

