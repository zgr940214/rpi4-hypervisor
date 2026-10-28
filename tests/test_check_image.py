"""Unit and host-tool integration tests; these are not Pi4 image validation."""

import importlib.util
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from contextlib import redirect_stdout


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-image.py"
SPEC = importlib.util.spec_from_file_location("check_image", SCRIPT)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class ImageCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def card(self, entries=None, length=8192):
        image = self.root / "card.wic"
        header = bytearray(512)
        header[510:] = b"\x55\xaa"
        if entries is None:
            entries = [(0x80, 0x0C, 1, 3), (0, 0x83, 4, 12)]
        for index, (flag, kind, start, count) in enumerate(entries):
            offset = 446 + index * 16
            header[offset] = flag
            header[offset + 4] = kind
            struct.pack_into("<II", header, offset + 8, start, count)
        with image.open("wb") as stream:
            stream.write(header)
            stream.truncate(length)
        return image

    def test_valid_two_partition_layout(self):
        result = CHECK.partitions(self.card())
        self.assertEqual(result[0]["offset"], 512)
        self.assertEqual(result[1]["size"], 12 * 512)

    def test_rootfs_is_not_card_image(self):
        image = self.root / "rootfs.ext4"
        image.write_bytes(bytes(8192))
        with self.assertRaisesRegex(CHECK.CheckError, "MBR signature"):
            CHECK.partitions(image)

    def test_gpt_is_explicitly_unsupported(self):
        with self.assertRaisesRegex(CHECK.CheckError, "GPT"):
            CHECK.partitions(self.card([(0, 0xEE, 1, 15)]))

    def test_truncated_partition_rejected(self):
        with self.assertRaisesRegex(CHECK.CheckError, "beyond image"):
            CHECK.partitions(self.card(length=8000))

    def test_overlapping_partitions_rejected(self):
        with self.assertRaisesRegex(CHECK.CheckError, "overlap"):
            CHECK.partitions(self.card([(0x80, 0x0C, 1, 5), (0, 0x83, 4, 12)]))

    def test_extra_partition_rejected(self):
        with self.assertRaisesRegex(CHECK.CheckError, "exactly"):
            CHECK.partitions(self.card([(0x80, 0x0C, 1, 3), (0, 0x83, 4, 5), (0, 0x83, 9, 7)]))

    def test_invalid_boot_flag_rejected(self):
        with self.assertRaisesRegex(CHECK.CheckError, "Invalid MBR"):
            CHECK.partitions(self.card([(0x90, 0x0C, 1, 3), (0, 0x83, 4, 12)]))

    def test_sparse_copy_is_exact_and_source_is_unchanged(self):
        source = self.root / "source"
        source.write_bytes(b"header" + bytes(1024 * 1024) + b"data" + b"tail")
        original = CHECK.sha256(source)
        dest = self.root / "partition"
        CHECK.sparse_copy(source, 6, 1024 * 1024 + 4, dest)
        self.assertEqual(dest.read_bytes(), bytes(1024 * 1024) + b"data")
        self.assertEqual(CHECK.sha256(source), original)

    def test_sparse_copy_reports_truncation(self):
        source = self.root / "short"
        source.write_bytes(b"abc")
        with self.assertRaisesRegex(CHECK.CheckError, "EOF"):
            CHECK.sparse_copy(source, 0, 10, self.root / "out")

    @staticmethod
    def config():
        return """name = 'guest1'
memory = 256
vcpus = 1
kernel = '/var/lib/xen/images/guest1/Image'
extra = 'console=hvc0 root=/dev/xvda rw rootwait'
disk = ['format=raw,vdev=xvda,access=rw,backendtype=phy,target=/var/lib/xen/images/guest1/rootfs.ext4']
vif = []
"""

    def test_literal_guest_config(self):
        parsed = CHECK.parse_guest_config(self.config())
        self.assertEqual(parsed["memory"], 256)

    def test_guest_disk_target_before_parameters_rejected(self):
        broken = self.config().replace(
            "format=raw,vdev=xvda,access=rw,backendtype=phy,target=/var/lib/xen/images/guest1/rootfs.ext4",
            "target=/var/lib/xen/images/guest1/rootfs.ext4,format=raw,vdev=xvda,access=rw,backendtype=phy")
        with self.assertRaisesRegex(CHECK.CheckError, "target= must be last"):
            CHECK.parse_guest_config(broken)

    def test_partitioned_guest_root_rejected(self):
        with self.assertRaisesRegex(CHECK.CheckError, "raw xvda"):
            CHECK.parse_guest_config(self.config().replace("root=/dev/xvda ", "root=/dev/xvda1 "))

    def test_readonly_guest_disk_rejected(self):
        with self.assertRaisesRegex(CHECK.CheckError, "phy/loop"):
            CHECK.parse_guest_config(self.config().replace("access=rw", "access=ro"))

    def test_unexpected_backend_rejected(self):
        with self.assertRaisesRegex(CHECK.CheckError, "phy/loop"):
            CHECK.parse_guest_config(self.config().replace("backendtype=phy", "backendtype=qdisk"))

    def test_guest_config_code_is_never_executed(self):
        target = self.root / "must-not-exist"
        payload = self.config() + f"__import__('pathlib').Path({str(target)!r}).touch()\n"
        with self.assertRaisesRegex(CHECK.CheckError, "literal assignments"):
            CHECK.parse_guest_config(payload)
        self.assertFalse(target.exists())

    def test_duplicate_guest_setting_rejected(self):
        with self.assertRaisesRegex(CHECK.CheckError, "Duplicate"):
            CHECK.parse_guest_config(self.config() + "vcpus = 2\n")

    def test_nonliteral_guest_setting_rejected(self):
        with self.assertRaisesRegex(CHECK.CheckError, "Nonliteral"):
            CHECK.parse_guest_config(self.config().replace("memory = 256", "memory = 2 * 128"))

    def test_filesystem_path_escape_rejected(self):
        with self.assertRaisesRegex(CHECK.CheckError, "escapes"):
            CHECK.clean_path("/../../outside")
        self.assertEqual(CHECK.clean_path("/etc/../usr/bin/xl"), "/usr/bin/xl")

    def test_debugfs_command_injection_rejected(self):
        with self.assertRaisesRegex(CHECK.CheckError, "Unsupported"):
            CHECK.clean_path("/etc/file\nwrite /outside /inside")

    def test_kernel_module_is_not_accepted_for_early_root_driver(self):
        config = self.root / ".config"
        names = ["ARM64", "XEN", "HVC_XEN", "XEN_BLKDEV_FRONTEND", "EXT4_FS", "DEVTMPFS", "DEVTMPFS_MOUNT"]
        config.write_text("".join("CONFIG_" + name + "=y\n" for name in names).replace("CONFIG_EXT4_FS=y", "CONFIG_EXT4_FS=m"))
        with self.assertRaisesRegex(CHECK.CheckError, "CONFIG_EXT4_FS"):
            CHECK.kernel_config(config, guest=True)

    def test_hardware_is_always_not_run(self):
        report = CHECK.Report(self.root / "report")
        report.add("synthetic_test", "FAIL", "This is a unit test, not a real image")
        with redirect_stdout(io.StringIO()):
            result = report.finish(self.root / "fake.wic")
        content = json.loads((self.root / "report" / "image-checks.json").read_text())
        self.assertEqual(result, 1)
        self.assertEqual(content["static_status"], "FAIL")
        self.assertEqual(content["checks"][-1]["status"], "NOT_RUN")

    def test_arm64_magic_is_required(self):
        image = self.root / "Image"
        image.write_bytes(b"\x1f\x8b" + bytes(62))
        with self.assertRaisesRegex(CHECK.CheckError, "uncompressed AArch64"):
            CHECK.arm64_image(image)

    def make_boot_fixture(self, kernel_address="0x04000000"):
        boot = self.root / "boot"
        deploy = self.root / "deploy"
        boot.mkdir()
        deploy.mkdir()
        (boot / "config.txt").write_text("arm_64bit=1\nenable_uart=1\nenable_gic=1\nkernel=u-boot.bin\n")
        script = f"""setenv xen_loadaddr 0x00200000
setenv kernel_loadaddr {kernel_address}
setenv xen_fdt_addr 0x08000000
fdt get value xen_uart /aliases serial0
part uuid mmc 1:2 rootfs_partuuid
fdt set /chosen xen,xen-bootargs 'console=dtuart'
fdt set /chosen xen,dom0-bootargs 'console=hvc0 root=PARTUUID=x rw'
booti ${{xen_loadaddr}} - ${{xen_fdt_addr}}
""".encode()
        (deploy / "boot.cmd").write_bytes(script)
        payload = struct.pack(">II", len(script), 0) + script
        header = bytearray(64)
        struct.pack_into(">I", header, 0, 0x27051956)
        struct.pack_into(">I", header, 12, len(payload))
        struct.pack_into(">I", header, 24, zlib.crc32(payload))
        header[30] = 6
        struct.pack_into(">I", header, 4, zlib.crc32(header))
        (boot / "boot.scr").write_bytes(header + payload)
        linux = bytearray(64)
        linux[56:60] = b"ARM\x64"
        struct.pack_into("<Q", linux, 16, 1024 * 1024)
        (boot / "Image").write_bytes(linux)
        (boot / "xen").write_bytes(bytes(4096))
        return boot, deploy

    def test_boot_script_crc_failure_is_reported(self):
        boot, deploy = self.make_boot_fixture()
        data = bytearray((boot / "boot.scr").read_bytes())
        data[-1] ^= 1
        (boot / "boot.scr").write_bytes(data)
        report = CHECK.Report(self.root / "report")
        CHECK.inspect_boot(report, boot, deploy)
        failure = next(item for item in report.checks if item["name"] == "boot_script_consistency_and_ranges")
        self.assertEqual(failure["status"], "FAIL")
        self.assertIn("CRC", failure["detail"])

    def test_runtime_kernel_size_cannot_overlap_fdt(self):
        boot, deploy = self.make_boot_fixture(kernel_address="0x07f80000")
        report = CHECK.Report(self.root / "report")
        CHECK.inspect_boot(report, boot, deploy)
        failure = next(item for item in report.checks if item["name"] == "boot_script_consistency_and_ranges")
        self.assertEqual(failure["status"], "FAIL")
        self.assertIn("overlap", failure["detail"])

    def test_packaged_script_cannot_differ_from_deploy_script(self):
        boot, deploy = self.make_boot_fixture()
        (deploy / "boot.cmd").write_text("different script")
        report = CHECK.Report(self.root / "report")
        CHECK.inspect_boot(report, boot, deploy)
        failure = next(item for item in report.checks if item["name"] == "boot_script_consistency_and_ranges")
        self.assertEqual(failure["status"], "FAIL")
        self.assertIn("differs", failure["detail"])


