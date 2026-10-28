#!/usr/bin/env python3
"""Pack a verified Yocto image into Git-sized XZ parts, or restore those parts.

Packing requires successful static inspection and an actual Yocto QEMU report
for the same image. Restoring needs only Python's standard library and the
manifest/chunks from the repository; it never downloads or boots an image.
"""
import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
IMAGE_NAME = 'pi4-xen-dom0-guest1.img'
MAX_CHUNK = 48 * 1024 * 1024
BLOCK = 1024 * 1024
STATIC_CHECKS = ('image_sha256', 'dom0_yocto_build_identity', 'guest_yocto_build_identity',
                 'guest_payloads_match_build', 'boot_payloads_match_build', 'shared_kernel_identity')
QEMU_CHECKS = ('xen_banner', 'xen_and_dom0_boot', 'dom0_toolstack',
               'guest1_first_boot_and_writable_root', 'dom0_ssh_and_guest_console_reattach',
               'guest1_pause_resume_and_project_demo', 'guest1_clean_shutdown',
               'guest1_recreate_and_persistent_root', 'guest1_final_shutdown', 'source_disk_unchanged')


def fingerprint(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(BLOCK), b''):
            digest.update(data)
            size += len(data)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def matches(record, expected):
    return isinstance(record, dict) and all(record.get(key) == value for key, value in expected.items())


def successful_checks(report, required, label, allowed_pending=()):
    records = {}
    for item in report.get('checks', []):
        if not isinstance(item, dict) or not isinstance(item.get('name'), str):
            raise ValueError(f'Malformed {label} check')
        name = item['name']
        if name in records:
            raise ValueError(f'Duplicate {label} check: {name}')
        if item.get('status') != 'PASS' and not (name in allowed_pending and item.get('status') == 'NOT_RUN'):
            raise ValueError(f'{label} check has not passed: {name}')
        records[name] = item
    for name in required:
        if records.get(name, {}).get('status') != 'PASS':
            raise ValueError(f'Missing successful {label} check: {name}')
    return records


