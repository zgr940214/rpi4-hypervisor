"""Reject substituted guest payloads; fixtures are not bootable OS images."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location('check_image', Path(__file__).resolve().parents[1] / 'scripts/check-image.py')
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class Files:
    def __init__(self, contents):
        self.contents = contents

    def read(self, name):
        return self.contents[name]

    def text(self, name):
        return self.read(name).decode()


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.deploy = self.root / 'deploy'
        self.deploy.mkdir()
        self.guest = self.root / 'packaged.ext4'
        self.guest.write_bytes(b'synthetic guest rootfs')
        self.kernel = self.root / 'packaged-Image'
        self.kernel.write_bytes(b'synthetic kernel')
        manifest = b'busybox aarch64 1.36.1\n'
        metadata = {'schema_version': 1, 'recipe': 'linux-yocto', 'version': '6.6',
                    'kernel_release': '6.6-fixture', 'machine': 'raspberrypi4-64',
                    'source_revision': 'a' * 40}
        (self.deploy / 'pi4-xen-kernel.json').write_text(json.dumps(metadata))
        self.provenance = {'schema_version': 1, 'build_system': 'yocto-bitbake',
                           'guest_image_recipe': 'pi4-guest1-image',
                           'machine': 'raspberrypi4-64', 'distro': 'pi4-xen',
                           'kernel': metadata, 'artifacts': {}}
        for name, deployed, data in [('Image', 'Image', self.kernel.read_bytes()),
                                     ('rootfs.ext4', 'pi4-guest1.ext4', self.guest.read_bytes()),
                                     ('guest.manifest', 'pi4-guest1.manifest', manifest)]:
            (self.deploy / deployed).write_bytes(data)
            self.provenance['artifacts'][name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        self.fs = Files({'/var/lib/xen/images/guest1/guest.manifest': manifest})
        self.save_provenance()

    def save_provenance(self):
        self.fs.contents['/var/lib/xen/images/guest1/provenance.json'] = json.dumps(self.provenance).encode()

    def check(self):
        return CHECK.built_guest_payloads(self.fs, self.guest, self.kernel, self.deploy)

    def test_packaged_bytes_match_build_outputs(self):
        self.assertEqual(self.check(), self.provenance)

    def test_guest_modified_after_packaging_is_rejected(self):
        self.guest.write_bytes(b'replacement guest OS')
        with self.assertRaisesRegex(CHECK.CheckError, 'recorded build provenance'):
            self.check()

    def test_replacement_with_matching_embedded_hash_still_rejected(self):
        self.guest.write_bytes(b'replacement guest OS')
        self.provenance['artifacts']['rootfs.ext4'] = {'sha256': CHECK.sha256(self.guest), 'bytes': self.guest.stat().st_size}
        self.save_provenance()
        with self.assertRaisesRegex(CHECK.CheckError, 'actual Yocto deploy output'):
            self.check()

    def test_other_build_kernel_metadata_rejected(self):
        self.provenance['kernel']['source_revision'] = 'b' * 40
        self.save_provenance()
        with self.assertRaisesRegex(CHECK.CheckError, 'built Pi4 kernel'):
            self.check()

    def test_manifest_from_different_build_rejected(self):
        (self.deploy / 'pi4-guest1.manifest').write_bytes(b'different package list\n')
        with self.assertRaisesRegex(CHECK.CheckError, 'actual Yocto deploy output'):
            self.check()

    def test_non_yocto_build_is_rejected(self):
        self.provenance['build_system'] = 'debootstrap'
        self.save_provenance()
        with self.assertRaisesRegex(CHECK.CheckError, 'Yocto guest provenance'):
            self.check()

    def test_rootfs_identity_must_be_guest_recipe_for_pi4(self):
        identity = {'schema_version': 1, 'build_system': 'yocto-bitbake',
                    'image_recipe': 'pi4-guest1-image', 'machine': 'raspberrypi4-64', 'distro': 'pi4-xen'}
        self.fs.contents['/etc/pi4-xen-build.json'] = json.dumps(identity).encode()
        self.assertEqual(CHECK.build_identity(self.fs, 'pi4-guest1-image'), identity)
        for field, value in [('machine', 'qemuarm64'), ('image_recipe', 'pi4-xen-dom0-image'), ('build_system', 'debootstrap')]:
            with self.subTest(field=field):
                self.fs.contents['/etc/pi4-xen-build.json'] = json.dumps(dict(identity, **{field: value})).encode()
                with self.assertRaises(CHECK.CheckError):
                    CHECK.build_identity(self.fs, 'pi4-guest1-image')

    def test_boot_xen_must_match_same_build(self):
        boot = self.root / 'boot'
        boot.mkdir()
        (boot / 'Image').write_bytes(self.kernel.read_bytes())
        (boot / 'xen').write_bytes(b'other Xen')
        (self.deploy / 'xen-raspberrypi4-64').write_bytes(b'Yocto Xen')
        with self.assertRaisesRegex(CHECK.CheckError, 'Boot xen differs'):
            CHECK.built_boot_payloads(boot, self.deploy)


if __name__ == '__main__':
    unittest.main()
