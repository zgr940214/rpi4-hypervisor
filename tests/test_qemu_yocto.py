"""Provenance rejection tests with synthetic metadata, not a Yocto build/boot test."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('prepare_yocto', ROOT / 'scripts/qemu/prepare-yocto.py')
PREPARE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARE)


class YoctoInputGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.lock = self.directory / 'sources.lock.json'
        self.lock.write_text('{"synthetic_unit_test": true}\n')

    def fixture(self):
        """Synthetic byte/container metadata for testing rejection paths only."""
        (self.directory / 'checks').mkdir()
        data = bytearray(8192)
        data[510:512] = b'\x55\xaa'
        for index, (kind, start, count) in enumerate([(0x0C, 1, 3), (0x83, 4, 12)]):
            entry = 446 + index * 16
            data[entry + 4] = kind
            struct.pack_into('<II', data, entry + 8, start, count)
        self.image = self.directory / 'pi4-xen-dom0-guest1.img'
        self.image.write_bytes(data)
        self.config = self.directory / 'pi4-xen-kernel.config'
        self.config.write_bytes((ROOT / 'meta-pi4-xen-lab/recipes-kernel/linux/files/pi4-xen.cfg').read_bytes())
        self.versions = {'build_system': 'yocto-bitbake', 'machine': 'raspberrypi4-64',
                         'distro': 'pi4-xen', 'source_lock': json.loads(self.lock.read_text()),
                         'selected_recipes': {name: {'PN': name} for name in
                                              ['pi4-xen-dom0-image', 'pi4-guest1-image', 'xen', 'xen-tools']}}
        self.versions['selected_recipes']['virtual/kernel'] = {'PN': 'linux-yocto'}
        self.save_versions()
        self.checks = self.directory / 'checks/image-checks.json'
        records = [{'name': name, 'status': 'PASS', 'detail': {}} for name in
                   ['dom0_yocto_build_identity', 'guest_yocto_build_identity',
                    'guest_payloads_match_build', 'boot_payloads_match_build',
                    'shared_kernel_identity']]
        records.append({'name': 'image_sha256', 'status': 'PASS',
                        'detail': {'sha256': PREPARE.CHECK.sha256(self.image)}})
        self.checks.write_text(json.dumps({'static_status': 'PASS', 'synthetic_unit_test': True,
                                          'checks': records}))
        self.update_checked_hashes()

    def save_versions(self):
        (self.directory / 'versions.json').write_text(json.dumps(self.versions))

    def update_checked_hashes(self):
        data = PREPARE.artifact(self.image)
        data['kernel_config_sha256'] = PREPARE.CHECK.sha256(self.config)
        (self.directory / 'checks/artifact.json').write_text(json.dumps(data))

    def validate(self):
        return PREPARE.validate_export(self.directory, self.lock)

    def test_missing_image_has_no_debian_fallback(self):
        with self.assertRaisesRegex(ValueError, 'Missing Yocto build output'):
            self.validate()

    def test_non_yocto_kernel_rejected(self):
        self.fixture()
        self.versions['selected_recipes']['virtual/kernel']['PN'] = 'debian-linux-image-arm64'
        self.save_versions()
        with self.assertRaisesRegex(ValueError, 'self-built Yocto recipe provenance'):
            self.validate()

    def test_other_machine_export_rejected(self):
        self.fixture()
        self.versions['machine'] = 'qemuarm64'
        self.save_versions()
        with self.assertRaisesRegex(ValueError, 'raspberrypi4-64 Yocto build'):
            self.validate()

    def test_legacy_pass_report_without_build_provenance_rejected(self):
        self.fixture()
        self.checks.write_text('{"static_status":"PASS","checks":[]}')
        with self.assertRaisesRegex(ValueError, 'Missing successful build provenance checks'):
            self.validate()

    def test_stale_successful_report_for_other_image_rejected(self):
        self.fixture()
        report = json.loads(self.checks.read_text())
        record = next(item for item in report['checks'] if item['name'] == 'image_sha256')
        record['detail']['sha256'] = '0' * 64
        self.checks.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, 'report belongs to a different card image'):
            self.validate()

    def test_missing_guest_build_recipe_rejected(self):
        self.fixture()
        del self.versions['selected_recipes']['pi4-guest1-image']
        self.save_versions()
        with self.assertRaisesRegex(ValueError, 'pi4-guest1-image'):
            self.validate()

    def test_changed_source_pin_rejected(self):
        self.fixture()
        self.lock.write_text('{"synthetic_unit_test": "changed source revision"}')
        with self.assertRaisesRegex(ValueError, 'source lock differs'):
            self.validate()

    def test_changed_card_bytes_rejected(self):
        self.fixture()
        with self.image.open('r+b') as stream:
            stream.seek(4096)
            stream.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'no longer matches'):
            self.validate()

    def test_failed_static_checks_rejected(self):
        self.fixture()
        self.checks.write_text('{"static_status":"FAIL"}')
        with self.assertRaisesRegex(ValueError, 'static image checks'):
            self.validate()

    def test_changed_kernel_configuration_rejected(self):
        self.fixture()
        self.config.write_text(self.config.read_text() + '# changed after export\n')
        with self.assertRaisesRegex(ValueError, 'Kernel configuration no longer matches'):
            self.validate()

    def test_virtio_root_driver_module_rejected_without_initrd(self):
        self.fixture()
        self.config.write_text(self.config.read_text().replace('CONFIG_VIRTIO_BLK=y', 'CONFIG_VIRTIO_BLK=m'))
        self.update_checked_hashes()
        with self.assertRaisesRegex(ValueError, 'VIRTIO_BLK'):
            self.validate()

    def test_input_validation_preserves_card_bytes(self):
        self.fixture()
        original = self.image.read_bytes()
        result = self.validate()
        self.assertEqual(result['image'], self.image)
        self.assertEqual(result['partitions'][1]['number'], 2)
        self.assertEqual(self.image.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
