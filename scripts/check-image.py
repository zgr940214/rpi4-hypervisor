#!/usr/bin/env python3
"""Inspect a Pi4 Xen raw card image without mounting or modifying it.

The JSON report records static evidence only. It never certifies a real Pi4 boot.
Requires mtools, e2fsprogs and binutils on the inspection host.
"""

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys
import tempfile


class CheckError(Exception):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode:
        raise CheckError(f"{args[0]} exited {result.returncode}: {result.stderr.strip()}")
    return result.stdout


def partitions(path):
    """Accept the two-partition DOS layout used by this project's .wks."""
    length = Path(path).stat().st_size
    with open(path, "rb") as image:
        mbr = image.read(512)
    if len(mbr) != 512 or mbr[510:512] != b"\x55\xaa":
        raise CheckError("Missing DOS/MBR signature; a rootfs alone is not a card image")
    result = []
    for index in range(4):
        entry = mbr[446 + index * 16:462 + index * 16]
        flag, kind = entry[0], entry[4]
        start, count = struct.unpack_from("<II", entry, 8)
        if not kind and not start and not count:
            continue
        if kind == 0xEE:
            raise CheckError("GPT images are unsupported; expected the project's DOS layout")
        if flag not in (0, 0x80) or not kind or not start or not count:
            raise CheckError(f"Invalid MBR entry {index + 1}")
        end = (start + count) * 512
        if end > length:
            raise CheckError(f"Partition {index + 1} extends beyond image length")
        result.append({"number": index + 1, "type": kind, "offset": start * 512,
                       "size": count * 512, "end": end, "bootable": flag == 0x80})
    if len(result) != 2 or [p["number"] for p in result] != [1, 2]:
        raise CheckError("Expected exactly primary partitions 1 (FAT) and 2 (ext4)")
    if result[0]["type"] not in (0x06, 0x0B, 0x0C, 0x0E) or result[1]["type"] != 0x83:
        raise CheckError("Expected a FAT boot partition followed by Linux type 0x83")
    if result[0]["offset"] >= result[1]["offset"] or result[0]["end"] > result[1]["offset"]:
        raise CheckError("Partitions overlap or occur in the wrong order")
    return result


def sparse_copy(source, offset, size, destination):
    """Copy one partition, leaving zero blocks sparse; never open source writable."""
    with open(source, "rb") as src, open(destination, "xb") as dst:
        src.seek(offset)
        remaining = size
        while remaining:
            data = src.read(min(1024 * 1024, remaining))
            if not data:
                raise CheckError("Unexpected EOF while reading partition")
            if any(data):
                dst.write(data)
            else:
                dst.seek(len(data), os.SEEK_CUR)
            remaining -= len(data)
        dst.truncate(size)


def filesystem_info(path):
    with open(path, "rb") as image:
        image.seek(1024)
        sb = image.read(1024)
    if len(sb) != 1024 or sb[56:58] != b"\x53\xef":
        raise CheckError("Expected a raw ext filesystem with superblock at byte 1024")
    incompat = struct.unpack_from("<I", sb, 96)[0]
    if not incompat & 0x40:
        raise CheckError("Expected ext4 extents feature")
    log_block = struct.unpack_from("<I", sb, 24)[0]
    if log_block > 6:
        raise CheckError("Invalid ext4 block size")
    block_size = 1024 << log_block
    count = struct.unpack_from("<I", sb, 4)[0]
    if incompat & 0x80:
        count |= struct.unpack_from("<I", sb, 0x150)[0] << 32
    if count * block_size > Path(path).stat().st_size:
        raise CheckError("Ext4 filesystem exceeds available image data")
    return {"format": "ext4", "block_size": block_size, "blocks": count}


def clean_path(path):
    if not isinstance(path, str) or not re.fullmatch(r"/[A-Za-z0-9_./+@:-]+", path):
        raise CheckError(f"Unsupported filesystem path: {path!r}")
    parts = []
    for part in PurePosixPath(path).parts[1:]:
        if part == "..":
            if not parts:
                raise CheckError("Path escapes image root")
            parts.pop()
        elif part != ".":
            parts.append(part)
    return "/" + "/".join(parts)


