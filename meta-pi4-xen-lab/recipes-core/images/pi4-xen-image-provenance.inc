# This file is generated inside each rootfs by its own BitBake image recipe.
# The outer image checker also verifies the payload hashes against deploy output.
ROOTFS_POSTPROCESS_COMMAND:append = " pi4_xen_image_provenance;"
python pi4_xen_image_provenance() {
    import json
    from pathlib import Path
    path = Path(d.getVar('IMAGE_ROOTFS') + d.getVar('sysconfdir')) / 'pi4-xen-build.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        'schema_version': 1,
        'build_system': 'yocto-bitbake',
        'image_recipe': d.getVar('PN'),
        'machine': d.getVar('MACHINE'),
        'distro': d.getVar('DISTRO'),
        'distro_version': d.getVar('DISTRO_VERSION'),
    }
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + '\n')
    path.chmod(0o644)
}