@unittest.skipUnless(shutil.which("mkfs.ext4") and shutil.which("debugfs"), "requires e2fsprogs host tools")
class Ext4IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        tree = self.root / "tree"
        (tree / "usr/bin").mkdir(parents=True)
        (tree / "usr/bin/busybox").write_bytes(b"fixture executable")
        (tree / "bin").symlink_to("usr/bin")
        (tree / "usr/bin/sh").symlink_to("busybox")
        (tree / "etc").mkdir()
        (tree / "etc/hostname").write_text("guest1\n")
        (tree / "etc/cycle").symlink_to("cycle")
        self.image = self.root / "fixture.ext4"
        with self.image.open("wb") as stream:
            stream.truncate(16 * 1024 * 1024)
        subprocess.run(["mkfs.ext4", "-q", "-F", "-d", str(tree), str(self.image)], check=True, capture_output=True)
        self.fs = CHECK.Ext4(self.image, self.root)

    def test_readonly_ext4_extraction_and_directory_symlinks(self):
        before = CHECK.sha256(self.image)
        self.assertEqual(self.fs.text("/etc/hostname"), "guest1\n")
        self.assertEqual(self.fs.resolve("/bin/sh"), "/usr/bin/busybox")
        self.assertEqual(self.fs.read("/bin/sh"), b"fixture executable")
        self.assertEqual(CHECK.sha256(self.image), before)

    def test_missing_inode_is_detected_despite_debugfs_zero_exit(self):
        with self.assertRaisesRegex(CHECK.CheckError, "Missing inode"):
            self.fs.read("/etc/missing")

    def test_symlink_loop_is_bounded(self):
        with self.assertRaisesRegex(CHECK.CheckError, "Symlink loop"):
            self.fs.resolve("/etc/cycle")


if __name__ == "__main__":
    unittest.main()