class Ext4:
    def __init__(self, path, scratch):
        self.path = Path(path)
        self.scratch = Path(scratch)
        self.counter = 0
        filesystem_info(path)

    def command(self, command):
        return run(["debugfs", "-R", command, str(self.path)])

    def stat(self, path):
        output = self.command("stat " + clean_path(path))
        if not re.search(r"Inode:\s+\d+", output):
            raise CheckError(f"Missing inode {path}")
        return output

    def resolve(self, path):
        path = clean_path(path)
        for _ in range(40):
            pieces = PurePosixPath(path).parts[1:]
            changed = False
            for number in range(1, len(pieces) + 1):
                prefix = "/" + "/".join(pieces[:number])
                info = self.stat(prefix)
                if "Type: symlink" not in info:
                    continue
                match = re.search(r'Fast link dest:\s*"(.*)"', info)
                target = match.group(1) if match else self.read_raw(prefix).decode().rstrip("\x00")
                if not target.startswith("/"):
                    target = str(PurePosixPath(prefix).parent / target)
                tail = "/".join(pieces[number:])
                path = clean_path(target + ("/" + tail if tail else ""))
                changed = True
                break
            if not changed:
                return path
        raise CheckError(f"Symlink loop while resolving {path}")

    def exists(self, path):
        try:
            self.resolve(path)
            return True
        except CheckError:
            return False

    def dump(self, path, destination):
        resolved = self.resolve(path)
        info = self.stat(resolved)
        if "Type: regular" not in info:
            raise CheckError(f"Expected a regular file at {path}")
        self.command(f"dump {resolved} {destination}")
        if not Path(destination).is_file():
            raise CheckError(f"Could not extract {path}")

    def read_raw(self, path):
        self.counter += 1
        dest = self.scratch / f"raw-{self.counter}"
        self.command(f"dump {clean_path(path)} {dest}")
        if not dest.is_file():
            raise CheckError(f"Could not read {path}")
        return dest.read_bytes()

    def read(self, path):
        self.counter += 1
        dest = self.scratch / f"read-{self.counter}"
        self.dump(path, dest)
        return dest.read_bytes()

    def text(self, path):
        return self.read(path).decode("utf-8")

    def require(self, paths):
        resolved = {path: self.resolve(path) for path in paths}
        return resolved


