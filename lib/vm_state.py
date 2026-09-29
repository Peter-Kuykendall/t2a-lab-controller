#!/usr/bin/env python3
import argparse
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


def run(*args):
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(msg)
    return result.stdout


def domain_exists(name):
    result = subprocess.run(
        ("virsh", "dominfo", name),
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def domain_xml(name):
    return ET.fromstring(run("virsh", "dumpxml", name))


def text_of(root, path, default=""):
    node = root.find(path)
    return node.text.strip() if node is not None and node.text else default


def inspect_vm(name):
    root = domain_xml(name)
    state = run("virsh", "domstate", name).strip()
    vcpus = int(text_of(root, "vcpu", "0"))
    memory_kib = int(text_of(root, "memory", "0"))

    disk = root.find("./devices/disk[@device='disk']")
    if disk is None:
        raise RuntimeError("No primary disk found")

    driver = disk.find("driver")
    source = disk.find("source")
    target = disk.find("target")
    disk_path = source.get("file", "") if source is not None else ""
    disk_target = target.get("dev", "") if target is not None else ""
    disk_format = driver.get("type", "") if driver is not None else ""
    discard = driver.get("discard", "") if driver is not None else ""

    pool = ""
    if disk_path:
        pool = run("virsh", "vol-pool", "--vol", disk_path).strip()
    capacity = 0
    allocation = 0
    if disk_target:
        info = run("virsh", "domblkinfo", name, disk_target)
        for line in info.splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "Capacity":
                capacity = int(value.strip())
            elif key.strip() == "Allocation":
                allocation = int(value.strip())

    iface = root.find("./devices/interface[@type='network']")
    network = ""
    if iface is not None:
        network_source = iface.find("source")
        if network_source is not None:
            network = network_source.get("network", "")

    return {
        "name": name,
        "state": state,
        "cpu_cores": vcpus,
        "memory_mb": memory_kib // 1024,
        "disk": {
            "target": disk_target,
            "path": disk_path,
            "pool": pool,
            "format": disk_format,
            "discard": discard,
            "virtual_size_gb": round(capacity / (1024 ** 3), 2),
            "allocation_mib": round(allocation / (1024 ** 2), 2),
        },
        "network": network,
    }


def print_inspect(actual):
    d = actual["disk"]
    print(f"VM: {actual['name']}")
    print(f"State: {actual['state']}")
    print(f"vCPUs: {actual['cpu_cores']}")
    print(f"Memory: {actual['memory_mb']} MB")
    print("Disk:")
    print(f"  Target: {d['target']}")
    print(f"  Path: {d['path']}")
    print(f"  Pool: {d['pool']}")
    print(f"  Format: {d['format']}")
    print(f"  Discard: {d['discard'] or 'none'}")
    print(f"  Virtual size: {d['virtual_size_gb']:g} GiB")
    print(f"  Current allocation: {d['allocation_mib']:g} MiB")
    print(f"Network: {actual['network']}")


def load_desired(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def print_create_plan(desired):
    disk = desired["storage"]["disks"][0]
    print(f"Plan for {desired['name']}:")
    print("  CREATE virtual machine")
    print(f"  vCPUs: {desired['hardware']['cpu']['cores']}")
    print(f"  Memory: {desired['hardware']['memory']['mb']} MB")
    print(f"  Disk pool: {disk['pool']}")
    print(f"  Disk format: {disk['format']}")
    print(f"  Disk discard: {disk.get('discard', 'none')}")
    print(f"  Disk virtual size: {disk['virtual_size_gb']} GiB")
    print(f"  Network: {desired['network']['libvirt_network']}")
    print("  No changes have been applied.")


def compare(desired, actual):
    disk = desired["storage"]["disks"][0]
    checks = [
        ("name", desired["name"], actual["name"]),
        ("cpu cores", desired["hardware"]["cpu"]["cores"], actual["cpu_cores"]),
        ("memory MB", desired["hardware"]["memory"]["mb"], actual["memory_mb"]),
        ("disk pool", disk["pool"], actual["disk"]["pool"]),
        ("disk format", disk["format"], actual["disk"]["format"]),
        ("disk discard", disk.get("discard", ""), actual["disk"]["discard"]),
        ("disk virtual size GiB", float(disk["virtual_size_gb"]),
         float(actual["disk"]["virtual_size_gb"])),
        ("network", desired["network"]["libvirt_network"], actual["network"]),
    ]
    differences = []
    for label, expected, observed in checks:
        if expected != observed:
            differences.append((label, expected, observed))
    return differences


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("name")

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("name")
    p_plan.add_argument("definition")

    args = parser.parse_args()
    try:
        if args.command == "inspect":
            actual = inspect_vm(args.name)
            print_inspect(actual)
            return 0

        desired = load_desired(Path(args.definition))
        if desired.get("name") != args.name:
            raise ValueError(
                f"Definition name {desired.get('name')!r} does not match requested VM {args.name!r}"
            )

        if not domain_exists(args.name):
            print_create_plan(desired)
            return 2

        actual = inspect_vm(args.name)
        differences = compare(desired, actual)
        print(f"Plan for {args.name}:")
        if not differences:
            print("  No changes required.")
            return 0

        for label, expected, observed in differences:
            print(f"  CHANGE {label}: {observed!r} -> {expected!r}")
        return 2
    except (RuntimeError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
