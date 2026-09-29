#!/usr/bin/env python3
import argparse
import hashlib
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


def run(*args):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(msg)
    return result.stdout


def load_definition(path, name):
    with open(path, "r", encoding="utf-8") as f:
        desired = yaml.safe_load(f)
    if desired.get("name") != name:
        raise ValueError(
            f"Definition name {desired.get('name')!r} does not match {name!r}"
        )
    return desired
def state(name):
    return run("virsh", "domstate", name).strip()


def require_shut_off(name):
    current = state(name)
    if current != "shut off":
        raise RuntimeError(
            f"VM {name!r} must be shut off for this operation; state is {current!r}"
        )


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def boot_order(root):
    os_node = root.find("os")
    if os_node is None:
        return []
    return [n.get("dev", "") for n in os_node.findall("boot")]


def cdrom_source(root):
    disk = root.find("./devices/disk[@device='cdrom']")
    if disk is None:
        return ""
    source = disk.find("source")
    return source.get("file", "") if source is not None else ""
def prepare_install(name, desired):
    require_shut_off(name)
    install = desired.get("installation")
    if not install:
        raise ValueError(f"No installation intent is defined for {name}")

    media = install["media"]
    pool = media["pool"]
    volume = media["volume"]
    expected_sha = media.get("sha256")
    wanted_boot = install.get("boot_order", ["cdrom", "hd"])

    iso_path = run(
        "virsh", "vol-path", "--pool", pool, volume
    ).strip()
    if expected_sha:
        actual_sha = sha256_file(iso_path)
        if actual_sha.lower() != expected_sha.lower():
            raise RuntimeError(
                f"ISO checksum mismatch for {iso_path}: {actual_sha}"
            )

    original_xml = run("virsh", "dumpxml", name)
    root = ET.fromstring(original_xml)
    if cdrom_source(root) == iso_path and boot_order(root) == wanted_boot:
        print(f"{name} installation media already matches intent.")
        return 0
    backup_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", prefix=f"{name}-pre-install-", suffix=".xml", delete=False
        ) as tmp:
            tmp.write(original_xml)
            backup_path = tmp.name

        if cdrom_source(root):
            run(
                "virsh", "detach-disk", name, "sda",
                "--config",
            )

        run(
            "virsh", "attach-disk", name, iso_path, "sda",
            "--type", "cdrom", "--mode", "readonly", "--config",
        )
        run(
            "virt-xml", name, "--edit",
            "--boot", ",".join(wanted_boot),
        )

        verified = ET.fromstring(run("virsh", "dumpxml", name))
        if cdrom_source(verified) != iso_path:
            raise RuntimeError("Post-change verification failed for CD-ROM source")
        if boot_order(verified) != wanted_boot:
            raise RuntimeError("Post-change verification failed for boot order")

        print(f"Prepared {name} for installation.")
        print(f"Media: {iso_path}")
        print(f"Boot order: {', '.join(wanted_boot)}")
        return 0
    except Exception:
        if backup_path:
            subprocess.run(
                ("virsh", "define", backup_path),
                text=True, capture_output=True,
            )
        raise
    finally:
        if backup_path:
            try:
                Path(backup_path).unlink()
            except OSError:
                pass
def start_vm(name):
    current = state(name)
    if current == "running":
        print(f"{name} is already running.")
        return 0
    if current != "shut off":
        raise RuntimeError(f"Cannot start {name} from state {current!r}")

    run("virsh", "start", name)
    current = state(name)
    if current != "running":
        raise RuntimeError(f"{name} failed to reach running state")
    display = run("virsh", "domdisplay", name).strip()
    print(f"Started {name}.")
    print(f"Display: {display or 'not reported'}")
    return 0


def shutdown_vm(name, timeout):
    current = state(name)
    if current == "shut off":
        print(f"{name} is already shut off.")
        return 0
    if current != "running":
        raise RuntimeError(f"Cannot request shutdown from state {current!r}")

    run("virsh", "shutdown", name)
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = state(name)
        if current == "shut off":
            print(f"{name} shut down cleanly.")
            return 0
        time.sleep(2)
    raise RuntimeError(
        f"{name} did not shut down within {timeout}s; no force-stop was attempted"
    )
def force_stop_vm(name):
    current = state(name)
    if current == "shut off":
        print(f"{name} is already shut off.")
        return 0
    if current != "running":
        raise RuntimeError(f"Cannot force-stop {name} from state {current!r}")

    run("virsh", "destroy", name)
    require_shut_off(name)
    print(f"Force-stopped {name}.")
    return 0


def snapshot_create(name, snapshot):
    require_shut_off(name)
    existing = subprocess.run(
        ("virsh", "snapshot-info", name, snapshot),
        text=True, capture_output=True,
    )
    if existing.returncode == 0:
        raise RuntimeError(f"Snapshot {snapshot!r} already exists for {name}")

    run(
        "virsh", "snapshot-create-as", name, snapshot,
        "--description", "T2A controller validation snapshot",
        "--atomic",
    )
    print(f"Created snapshot {snapshot} for {name}.")
    return 0


def snapshot_revert(name, snapshot):
    require_shut_off(name)
    run("virsh", "snapshot-info", name, snapshot)
    run("virsh", "snapshot-revert", name, snapshot)
    require_shut_off(name)
    print(f"Reverted {name} to snapshot {snapshot}.")
    return 0