def parse_guest_config(text):
    """Parse the intentionally declarative xl file; never execute image content."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise CheckError(f"Invalid guest configuration: {exc}") from exc
    config = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise CheckError("guest1.cfg must contain literal assignments only")
        name = node.targets[0].id
        if name in config:
            raise CheckError(f"Duplicate guest setting {name}")
        try:
            config[name] = ast.literal_eval(node.value)
        except (ValueError, TypeError) as exc:
            raise CheckError(f"Nonliteral guest setting {name}") from exc
    expected = {"name": "guest1", "vcpus": 1,
                "kernel": "/var/lib/xen/images/guest1/Image"}
    for key, value in expected.items():
        if config.get(key) != value:
            raise CheckError(f"Expected {key}={value!r}, got {config.get(key)!r}")
    if type(config.get("vcpus")) is not int:
        raise CheckError("Guest vcpus must be an integer")
    if type(config.get("memory")) is not int or config["memory"] <= 0:
        raise CheckError("Guest memory must be a positive integer in MiB")
    extra = config.get("extra", "")
    if not isinstance(extra, str) or "console=hvc0" not in extra.split() or "root=/dev/xvda" not in extra.split():
        raise CheckError("Guest must boot raw xvda with console=hvc0")
    if "rw" not in extra.split():
        raise CheckError("Guest kernel command line must request a writable rootfs")
    disks = config.get("disk")
    if not isinstance(disks, list) or len(disks) != 1 or not isinstance(disks[0], str):
        raise CheckError("Expected exactly one raw writable guest disk")
    disk = disks[0]
    fields = [item.strip() for item in disk.split(",")]
    pairs = [item.split("=", 1) for item in fields if "=" in item]
    values = dict(pairs)
    if len(pairs) != len(values):
        raise CheckError("Duplicate guest disk setting")
    if values:
        if any("=" not in item for item in fields):
            raise CheckError("Mixed positional and named disk syntax is unsupported")
        expected_disk = {"target": "/var/lib/xen/images/guest1/rootfs.ext4",
                         "format": "raw", "vdev": "xvda", "access": "rw", "backendtype": "phy"}
        if any(values.get(key) != value for key, value in expected_disk.items()):
            raise CheckError(f"Expected a phy/loop raw xvda disk: {expected_disk}")
    elif fields != ["phy:/var/lib/xen/images/guest1/rootfs.ext4", "xvda", "w"]:
        raise CheckError("Expected phy raw file exported writable as xvda")
    if config.get("vif") not in (None, []):
        raise CheckError("First-version guest must not depend on an unconfigured network")
    return config


def kernel_config(path, guest=False):
    values = dict(re.findall(r"^(CONFIG_[A-Z0-9_]+)=(.*)$", Path(path).read_text(), re.MULTILINE))
    required = ["CONFIG_ARM64", "CONFIG_XEN", "CONFIG_HVC_XEN", "CONFIG_XEN_BLKDEV_FRONTEND",
                "CONFIG_EXT4_FS", "CONFIG_DEVTMPFS", "CONFIG_DEVTMPFS_MOUNT"]
    if not guest:
        required += ["CONFIG_XEN_BLKDEV_BACKEND", "CONFIG_BLK_DEV_LOOP", "CONFIG_XEN_DEV_EVTCHN",
                     "CONFIG_XEN_GNTDEV", "CONFIG_XEN_PRIVCMD", "CONFIG_MMC", "CONFIG_MMC_BLOCK",
                     "CONFIG_ARCH_BCM2835", "CONFIG_MMC_SDHCI", "CONFIG_MMC_SDHCI_IPROC",
                     "CONFIG_BCMGENET", "CONFIG_BCM2835_MBOX", "CONFIG_RASPBERRYPI_FIRMWARE"]
    missing = [name for name in required if values.get(name) != "y"]
    if missing:
        raise CheckError("Required built-in kernel options missing: " + ", ".join(missing))
    return {"path": str(Path(path).resolve()), "sha256": sha256(path),
            "required_builtins": required, "note": "Final .config supplied by build; not a boot test"}


def arm64_image(path):
    with open(path, "rb") as stream:
        header = stream.read(64)
    if len(header) < 64 or header[56:60] != b"ARM\x64":
        raise CheckError(f"{Path(path).name} is not an uncompressed AArch64 Linux Image")
    size = struct.unpack_from("<Q", header, 16)[0]
    return {"file_size": Path(path).stat().st_size, "runtime_size": size,
            "sha256": sha256(path)}


def elf_dependencies(fs, binary):
    """Resolve ELF interpreter and recursively check DT_NEEDED inside the image."""
    pending = [binary]
    checked = set()
    dirs = ("/lib", "/usr/lib", "/lib64", "/usr/lib64", "/lib/aarch64-linux-gnu", "/usr/lib/aarch64-linux-gnu")
    while pending:
        source = fs.resolve(pending.pop())
        if source in checked:
            continue
        checked.add(source)
        fs.counter += 1
        local = fs.scratch / f"elf-{fs.counter}"
        fs.dump(source, local)
        with open(local, "rb") as stream:
            if stream.read(4) != b"\x7fELF":
                raise CheckError(f"Expected ELF executable/library at {source}")
        headers = run(["readelf", "-h", "-l", "-d", str(local)])
        if not re.search(r"Machine:\s+AArch64", headers):
            raise CheckError(f"Non-AArch64 executable at {source}")
        interpreter = re.search(r"Requesting program interpreter:\s*([^\]]+)", headers)
        if interpreter:
            pending.append(clean_path(interpreter.group(1)))
        for soname in re.findall(r"\(NEEDED\).*Shared library: \[([^\]]+)\]", headers):
            matches = [f"{directory}/{soname}" for directory in dirs if fs.exists(f"{directory}/{soname}")]
            if not matches:
                raise CheckError(f"{source} needs missing library {soname}")
            pending.append(matches[0])
    return sorted(checked)


class Report:
    def __init__(self, output):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.checks = []

    def add(self, name, status, detail):
        self.checks.append({"name": name, "status": status, "detail": detail})

    def check(self, name, operation):
        try:
            result = operation()
        except (CheckError, OSError, UnicodeError, ValueError) as exc:
            self.add(name, "FAIL", str(exc))
            return None
        self.add(name, "PASS", result)
        return result

    def finish(self, image):
        self.add("pi4_hardware_boot", "NOT_RUN", "Requires real Pi4 UART, Dom0 SSH and guest shell validation")
        has_failure = any(item["status"] == "FAIL" for item in self.checks)
        blocked = any(item["status"] == "BLOCKED" for item in self.checks)
        status = "FAIL" if has_failure else "BLOCKED" if blocked else "PASS"
        summary = {"image": str(Path(image).resolve()), "scope": "static image inspection",
                   "static_status": status, "checks": self.checks}
        (self.output / "image-checks.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
        return int(status != "PASS")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--deploy", type=Path, required=True)
    parser.add_argument("--kernel-config", type=Path, required=True)
    parser.add_argument("--guest-kernel-config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temp-dir", type=Path)
    args = parser.parse_args(argv)
    report = Report(args.output)
    tools = ("mcopy", "mdir", "debugfs", "dumpe2fs", "e2fsck", "readelf")
    missing = [name for name in tools if not shutil.which(name)]
    if missing:
        report.add("inspection_tools", "BLOCKED", "Install: " + ", ".join(missing))
        return report.finish(args.image)
    table = report.check("partition_table", lambda: partitions(args.image))
    if table is None:
        return report.finish(args.image)
    report.check("dom0_kernel_config", lambda: kernel_config(args.kernel_config))
    report.check("guest_kernel_config", lambda: kernel_config(args.guest_kernel_config or args.kernel_config, guest=True))
    report.check("image_sha256", lambda: {"sha256": sha256(args.image), "bytes": args.image.stat().st_size})
    try:
        with tempfile.TemporaryDirectory(prefix="pi4-image-check-", dir=args.temp_dir) as temporary:
            scratch = Path(temporary)
            fat = f"{args.image.resolve()}@@{table[0]['offset']}"
            boot = scratch / "boot"
            boot.mkdir()
            boot_files = ["config.txt", "start4.elf", "fixup4.dat", "u-boot.bin", "boot.scr", "xen", "Image", "bcm2711-rpi-4-b.dtb"]
            for filename in boot_files:
                report.check("boot_file:" + filename,
                             lambda name=filename: run(["mcopy", "-i", fat, "::/" + name, str(boot / name)]))
            report.check("dom0_kernel_image", lambda: arm64_image(boot / "Image"))
            root = scratch / "dom0.ext4"
            sparse_copy(args.image, table[1]["offset"], table[1]["size"], root)
            report.check("dom0_filesystem", lambda: filesystem_info(root))
            report.check("dom0_superblock", lambda: run(["dumpe2fs", "-h", str(root)]))
            report.check("dom0_filesystem_integrity", lambda: run(["e2fsck", "-f", "-n", str(root)]))
            fs = Ext4(root, scratch)
            report.check("dom0_required_files", lambda: fs.require([
                "/bin/sh", "/sbin/init", "/usr/sbin/sshd", "/etc/xen/guest1.cfg",
                "/var/lib/xen/images/guest1/Image", "/var/lib/xen/images/guest1/rootfs.ext4",
                "/usr/sbin/guest1-start", "/usr/sbin/guest1-pause-demo", "/usr/sbin/guest1-common.sh"]))
            for binary, paths in (("xl", ["/usr/sbin/xl", "/usr/bin/xl"]),
                                  ("xenstored", ["/usr/sbin/xenstored", "/usr/bin/xenstored"]),
                                  ("xenconsoled", ["/usr/sbin/xenconsoled", "/usr/bin/xenconsoled"]),
                                  ("sshd", ["/usr/sbin/sshd"])):
                def check_binary(options=paths):
                    found = next((item for item in options if fs.exists(item)), None)
                    if found is None:
                        raise CheckError("Missing binary: " + " or ".join(options))
                    return elf_dependencies(fs, found)
                report.check("dom0_elf_dependencies:" + binary, check_binary)
            report.check("guest_configuration", lambda: parse_guest_config(fs.text("/etc/xen/guest1.cfg")))
            guest_image = scratch / "guest1.ext4"
            fs.dump("/var/lib/xen/images/guest1/rootfs.ext4", guest_image)
            report.check("guest_filesystem", lambda: filesystem_info(guest_image))
            report.check("guest_filesystem_integrity", lambda: run(["e2fsck", "-f", "-n", str(guest_image)]))
            guest = Ext4(guest_image, scratch)
            report.check("guest_required_files", lambda: guest.require(["/bin/sh", "/sbin/init"]))
            def hostname():
                name = guest.text("/etc/hostname").strip()
                if name != "guest1":
                    raise CheckError(f"Unexpected guest hostname {name!r}")
                return name
            report.check("guest_hostname", hostname)
            guest_kernel = scratch / "guest-Image"
            fs.dump("/var/lib/xen/images/guest1/Image", guest_kernel)
            report.check("guest_kernel_image", lambda: arm64_image(guest_kernel))
            if not args.guest_kernel_config:
                def shared_kernel():
                    if sha256(guest_kernel) != sha256(boot / "Image"):
                        raise CheckError("Guest and Dom0 Image differ despite a shared final kernel configuration")
                    return sha256(guest_kernel)
                report.check("shared_kernel_identity", shared_kernel)
            # Extended service and boot-script checks follow the project layout.
            inspect_services(report, fs, guest)
            inspect_boot(report, boot, args.deploy)
            report.add("ssh_login", "NOT_RUN", "Static SSH files do not prove network connectivity or possession of the login key")
            artifact = {"image": str(args.image.resolve()), "sha256": sha256(args.image),
                        "bytes": args.image.stat().st_size,
                        "kernel_config_sha256": sha256(args.kernel_config)}
            (args.output / "artifact.json").write_text(json.dumps(artifact, indent=2) + "\n")
            (args.output / "SHA256SUMS").write_text(f"{artifact['sha256']}  {args.image.name}\n")
    except (CheckError, OSError, UnicodeError, ValueError) as exc:
        report.add("remaining_inspection", "FAIL", str(exc))
    return report.finish(args.image)


def inspect_services(report, fs, guest):
    def dom0():
        if fs.text("/etc/hostname").strip() != "pi4-dom0":
            raise CheckError("Dom0 hostname must be pi4-dom0")
        paths = [f"/etc/systemd/system/multi-user.target.wants/{name}.service"
                 for name in ("xenstored", "xenconsoled", "xen-init-dom0")]
        resolved = fs.require(paths + ["/etc/xen/scripts/block"])
        for path in paths:
            text = fs.text(path)
            if not re.search(r"^ExecStart=", text, re.MULTILINE):
                raise CheckError(f"No ExecStart in {path}")
            if re.search(r"^ExecStart=.*@(?:sbindir|LIBEXEC_BIN|XEN_SCRIPT_DIR)@", text, re.MULTILINE):
                raise CheckError(f"Unexpanded Xen install paths in {path}")
        init = fs.resolve("/sbin/init")
        if not init.endswith("/systemd"):
            raise CheckError(f"Expected systemd init, found {init}")
        loops = [p for p in ("/sbin/losetup", "/usr/sbin/losetup", "/usr/bin/losetup") if fs.exists(p)]
        if not loops:
            raise CheckError("Missing losetup required by the phy file backend")
        autostart = "/etc/xen/auto/guest1.cfg"
        if fs.exists(autostart):
            raise CheckError("guest1 must be started manually, but /etc/xen/auto/guest1.cfg exists")
        resolved["loop_tool"] = loops[0]
        return resolved
    report.check("dom0_services_and_loop_backend", dom0)

    def login():
        link = "/etc/systemd/system/getty.target.wants/serial-getty@hvc0.service"
        override = "/etc/systemd/system/serial-getty@hvc0.service.d/autologin.conf"
        files = guest.require([link, override, "/sbin/agetty", "/bin/login"])
        text = guest.text(override)
        if not re.search(r"^ExecStart=.*agetty\s+.*--autologin\s+root(?:\s|$)", text, re.MULTILINE):
            raise CheckError("Guest hvc0 service does not enable the documented root console autologin")
        passwd = guest.text("/etc/passwd")
        root = next((line.split(":") for line in passwd.splitlines() if line.startswith("root:")), None)
        if root is None or len(root) != 7 or root[-1] not in ("/bin/sh", "/bin/bash"):
            raise CheckError("Guest root account has no usable shell")
        guest.require([root[-1]])
        return files
    report.check("guest_console_login_configuration", login)

    def writable():
        path = "/var/lib/xen/images/guest1/rootfs.ext4"
        info = fs.stat(path)
        mode = re.search(r"Mode:\s+(0[0-7]+)", info)
        if not mode or not int(mode.group(1), 8) & 0o200:
            raise CheckError("Guest backing file is not owner-writable")
        mounts = fs.text("/etc/fstab")
        for line in mounts.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            fields = line.split()
            if len(fields) >= 4 and fields[1] in ("/", "/var", "/var/lib", "/var/lib/xen", "/var/lib/xen/images"):
                if "ro" in fields[3].split(","):
                    raise CheckError("Guest backing file is beneath a read-only fstab mount")
        return "Owner-writable backing file and no read-only covering fstab entry; runtime I/O still needs Pi4 validation"
    report.check("guest_backing_file_writable_configuration", writable)

    def ssh_service():
        candidates = ["/etc/systemd/system/multi-user.target.wants/sshd.service",
                      "/etc/systemd/system/sockets.target.wants/sshd.socket"]
        enabled = [item for item in candidates if fs.exists(item)]
        if not enabled:
            raise CheckError("No enabled sshd service or socket")
        return fs.require(enabled)
    report.check("dom0_ssh_service", ssh_service)

    def network_and_ssh_config():
        network = "/etc/systemd/network/20-wired.network"
        enabled = "/etc/systemd/system/multi-user.target.wants/systemd-networkd.service"
        fs.require([network, enabled, "/etc/ssh/sshd_config.d/10-pi4-xen.conf"])
        if not re.search(r"^DHCP\s*=\s*(yes|ipv4)\s*$", fs.text(network), re.MULTILINE):
            raise CheckError("Dom0 wired network does not request DHCP")
        root_config = fs.text("/etc/ssh/sshd_config")
        first_directive = next((line.strip() for line in root_config.splitlines()
                                if line.strip() and not line.lstrip().startswith("#")), "")
        if first_directive != "Include /etc/ssh/sshd_config.d/*.conf":
            raise CheckError("sshd_config must load the lab drop-in before other directives")
        text = fs.text("/etc/ssh/sshd_config.d/10-pi4-xen.conf")
        for line in ("PermitRootLogin prohibit-password", "PubkeyAuthentication yes", "PasswordAuthentication no", "UsePAM yes"):
            if line not in [item.strip() for item in text.splitlines()]:
                raise CheckError(f"Missing SSH setting {line}")
        return {"network": network, "sshd_drop_in": "/etc/ssh/sshd_config.d/10-pi4-xen.conf"}
    report.check("dom0_wired_network_and_ssh_configuration", network_and_ssh_config)
    try:
        keyfile = "/root/.ssh/authorized_keys"
        lines = fs.text(keyfile).splitlines() if fs.exists(keyfile) else []
        keys = [line for line in lines if re.match(r"^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(?:256|384|521)) [A-Za-z0-9+/=]+(?: |$)", line)]
        if not keys:
            report.add("dom0_ssh_public_key", "BLOCKED", "Run scripts/configure-access.py, verify local/credentials/id_ed25519.pub, and rebuild; no usable root SSH public key is embedded")
        else:
            report.add("dom0_ssh_public_key", "PASS", {"key_count": len(keys), "path": keyfile})
    except (CheckError, OSError, UnicodeError) as exc:
        report.add("dom0_ssh_public_key", "FAIL", str(exc))


def inspect_boot(report, boot, deploy):
    def firmware():
        text = (boot / "config.txt").read_text()
        required = {"arm_64bit": "1", "enable_uart": "1", "enable_gic": "1", "kernel": "u-boot.bin"}
        pairs = {key: value.strip() for key, value in re.findall(r"^\s*([a-zA-Z0-9_]+)\s*=\s*([^#\r\n]+)", text, re.MULTILINE)}
        for key, value in required.items():
            if pairs.get(key) != value:
                raise CheckError(f"config.txt requires {key}={value}")
        return required
    report.check("firmware_boot_configuration", firmware)

    def boot_script():
        raw = (boot / "boot.scr").read_bytes()
        if len(raw) < 72 or struct.unpack_from(">I", raw)[0] != 0x27051956:
            raise CheckError("boot.scr is not a legacy U-Boot script image")
        if raw[30] != 6 or raw[31] != 0:
            raise CheckError("Expected an uncompressed U-Boot script payload")
        import zlib
        header = bytearray(raw[:64])
        expected_header = struct.unpack_from(">I", header, 4)[0]
        header[4:8] = bytes(4)
        if zlib.crc32(header) & 0xFFFFFFFF != expected_header:
            raise CheckError("boot.scr header CRC mismatch")
        size, expected_crc = struct.unpack_from(">II", raw, 12)[0], struct.unpack_from(">I", raw, 24)[0]
        payload = raw[64:64 + size]
        if len(payload) != size or zlib.crc32(payload) & 0xFFFFFFFF != expected_crc:
            raise CheckError("boot.scr payload size/CRC mismatch")
        # mkimage -T script stores a length table terminated by a zero word.
        first_length, terminator = struct.unpack_from(">II", payload)
        if terminator != 0 or len(payload) < 8 + first_length:
            raise CheckError("Unsupported multi-component or truncated U-Boot script")
        script_bytes = payload[8:8 + first_length]
        text = script_bytes.decode()
        bootcmd = Path(deploy) / "boot.cmd"
        if not bootcmd.is_file():
            raise CheckError("Missing deploy/boot.cmd needed to compare deployed and embedded scripts")
        if script_bytes.rstrip(b"\x00") != bootcmd.read_bytes().rstrip(b"\x00"):
            raise CheckError("Embedded boot.scr differs from deploy/boot.cmd")
        if "@@" in text:
            raise CheckError("Unexpanded boot script template markers")
        for token in ("xen,xen-bootargs", "xen,dom0-bootargs", "console=hvc0", "root=PARTUUID=", "booti"):
            if token not in text:
                raise CheckError(f"Missing boot script requirement: {token}")
        if not re.search(r"\bpart\s+uuid\b", text):
            raise CheckError("Boot script must obtain the actual root partition UUID")
        if not re.search(r"\bfdt\s+get\s+value\b.*?/aliases\s+serial0", text):
            raise CheckError("Boot script must derive the UART from firmware's serial0 alias")
        addresses = {}
        for name, value in re.findall(r"^\s*setenv\s+(\w+)\s+[\"']?(0x[0-9a-fA-F]+)[\"']?\s*$", text, re.MULTILINE):
            addresses[name] = int(value, 16)
        ranges = []
        for name, filename in (("xen_loadaddr", "xen"), ("kernel_loadaddr", "Image")):
            if name not in addresses:
                raise CheckError(f"Missing literal load address {name}")
            size = (boot / filename).stat().st_size
            if filename == "Image":
                size = max(size, arm64_image(boot / filename)["runtime_size"])
            ranges.append((addresses[name], addresses[name] + size, filename))
        fdt_names = [name for name in ("xen_fdt_addr", "fdt_loadaddr", "fdt_relocaddr", "fdt_safeaddr") if name in addresses]
        if not fdt_names:
            raise CheckError("Missing literal safe FDT relocation address")
        fdt = addresses[fdt_names[0]]
        ranges.append((fdt, fdt + 1024 * 1024, "FDT reservation"))
        ordered = sorted(ranges)
        for left, right in zip(ordered, ordered[1:]):
            if left[1] > right[0]:
                raise CheckError(f"Load ranges overlap: {left[2]} and {right[2]}")
        if ordered[-1][1] > 512 * 1024 * 1024:
            raise CheckError("Boot payload ranges exceed the conservative first 512 MiB RAM window")
        return {"boot_cmd_sha256": sha256(bootcmd), "ranges": ranges,
                "note": "Static ranges do not prove firmware/U-Boot runtime reservations or EL2 entry"}
    report.check("boot_script_consistency_and_ranges", boot_script)
    report.add("xen_el2_entry_and_firmware_reservations", "NOT_RUN", "Check firmware/U-Boot/Xen startup on real Pi4; binary packaging alone cannot establish EL2 entry")


if __name__ == "__main__":
    sys.exit(main())
