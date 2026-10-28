#!/usr/bin/env python3
"""Export the actual successful Wic output and its verification evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def value(recipe, name):
    return subprocess.check_output(['bitbake-getvar', '-r', recipe, '--value', name],
                                   text=True).strip()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    image_recipe = 'pi4-xen-dom0-image'
    deploy = Path(value(image_recipe, 'DEPLOY_DIR_IMAGE'))
    native = deploy / (value(image_recipe, 'IMAGE_LINK_NAME') + '.wic')
    if not native.is_file():
        raise SystemExit(f'Expected uncompressed Wic output is absent: {native}')
    out = ROOT / 'artifacts'
    out.mkdir(exist_ok=True)
    image = out / 'pi4-xen-dom0-guest1.img'
    # Preserve sparse allocation; the exported image must remain byte-identical.
    subprocess.run(['cp', '--sparse=always', '--reflink=auto', str(native), str(image)], check=True)
    if digest(native) != digest(image):
        raise SystemExit('Export differs from the original Wic image')
    config = deploy / 'pi4-xen-kernel.config'
    if not config.is_file():
        raise SystemExit(f'Final built kernel configuration is absent: {config}')
    shutil.copy2(config, out / config.name)
    kernel_metadata = deploy / 'pi4-xen-kernel.json'
    if not kernel_metadata.is_file():
        raise SystemExit(f'Built kernel provenance is absent: {kernel_metadata}')
    shutil.copy2(kernel_metadata, out / kernel_metadata.name)
    versions = {'build_system': 'yocto-bitbake',
                'source_lock': json.loads((ROOT / 'sources.lock.json').read_text()),
                'native_wic': str(native.resolve()), 'bytes': image.stat().st_size,
                'machine': value(image_recipe, 'MACHINE'),
                'distro': value(image_recipe, 'DISTRO'),
                'kernel': json.loads(kernel_metadata.read_text()),
                'selected_recipes': {}}
    for recipe in [image_recipe, 'pi4-guest1-image', 'xen', 'xen-tools', 'virtual/kernel', 'u-boot']:
        versions['selected_recipes'][recipe] = {k: value(recipe, k) for k in ['PN', 'PV', 'FILE']}
    versions['guest_build_outputs'] = {}
    for name in ['pi4-guest1.ext4', 'pi4-guest1.manifest']:
        payload = deploy / name
        if not payload.is_file():
            raise SystemExit(f'Yocto guest build output is absent: {payload}')
        versions['guest_build_outputs'][name] = {'sha256': digest(payload), 'bytes': payload.stat().st_size}
    shutil.copy2(deploy / 'pi4-guest1.manifest', out / 'pi4-guest1.manifest')
    (out / 'versions.json').write_text(json.dumps(versions, indent=2) + '\n')
    (out / 'SHA256SUMS').write_text(f'{digest(image)}  {image.name}\n')
    # Nonzero status is preserved. Hardware success is never inferred here.
    subprocess.run(['python3', str(ROOT / 'scripts/check-image.py'),
                    '--image', str(image), '--deploy', str(deploy),
                    '--kernel-config', str(config), '--output', str(out / 'checks')], check=True)
    print(f'Export and static checks completed: {image}')


if __name__ == '__main__':
    main()