def verify_delivery(artifacts, qemu_report):
    """Bind the current bytes to both existing verification report formats."""
    image = artifacts / IMAGE_NAME
    if not image.is_file():
        raise ValueError(f'Missing built Yocto image: {image}')
    actual = fingerprint(image)
    if not actual['bytes']:
        raise ValueError('The built image is empty')
    inputs = {'image-checks.json': artifacts / 'checks/image-checks.json',
              'artifact.json': artifacts / 'checks/artifact.json',
              'versions.json': artifacts / 'versions.json',
              'pi4-xen-kernel.config': artifacts / 'pi4-xen-kernel.config',
              'qemu-report.json': qemu_report}
    evidence = {name: path.read_bytes() for name, path in inputs.items()}
    reports = {name: json.loads(data) for name, data in evidence.items() if name.endswith('.json')}
    if not all(isinstance(value, dict) for value in reports.values()):
        raise ValueError('Expected JSON objects in verification reports')
    static, checked, versions, qemu = (reports[name] for name in
        ('image-checks.json', 'artifact.json', 'versions.json', 'qemu-report.json'))
    if static.get('static_status') != 'PASS':
        raise ValueError('Static image inspection must PASS before packaging')
    records = successful_checks(static, STATIC_CHECKS, 'static',
                                ('ssh_login', 'pi4_hardware_boot', 'xen_el2_entry_and_firmware_reservations'))
    if not matches(checked, actual) or not matches(records['image_sha256'].get('detail'), actual):
        raise ValueError('Static inspection belongs to a different image')
    identity = {'build_system': 'yocto-bitbake', 'machine': 'raspberrypi4-64', 'distro': 'pi4-xen'}
    if not matches(versions, identity) or versions.get('bytes') != actual['bytes']:
        raise ValueError('Expected self-built Pi4 Yocto export metadata')
    for recipe, pn in [('pi4-xen-dom0-image', 'pi4-xen-dom0-image'),
                       ('pi4-guest1-image', 'pi4-guest1-image'), ('virtual/kernel', 'linux-yocto'),
                       ('xen', 'xen'), ('xen-tools', 'xen-tools')]:
        if versions.get('selected_recipes', {}).get(recipe, {}).get('PN') != pn:
            raise ValueError(f'Missing self-built Yocto recipe: {recipe}')
    if qemu.get('status') != 'PASS' or qemu.get('pi4_image_build') != 'VERIFIED_SELF_BUILT_ARTIFACT':
        raise ValueError('Actual Yocto image QEMU validation must PASS before packaging')
    qchecks = successful_checks(qemu, QEMU_CHECKS, 'QEMU')
    if qchecks['source_disk_unchanged'].get('detail', {}).get('sha256_before_and_after') != actual['sha256']:
        raise ValueError('QEMU source-disk check belongs to a different image')
    provenance = qemu.get('yocto_provenance', {})
    if (not matches(provenance, {'schema_version': 1, 'build_system': 'yocto-bitbake',
                                 'machine': 'raspberrypi4-64'}) or
            provenance.get('build_versions') != versions):
        raise ValueError('Missing matching self-built Yocto QEMU provenance')
    runtime = provenance.get('runtime_artifacts', {})
    observed = qemu.get('artifacts', {})
    if not matches(runtime.get('rootfs'), actual) or not matches(observed.get('rootfs'), actual):
        raise ValueError('QEMU validated a different disk image')
    for name in ('xen', 'kernel'):
        expected = runtime.get(name, {})
        require_digest(expected, f'QEMU {name}')
        if not matches(observed.get(name), {key: expected[key] for key in ('bytes', 'sha256')}):
            raise ValueError(f'QEMU {name} differs from the image provenance')
        boot_name = 'Image' if name == 'kernel' else name
        if records['boot_payloads_match_build'].get('detail', {}).get(boot_name) != expected['sha256']:
            raise ValueError(f'QEMU {name} differs from the inspected image boot payload')
    if 'initrd' in observed:
        raise ValueError('Yocto image validation must use its original built-in kernel drivers')
    for key, name in [('versions_file', 'versions.json'), ('checks_file', 'image-checks.json'),
                      ('kernel_config', 'pi4-xen-kernel.config')]:
        data = evidence[name]
        expected = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        if not matches(provenance.get('evidence_artifacts', {}).get(key), expected):
            raise ValueError(f'QEMU provenance refers to different {name} evidence')
    if checked.get('kernel_config_sha256') != hashlib.sha256(evidence['pi4-xen-kernel.config']).hexdigest():
        raise ValueError('Static inspection refers to a different kernel configuration')
    return actual, evidence, qemu.get('pi4_hardware', 'NOT_RUN')


