FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI:append:raspberrypi4-64 = " file://pi4-xen.cfg"

# Keep the finalized merged configuration even when rm_work is enabled.
do_deploy:append:raspberrypi4-64() {
    install -m 0644 ${B}/.config ${DEPLOYDIR}/pi4-xen-kernel.config
}

do_deploy[postfuncs] += "pi4_xen_kernel_provenance"
python pi4_xen_kernel_provenance() {
    import json
    from pathlib import Path
    if d.getVar('MACHINE') != 'raspberrypi4-64':
        return
    release = Path(d.getVar('B'), 'include/config/kernel.release').read_text().strip()
    metadata = {
        'schema_version': 1,
        'recipe': d.getVar('PN'),
        'version': d.getVar('PV'),
        'kernel_release': release,
        'machine': d.getVar('MACHINE'),
        'source_revision': d.getVar('SRCREV_machine') or d.getVar('SRCREV'),
    }
    path = Path(d.getVar('DEPLOYDIR'), 'pi4-xen-kernel.json')
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + '\n')
    path.chmod(0o644)
}

python do_pi4_xen_config_check() {
    from pathlib import Path
    if d.getVar('MACHINE') != 'raspberrypi4-64':
        return
    text = Path(d.getVar('B'), '.config').read_text()
    expected = (
        'ARM64', 'XEN', 'XEN_DOM0', 'XEN_BACKEND', 'HVC_XEN',
        'XEN_BLKDEV_FRONTEND', 'XEN_BLKDEV_BACKEND', 'XEN_DEV_EVTCHN',
        'XEN_GNTDEV', 'XEN_GRANT_DEV_ALLOC', 'XEN_PRIVCMD', 'XENFS',
        'XEN_COMPAT_XENFS', 'BLK_DEV_LOOP', 'EXT4_FS', 'DEVTMPFS',
        'DEVTMPFS_MOUNT', 'MMC', 'MMC_BLOCK', 'MMC_SDHCI',
        'MMC_SDHCI_PLTFM', 'MMC_SDHCI_IPROC', 'BCMGENET',
        'ARM_GIC_V3', 'VIRTIO', 'VIRTIO_MMIO', 'VIRTIO_BLK', 'VIRTIO_NET',
        'MSDOS_PARTITION',
    )
    missing = [name for name in expected if 'CONFIG_%s=y' % name not in text.splitlines()]
    if missing:
        bb.fatal('Final kernel configuration lacks required builtins: ' + ', '.join(missing))
}
addtask pi4_xen_config_check after do_configure before do_compile
