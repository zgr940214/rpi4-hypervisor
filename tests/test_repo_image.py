"""Synthetic integrity/gating tests only; these do not build or boot a Pi4 image."""
import hashlib
import importlib.util
import json
import lzma
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('repo_image', ROOT / 'scripts/repo-image.py')
DELIVERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DELIVERY)


class RepositoryImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifacts = self.root / 'artifacts'
        (self.artifacts / 'checks').mkdir(parents=True)
        self.image = self.artifacts / DELIVERY.IMAGE_NAME
        self.payload = os.urandom(8192) + b'\0' * 65536
        self.image.write_bytes(self.payload)
        self.actual = DELIVERY.fingerprint(self.image)
        self.config = self.artifacts / 'pi4-xen-kernel.config'
        self.config.write_text('# synthetic integrity-test fixture\n')
        self.static_file = self.artifacts / 'checks/image-checks.json'
        self.checked_file = self.artifacts / 'checks/artifact.json'
        self.versions_file = self.artifacts / 'versions.json'
        self.qemu_file = self.root / 'synthetic-qemu-report.json'
        self.output = self.artifacts / 'repository-image'
        self.restored = self.root / 'restored.img'
        static_checks = [{'name': name, 'status': 'PASS', 'detail': {}}
                         for name in DELIVERY.STATIC_CHECKS]
        static_checks[0]['detail'] = self.actual
        next(item for item in static_checks if item['name'] == 'boot_payloads_match_build')['detail'] = {
            'xen': 'a' * 64, 'Image': 'b' * 64}
        static_checks.extend({'name': name, 'status': 'NOT_RUN'} for name in
                             ['ssh_login', 'pi4_hardware_boot', 'xen_el2_entry_and_firmware_reservations'])
        self.static = {'static_status': 'PASS', 'checks': static_checks}
        self.write(self.static_file, self.static)
        self.write(self.checked_file, {**self.actual, 'kernel_config_sha256': DELIVERY.fingerprint(self.config)['sha256']})
        versions = {'build_system': 'yocto-bitbake', 'machine': 'raspberrypi4-64',
                    'distro': 'pi4-xen', 'bytes': len(self.payload), 'selected_recipes': {}}
        for recipe, pn in [('pi4-xen-dom0-image', 'pi4-xen-dom0-image'),
                           ('pi4-guest1-image', 'pi4-guest1-image'), ('virtual/kernel', 'linux-yocto'),
                           ('xen', 'xen'), ('xen-tools', 'xen-tools')]:
            versions['selected_recipes'][recipe] = {'PN': pn}
        self.write(self.versions_file, versions)
        runtime = {'rootfs': self.actual, 'xen': {'bytes': 1, 'sha256': 'a' * 64},
                   'kernel': {'bytes': 2, 'sha256': 'b' * 64}}
        self.qemu = {'status': 'PASS', 'pi4_image_build': 'VERIFIED_SELF_BUILT_ARTIFACT',
                     'pi4_hardware': 'NOT_RUN', 'artifacts': runtime,
                     'checks': [{'name': name, 'status': 'PASS', 'detail': {}}
                                for name in DELIVERY.QEMU_CHECKS],
                     'yocto_provenance': {'schema_version': 1, 'build_system': 'yocto-bitbake',
                         'machine': 'raspberrypi4-64', 'build_versions': versions,
                         'runtime_artifacts': runtime,
                         'evidence_artifacts': {'versions_file': DELIVERY.fingerprint(self.versions_file),
                             'checks_file': DELIVERY.fingerprint(self.static_file),
                             'kernel_config': DELIVERY.fingerprint(self.config)}}}
        self.qemu['checks'][-1]['detail'] = {'sha256_before_and_after': self.actual['sha256']}
        self.write(self.qemu_file, self.qemu)

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value) + '\n')

    def pack(self):
        return DELIVERY.pack(self.artifacts, self.qemu_file, self.output, chunk_size=512)

    def manifest(self):
        return self.output / 'manifest.json'

    def assert_not_published(self):
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.artifacts.glob('.repository-image-*')))

    def assert_no_restore_temporary(self):
        self.assertFalse(list(self.root.glob('.restored.img-*.tmp')))

    def test_multichunk_roundtrip_and_idempotent_restore(self):
        result = self.pack()
        self.assertGreater(len(result['chunks']), 2)
        self.assertTrue(all(item['bytes'] <= 512 for item in result['chunks']))
        compressed = b''.join((self.output / item['name']).read_bytes() for item in result['chunks'])
        self.assertEqual(lzma.decompress(compressed), self.payload)
        self.assertEqual(hashlib.sha256(compressed).hexdigest(), result['compressed']['sha256'])
        self.assertEqual(DELIVERY.restore(self.manifest(), self.restored), self.actual)
        self.assertEqual(self.restored.read_bytes(), self.payload)
        original_inode = self.restored.stat().st_ino
        DELIVERY.restore(self.manifest(), self.restored)
        self.assertEqual(self.restored.stat().st_ino, original_inode)
        self.assert_no_restore_temporary()

    def test_absent_image_cannot_publish(self):
        self.image.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing built Yocto image'):
            self.pack()
        self.assert_not_published()

    def test_failed_or_stale_static_report_cannot_publish(self):
        for changed in [{'static_status': 'FAIL'}, {'checks': []}]:
            self.write(self.static_file, {**self.static, **changed})
            with self.assertRaises(ValueError):
                self.pack()
            self.assert_not_published()
        self.write(self.static_file, self.static)
        self.image.write_bytes(b'different current image')
        with self.assertRaisesRegex(ValueError, 'different image'):
            self.pack()
        self.assert_not_published()

    def test_other_pending_static_check_remains_rejected(self):
        self.static['checks'].append({'name': 'unexpected_unfinished_inspection', 'status': 'NOT_RUN'})
        self.write(self.static_file, self.static)
        with self.assertRaisesRegex(ValueError, 'has not passed'):
            self.pack()
        self.assert_not_published()

    def test_debian_qemu_pass_is_not_a_yocto_pass(self):
        self.qemu['pi4_image_build'] = 'NOT_RUN'
        self.write(self.qemu_file, self.qemu)
        with self.assertRaisesRegex(ValueError, 'Yocto image QEMU validation'):
            self.pack()
        self.assert_not_published()

    def test_pending_qemu_check_and_wrong_disk_are_rejected(self):
        self.qemu['checks'][2]['status'] = 'NOT_RUN'
        self.write(self.qemu_file, self.qemu)
        with self.assertRaisesRegex(ValueError, 'has not passed'):
            self.pack()
        self.qemu['checks'][2]['status'] = 'PASS'
        self.qemu['artifacts']['rootfs'] = {'bytes': len(self.payload), 'sha256': '0' * 64}
        self.write(self.qemu_file, self.qemu)
        with self.assertRaisesRegex(ValueError, 'different disk image'):
            self.pack()
        self.assert_not_published()

    def test_changed_evidence_is_rejected(self):
        self.static['scope'] = 'changed after QEMU'
        self.write(self.static_file, self.static)
        with self.assertRaisesRegex(ValueError, 'different image-checks.json'):
            self.pack()
        self.assert_not_published()

    def test_external_boot_payload_cannot_differ_from_static_image(self):
        # QEMU and its embedded provenance agree, but the actual image check does not.
        self.qemu['artifacts']['kernel']['sha256'] = 'c' * 64
        self.write(self.qemu_file, self.qemu)
        with self.assertRaisesRegex(ValueError, 'inspected image boot payload'):
            self.pack()
        self.assert_not_published()

    def test_image_changed_during_pack_leaves_no_chunks(self):
        verify = DELIVERY.verify_delivery

        def mutate(*args):
            result = verify(*args)
            self.image.write_bytes(self.payload + b'changed')
            return result

        with patch.object(DELIVERY, 'verify_delivery', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'Image changed'):
                self.pack()
        self.assert_not_published()

    def test_pack_refuses_existing_directory_and_oversized_chunks(self):
        with self.assertRaisesRegex(ValueError, 'at most 48 MiB'):
            DELIVERY.pack(self.artifacts, self.qemu_file, self.output, DELIVERY.MAX_CHUNK + 1)
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.pack()

    def test_corrupt_chunk_preserves_existing_output_even_with_force(self):
        manifest = self.pack()
        chunk = self.output / manifest['chunks'][-1]['name']
        data = chunk.read_bytes()
        chunk.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
        self.restored.write_bytes(b'existing image')
        with self.assertRaises((ValueError, lzma.LZMAError)):
            DELIVERY.restore(self.manifest(), self.restored, force=True)
        self.assertEqual(self.restored.read_bytes(), b'existing image')
        self.assert_no_restore_temporary()

    def test_missing_chunk_leaves_no_output(self):
        manifest = self.pack()
        (self.output / manifest['chunks'][1]['name']).unlink()
        with self.assertRaisesRegex(ValueError, 'Missing or non-regular chunk'):
            DELIVERY.restore(self.manifest(), self.restored)
        self.assertFalse(self.restored.exists())
        self.assert_no_restore_temporary()

    def test_compressed_and_restored_hashes_are_checked(self):
        original = self.pack()
        for key in ['compressed', 'image']:
            changed = json.loads(json.dumps(original))
            changed[key]['sha256'] = '0' * 64
            self.write(self.manifest(), changed)
            with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                DELIVERY.restore(self.manifest(), self.restored)
            self.assertFalse(self.restored.exists())
            self.assert_no_restore_temporary()

    def test_truncated_xz_is_rejected_even_with_updated_chunk_hash(self):
        manifest = self.pack()
        last = manifest['chunks'][-1]
        path = self.output / last['name']
        path.write_bytes(path.read_bytes()[:-8])
        last.update(DELIVERY.fingerprint(path))
        compressed = b''.join((self.output / item['name']).read_bytes() for item in manifest['chunks'])
        manifest['compressed'].update(bytes=len(compressed), sha256=hashlib.sha256(compressed).hexdigest())
        self.write(self.manifest(), manifest)
        with self.assertRaisesRegex(ValueError, 'Truncated XZ stream'):
            DELIVERY.restore(self.manifest(), self.restored)
        self.assertFalse(self.restored.exists())

    def test_unsafe_names_and_symlinks_are_rejected(self):
        original = self.pack()
        for name in ['../outside', '/absolute', r'..\outside', '.', 'a/b']:
            manifest = json.loads(json.dumps(original))
            manifest['chunks'][0]['name'] = name
            self.write(self.manifest(), manifest)
            with self.assertRaisesRegex(ValueError, 'Unsafe manifest filename'):
                DELIVERY.restore(self.manifest(), self.restored)
        self.write(self.manifest(), original)
        part = self.output / original['chunks'][0]['name']
        external = self.root / 'external'
        part.rename(external)
        part.symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'non-regular chunk'):
            DELIVERY.restore(self.manifest(), self.restored)
        self.assertFalse(self.restored.exists())

    def test_existing_different_image_requires_force(self):
        self.pack()
        self.restored.write_bytes(b'keep this image')
        with self.assertRaisesRegex(ValueError, 'use --force'):
            DELIVERY.restore(self.manifest(), self.restored)
        self.assertEqual(self.restored.read_bytes(), b'keep this image')
        DELIVERY.restore(self.manifest(), self.restored, force=True)
        self.assertEqual(self.restored.read_bytes(), self.payload)


if __name__ == '__main__':
    unittest.main()
