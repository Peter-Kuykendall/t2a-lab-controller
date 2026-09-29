# Virtual Rev M Provisioning Stick

## Purpose

This document records how the lab will create a repeatable Rev M provisioning medium for `T2A-Deploy-Test` from the archived legacy J image.

The design preserves the original J image, keeps the production J -> M safety checks intact, and creates a disposable/repeatable regression fixture.

## Source image

The provisioning repository contains the verified raw source image at:

`/home/tech/Projects/t2a-provisioning/USB-sticks/J/J-usb.img`

It is a 32 GiB `dd` image. The accompanying SHA1 was verified before use:

`47d94c34b1ee12a498387f6d885de14de3922ea1`

The source image is immutable lab reference material and must never be used as the writable migration target.

## Working image

The writable M candidate is a qcow2 overlay backed by the raw J image:

`/home/tech/Projects/t2a-provisioning/USB-sticks/M/M-usb.qcow2`

It presents a 32 GiB virtual disk while initially consuming only a few hundred KiB.
Reads come from the J backing image until a block is changed. All migration writes are stored in the overlay.

This makes reset cheap: delete the failed overlay and create a new one against the same verified J source.

If a standalone raw M image is later needed for writing to a physical USB device, the validated overlay can be converted to raw after testing.

## USB presentation

The production J -> M migration engine requires its target to report `TRAN=usb`.

The lab does not bypass that guard.

libvirt can attach the qcow2 overlay using a USB storage bus. A dry `virt-xml --print-diff` confirmed the intended device form:

```xml
<disk type="file" device="disk">
  <driver name="qemu" type="qcow2"/>
  <source file="/home/tech/Projects/t2a-provisioning/USB-sticks/M/M-usb.qcow2"/>
  <target dev="sda" bus="usb" removable="on"/>
</disk>
```

The guest therefore sees the virtual provisioning image as USB storage while its normal target system disk remains separate.
## Migration inputs

The large standard Clonezilla 3.3.3-15 amd64 runtime has been reconstructed from the official Clonezilla ZIP and hash-verified against the known-good values embedded in the T2A migration script.

The remaining T2A-specific reference files still required before migration are:

```text
reference/clonezilla/t2a-revl.sh
reference/usb-data/go.sh
reference/usb-data/ssh/t2a_sync_ed25519
```

The corresponding public key is optional but useful.

These files must come from the approved T2A reference copy. They are not synthesized from memory, and the private key is never committed.

## Planned validation sequence

1. create a fresh qcow2 overlay from the verified J master;
2. present the overlay to a helper/Linux environment as USB storage;
3. run the production J -> M upgrader in dry-run mode;
4. verify geometry, J runtime, labels, space, modern-source hashes, and reference files;
5. perform the explicit J -> M apply only after preflight passes;
6. boot `T2A-Deploy-Test` from the resulting virtual Rev M USB disk;
7. exercise the normal provisioning workflow against the disposable Deploy-Test target disk;
8. restore the golden image, expand filesystems, and perform normal post-processing;
9. boot the restored Linux Mint system;
10. capture and semantically inspect the VM framebuffer.

Semantic screen inspection is the preferred boot-state check. It can classify expected Mint/Clonezilla states as well as failures such as GRUB console, initramfs shell, kernel text errors, filesystem errors, or other unexpected screens.

## Safety rules

- Never mutate the archived raw J image.
- Never relax the migration engine to accept arbitrary partition geometry.
- Preserve the production `TRAN=usb` check.
- Dry-run before apply.
- Keep provisioning private keys out of Git.
- Keep raw/qcow2 provisioning media out of Git.
- Use VM snapshots around destructive regression stages where useful.
- Do not automatically escalate graceful shutdown failure to force-stop.

The provisioning-side details, exact J geometry, and reference hashes are documented in:

`t2a-provisioning/docs/rev-m-virtual-stick-lab.md`

## Dry-run result

A temporary Ubuntu 24.04 cloud helper VM named `T2A-Stick-Builder` was created specifically to exercise the production migration engine without weakening its checks. The J-backed qcow2 overlay appeared inside the guest as `/dev/sda`, model `QEMU HARDDISK`, with `ID_BUS=usb` and `TRAN=usb`.

The production J -> M dry-run completed successfully with exit code 0 after two migration-engine defects were found and corrected: explicit modern-reference path options were accepted by the fleet wrapper but not by the engine, and temporary mount state created inside command substitutions was not visible to the parent cleanup trap.

The corrected dry-run recognized the exact 32 GiB J layout, verified the J Clonezilla runtime and golden-image presence, verified the Rev M reference tree and repo state, mounted target filesystems read-only, and removed every temporary mount/directory at exit.

No `--apply` operation has been performed.

