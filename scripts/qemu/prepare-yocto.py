#!/usr/bin/env python3
"""Verify a self-built Yocto card image and extract its exact QEMU boot payloads.

The complete original card image remains the QEMU disk. No rootfs is replaced,
no guest payload is rewritten, and this script never downloads an OS image.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('image_check', ROOT / 'scripts/check-image.py')
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)
DOM0_ARGS = 'console=hvc0 earlycon=xenboot root=/dev/vda2 rw rootwait net.ifnames=0'
RECIPES = {'pi4-xen-dom0-image': 'pi4-xen-dom0-image',
           'pi4-guest1-image': 'pi4-guest1-image',
           'virtual/kernel': 'linux-yocto', 'xen': 'xen', 'xen-tools': 'xen-tools'}
PROVENANCE_CHECKS = ['image_sha256', 'dom0_yocto_build_identity',
                     'guest_yocto_build_identity', 'guest_payloads_match_build',
                     'boot_payloads_match_build', 'shared_kernel_identity']


def artifact(path):
    return {'path': str(path.resolve()), 'bytes': path.stat().st_size,
            'sha256': CHECK.sha256(path)}


def validate_export(directory, lock_file):
    """Reject missing, changed, unverified or non-Yocto inputs before QEMU."""
    image = directory / 'pi4-xen-dom0-guest1.img'
    versions_file = directory / 'versions.json'
    config = directory / 'pi4-xen-kernel.config'
    checks_file = directory / 'checks/image-checks.json'
    checked_artifact_file = directory / 'checks/artifact.json'
    for path in [image, versions_file, config, checks_file, checked_artifact_file]:
        if not path.is_file():
            raise ValueError(f'Missing Yocto build output: {path}; run ./scripts/container.sh build first')
    versions = json.loads(versions_file.read_text())
    identity = {'build_system': 'yocto-bitbake', 'machine': 'raspberrypi4-64', 'distro': 'pi4-xen'}
    if any(versions.get(name) != expected for name, expected in identity.items()):
        raise ValueError('Expected export metadata for the pi4-xen raspberrypi4-64 Yocto build')
    if versions.get('source_lock') != json.loads(lock_file.read_text()):
        raise ValueError('The exported image source lock differs from sources.lock.json')
    selected = versions.get('selected_recipes', {})
    for recipe, expected in RECIPES.items():
        if selected.get(recipe, {}).get('PN') != expected:
            raise ValueError(f'Missing self-built Yocto recipe provenance: {recipe}')
    checks = json.loads(checks_file.read_text())
    if checks.get('static_status') != 'PASS':
        raise ValueError('The exact exported card image must pass the static image checks first')
    records = {item['name']: item for item in checks.get('checks', [])}
    missing = [name for name in PROVENANCE_CHECKS if records.get(name, {}).get('status') != 'PASS']
    if missing:
        raise ValueError('Missing successful build provenance checks: ' + ', '.join(missing))
    checked = json.loads(checked_artifact_file.read_text())
    actual = artifact(image)
    if checked.get('sha256') != actual['sha256'] or checked.get('bytes') != actual['bytes']:
        raise ValueError('Card image no longer matches its successful static inspection')
    if records['image_sha256'].get('detail', {}).get('sha256') != actual['sha256']:
        raise ValueError('Static check report belongs to a different card image')
    if checked.get('kernel_config_sha256') != CHECK.sha256(config):
        raise ValueError('Kernel configuration no longer matches the inspected build output')
    CHECK.kernel_config(config)
    required = ['ARM_GIC_V3', 'VIRTIO', 'VIRTIO_MMIO', 'VIRTIO_BLK',
                'VIRTIO_NET', 'MSDOS_PARTITION']
    lines = set(config.read_text().splitlines())
    missing = [name for name in required if f'CONFIG_{name}=y' not in lines]
    if missing:
        raise ValueError('Shared Pi4 kernel lacks QEMU builtins: ' + ', '.join(missing))
    return {'image': image, 'image_artifact': actual, 'versions': versions,
            'versions_file': versions_file, 'checks_file': checks_file,
            'kernel_config': config, 'partitions': CHECK.partitions(image),
            'boot_sha256': records['boot_payloads_match_build']['detail']}


def prepare(directory, output, lock_file):
    verified = validate_export(directory, lock_file)
    output.mkdir(parents=True, exist_ok=True)
    image = verified['image']
    fat = f"{image.resolve()}@@{verified['partitions'][0]['offset']}"
    with tempfile.TemporaryDirectory(prefix='yocto-boot-', dir=output) as temporary:
        scratch = Path(temporary)
        for name in ['xen', 'Image']:
            subprocess.run(['mcopy', '-i', fat, '::/' + name, str(scratch / name)], check=True)
            if not (scratch / name).stat().st_size:
                raise ValueError(f'Empty {name} in the original card boot partition')
            if CHECK.sha256(scratch / name) != verified['boot_sha256'].get(name):
                raise ValueError(f'Extracted {name} differs from the verified Yocto boot payload')
        CHECK.arm64_image(scratch / 'Image')
        # Copy only verified boot bytes. The complete source disk and its
        # embedded guest rootfs are never opened writable.
        for name in ['xen', 'Image']:
            shutil.copyfile(scratch / name, output / name)
    if CHECK.sha256(image) != verified['image_artifact']['sha256']:
        raise ValueError('Source card image changed while preparing QEMU inputs')
    provenance = {
        'schema_version': 1, 'build_system': 'yocto-bitbake',
        'machine': 'raspberrypi4-64',
        'prepared_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Exact self-built Pi4 card disk; boot Xen and Image extracted from its FAT partition',
        'dom0_args': DOM0_ARGS,
        'runtime_artifacts': {'rootfs': verified['image_artifact'],
                              'xen': artifact(output / 'xen'),
                              'kernel': artifact(output / 'Image')},
        'build_versions': verified['versions'],
        'evidence_artifacts': {name: artifact(verified[name])
                               for name in ['versions_file', 'checks_file', 'kernel_config']},
        'guest_payload': 'Original /var/lib/xen/images/guest1 inside the unchanged Dom0 partition',
        'pi4_hardware': 'NOT_RUN',
    }
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print('Verified exact Yocto card image:', image)
    print('QEMU boot provenance:', output / 'provenance.json')
    return provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', type=Path, default=ROOT / 'artifacts')
    parser.add_argument('--output', type=Path, default=ROOT / 'local/qemu-yocto')
    args = parser.parse_args()
    try:
        prepare(args.artifacts.resolve(), args.output.resolve(), ROOT / 'sources.lock.json')
    except (ValueError, OSError, CHECK.CheckError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f'Yocto QEMU preparation refused: {exc}') from exc


if __name__ == '__main__':
    main()