def capture_screen(name, output):
    current = state(name)
    if current != "running":
        raise RuntimeError(
            f"VM {name!r} must be running to capture a screen; state is {current!r}"
        )

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run("virsh", "screenshot", name, str(output_path))
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("Screenshot command returned without a usable image")

    print(f"Captured {name} screen: {output_path}")
    return 0


def snapshot_list(name):
    print(run("virsh", "snapshot-list", name).rstrip())
    return 0


def deployment_preflight(name):
    require_shut_off(name)

    xml = ET.fromstring(run("virsh", "dumpxml", name))
    disk = xml.find("./devices/disk[@device='disk']")
    if disk is None:
        raise RuntimeError("No target system disk is defined")
    target = disk.find("target")
    source = disk.find("source")
    target_dev = target.get("dev", "") if target is not None else ""
    source_path = source.get("file", "") if source is not None else ""

    blkinfo = run("virsh", "domblkinfo", name, target_dev)
    capacity = ""
    allocation = ""
    for line in blkinfo.splitlines():
        key, _, value = line.partition(":")
        if key.strip() == "Capacity":
            capacity = value.strip()
        elif key.strip() == "Allocation":
            allocation = value.strip()

    boot = boot_order(xml) or ["firmware/default"]
    snapshots = run("virsh", "snapshot-list", name, "--name").split()

    candidates = []
    for pool in run("virsh", "pool-list", "--name").split():
        listing = run("virsh", "vol-list", pool)
        for line in listing.splitlines()[2:]:
            fields = line.split()
            if not fields:
                continue
            volume = fields[0]
            if volume.lower().endswith((".img", ".iso")):
                path = run("virsh", "vol-path", "--pool", pool, volume).strip()
                candidates.append((pool, volume, path))

    usb_disks = []
    lsblk = run("lsblk", "-dn", "-o", "NAME,TYPE,TRAN,SIZE,MODEL")
    for line in lsblk.splitlines():
        fields = line.split(None, 4)
        if len(fields) >= 4 and fields[1] == "disk" and fields[2] == "usb":
            usb_disks.append(line.strip())

    provisioning = [
        item for item in candidates
        if item[1].lower().endswith(".img")
    ]

    print(f"Deployment preflight for {name}:")
    print(f"  VM state: shut off")
    print(f"  Target disk: {target_dev} -> {source_path}")
    print(f"  Target capacity: {capacity} bytes")
    print(f"  Current allocation: {allocation} bytes")
    print(f"  Boot order: {', '.join(boot)}")
    print(f"  Snapshots: {', '.join(snapshots) if snapshots else 'none'}")

    print("  Candidate virtual boot media:")
    if candidates:
        for pool, volume, path in candidates:
            print(f"    {pool}/{volume} -> {path}")
    else:
        print("    none")

    print("  Host USB storage devices:")
    if usb_disks:
        for item in usb_disks:
            print(f"    {item}")
    else:
        print("    none")

    if provisioning:
        print("READY: at least one disk-image deployment medium is available.")
        return 0

    print(
        "BLOCKED: no provisioning USB/disk image is available to boot the "
        "deployment VM."
    )
    print(
        "Rev M production media uses a three-partition USB layout "
        "(USB-DATA, Live-usb, LIVE-UEFI), so an ISO alone is not an "
        "equivalent deployment test."
    )
    return 2


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare-install")
    p_prepare.add_argument("name")
    p_prepare.add_argument("definition")

    p_start = sub.add_parser("start")
    p_start.add_argument("name")

    p_stop = sub.add_parser("shutdown")
    p_stop.add_argument("name")
    p_stop.add_argument("--timeout", type=int, default=120)

    p_force = sub.add_parser("force-stop")
    p_force.add_argument("name")

    p_sc = sub.add_parser("snapshot-create")
    p_sc.add_argument("name")
    p_sc.add_argument("snapshot")

    p_sr = sub.add_parser("snapshot-revert")
    p_sr.add_argument("name")
    p_sr.add_argument("snapshot")

    p_sl = sub.add_parser("snapshot-list")
    p_sl.add_argument("name")

    p_cap = sub.add_parser("capture-screen")
    p_cap.add_argument("name")
    p_cap.add_argument("output")

    p_dp = sub.add_parser("deploy-preflight")
    p_dp.add_argument("name")

    args = parser.parse_args()
    try:
        if args.command == "prepare-install":
            return prepare_install(
                args.name, load_definition(args.definition, args.name)
            )
        if args.command == "start":
            return start_vm(args.name)
        if args.command == "shutdown":
            return shutdown_vm(args.name, args.timeout)
        if args.command == "force-stop":
            return force_stop_vm(args.name)
        if args.command == "snapshot-create":
            return snapshot_create(args.name, args.snapshot)
        if args.command == "snapshot-revert":
            return snapshot_revert(args.name, args.snapshot)
        if args.command == "snapshot-list":
            return snapshot_list(args.name)
        if args.command == "capture-screen":
            return capture_screen(args.name, args.output)
        if args.command == "deploy-preflight":
            return deployment_preflight(args.name)
        raise ValueError(f"Unknown command: {args.command}")
    except (RuntimeError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