class ChunkWriter:
    def __init__(self, directory, chunk_size):
        self.directory = directory
        self.limit = chunk_size
        self.chunks = []
        self.stream = None
        self.total = 0
        self.digest = hashlib.sha256()

    def write(self, data):
        self.digest.update(data)
        self.total += len(data)
        while data:
            if self.stream is None:
                name = f'{IMAGE_NAME}.xz.part{len(self.chunks) + 1:05d}'
                self.current = {'name': name, 'bytes': 0}
                self.part_digest = hashlib.sha256()
                self.stream = (self.directory / name).open('xb')
            amount = min(len(data), self.limit - self.current['bytes'])
            piece, data = data[:amount], data[amount:]
            self.stream.write(piece)
            self.part_digest.update(piece)
            self.current['bytes'] += amount
            if self.current['bytes'] == self.limit:
                self.close()

    def close(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None
            self.current['sha256'] = self.part_digest.hexdigest()
            self.chunks.append(self.current)


def pack(artifacts, qemu_report, output, chunk_size=MAX_CHUNK):
    if type(chunk_size) is not int or not 0 < chunk_size <= MAX_CHUNK:
        raise ValueError('Chunk size must be positive and at most 48 MiB')
    if output.exists() or output.is_symlink():
        raise ValueError(f'Delivery directory already exists: {output}')
    expected, evidence, hardware = verify_delivery(artifacts, qemu_report)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.repository-image-', dir=output.parent))
    writer = ChunkWriter(stage, chunk_size)
    try:
        compressor = lzma.LZMACompressor(format=lzma.FORMAT_XZ, preset=6, check=lzma.CHECK_CRC64)
        raw_hash, raw_size = hashlib.sha256(), 0
        with (artifacts / IMAGE_NAME).open('rb') as stream:
            for data in iter(lambda: stream.read(BLOCK), b''):
                raw_hash.update(data)
                raw_size += len(data)
                writer.write(compressor.compress(data))
        writer.write(compressor.flush())
        writer.close()
        if expected != {'bytes': raw_size, 'sha256': raw_hash.hexdigest()}:
            raise ValueError('Image changed while compressing; no delivery was published')
        evidence_records = []
        for name, data in evidence.items():
            (stage / name).write_bytes(data)
            evidence_records.append({'name': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        manifest = {'schema_version': 1, 'image': {'name': IMAGE_NAME, **expected},
                    'compressed': {'format': 'xz', 'bytes': writer.total, 'sha256': writer.digest.hexdigest()},
                    'chunks': writer.chunks, 'evidence': evidence_records,
                    'verification': {'static_status': 'PASS', 'yocto_qemu_status': 'PASS', 'pi4_hardware': hardware}}
        (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        # The final folder appears only after compression and evidence binding pass.
        os.rename(stage, output)
        return manifest
    finally:
        writer.close()
        if stage.exists():
            shutil.rmtree(stage)


def safe_name(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name):
        raise ValueError(f'Unsafe manifest filename: {name!r}')
    return name


def require_digest(record, label):
    if (not isinstance(record, dict) or type(record.get('bytes')) is not int or record['bytes'] <= 0 or
            not isinstance(record.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', record['sha256'])):
        raise ValueError(f'Invalid size or SHA256 for {label}')


def read_manifest(path):
    manifest = json.loads(path.read_text())
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1:
        raise ValueError('Unsupported repository image manifest')
    for name in ('image', 'compressed'):
        require_digest(manifest.get(name), name)
    safe_name(manifest['image'].get('name'))
    if manifest['compressed'].get('format') != 'xz':
        raise ValueError('Expected an XZ archive')
    chunks = manifest.get('chunks')
    if not isinstance(chunks, list) or not chunks:
        raise ValueError('Manifest has no ordered chunks')
    names, total = set(), 0
    for item in chunks:
        require_digest(item, 'chunk')
        name = safe_name(item.get('name'))
        if name in names or item['bytes'] > MAX_CHUNK:
            raise ValueError('Duplicate chunk or chunk larger than 48 MiB')
        names.add(name)
        total += item['bytes']
    if total != manifest['compressed']['bytes']:
        raise ValueError('Chunk sizes do not match the compressed size')
    return manifest


def restore(manifest_path, output, force=False):
    manifest = read_manifest(manifest_path)
    expected = {key: manifest['image'][key] for key in ('bytes', 'sha256')}
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ValueError(f'Refusing non-regular output: {output}')
    if output.exists() and not force and fingerprint(output) != expected:
        raise ValueError(f'Existing image differs: {output}; use --force to replace it')
    # Never overwrite a chunk, manifest or evidence file, even with --force.
    if output.resolve().parent == manifest_path.resolve().parent:
        raise ValueError('Restore output must be outside the delivery directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + output.name + '-', suffix='.tmp', dir=output.parent)
    temporary = Path(name)
    compressed_hash, image_hash = hashlib.sha256(), hashlib.sha256()
    raw_size = 0
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ, memlimit=256 * 1024 * 1024)
    try:
        with os.fdopen(fd, 'wb') as target:
            for item in manifest['chunks']:
                chunk = manifest_path.parent / item['name']
                if chunk.is_symlink() or not chunk.is_file():
                    raise ValueError(f'Missing or non-regular chunk: {item["name"]}')
                digest, size = hashlib.sha256(), 0
                with chunk.open('rb') as source:
                    for data in iter(lambda: source.read(BLOCK), b''):
                        size += len(data)
                        if size > item['bytes']:
                            raise ValueError(f'Chunk size mismatch: {item["name"]}')
                        digest.update(data)
                        compressed_hash.update(data)
                        if decoder.eof:
                            raise ValueError('Trailing bytes after the XZ stream')
                        while True:
                            plain = decoder.decompress(data, max_length=BLOCK)
                            data = b''
                            raw_size += len(plain)
                            if raw_size > expected['bytes']:
                                raise ValueError('Decompressed image exceeds its declared size')
                            image_hash.update(plain)
                            # Preserve zero regions as sparse extents when supported.
                            if plain and not any(plain):
                                target.seek(len(plain), os.SEEK_CUR)
                            else:
                                target.write(plain)
                            if decoder.eof or decoder.needs_input:
                                break
                        if decoder.unused_data:
                            raise ValueError('Trailing bytes after the XZ stream')
                if not matches(item, {'bytes': size, 'sha256': digest.hexdigest()}):
                    raise ValueError(f'Chunk integrity mismatch: {item["name"]}')
            if not decoder.eof:
                raise ValueError('Truncated XZ stream')
            if compressed_hash.hexdigest() != manifest['compressed']['sha256']:
                raise ValueError('Compressed archive SHA256 mismatch')
            if expected != {'bytes': raw_size, 'sha256': image_hash.hexdigest()}:
                raise ValueError('Restored image size or SHA256 mismatch')
            target.truncate(raw_size)
            target.flush()
            os.fsync(target.fileno())
        if force:
            os.replace(temporary, output)
        else:
            # Atomic no-clobber publication also handles a file created meanwhile.
            try:
                os.link(temporary, output)
            except FileExistsError:
                if output.is_symlink() or not output.is_file() or fingerprint(output) != expected:
                    raise ValueError(f'Existing image differs: {output}; use --force to replace it')
        return expected
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    packing = sub.add_parser('pack', help='Require matching static and Yocto QEMU PASS, then compress')
    packing.add_argument('--artifacts', type=Path, default=ROOT / 'artifacts')
    packing.add_argument('--qemu-report', type=Path, required=True)
    packing.add_argument('--output', type=Path, default=ROOT / 'artifacts/repository-image')
    packing.add_argument('--chunk-mib', type=int, choices=range(1, 49), default=48)
    restoring = sub.add_parser('restore', help='Verify and reconstruct the exact raw card image')
    restoring.add_argument('--manifest', type=Path, default=ROOT / 'artifacts/repository-image/manifest.json')
    restoring.add_argument('--output', type=Path, default=ROOT / 'artifacts' / IMAGE_NAME)
    restoring.add_argument('--force', action='store_true', help='Replace an existing different image after all checks pass')
    args = parser.parse_args(argv)
    try:
        if args.command == 'pack':
            result = pack(args.artifacts, args.qemu_report, args.output, args.chunk_mib * 1024 * 1024)
            print(f'Published {len(result["chunks"])} verified chunks: {args.output / "manifest.json"}')
        else:
            result = restore(args.manifest, args.output, args.force)
            print(f'Restored verified image: {args.output} ({result["bytes"]} bytes, SHA256 {result["sha256"]})')
    except (ValueError, OSError, EOFError, lzma.LZMAError, TypeError, KeyError) as exc:
        print(f'Repository image {args.command} refused: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
