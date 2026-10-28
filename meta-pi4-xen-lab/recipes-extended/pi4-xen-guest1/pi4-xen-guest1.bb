SUMMARY = "The guest1 kernel, writable disk image, and Xen configuration"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://guest1.cfg.in"
S = "${WORKDIR}"
PACKAGE_ARCH = "${MACHINE_ARCH}"

# These real task edges rebuild this package after either guest rootfs or the
# shared Linux Image changes. The guest image never depends on this package.
do_install[depends] += "pi4-guest1-image:do_image_complete virtual/kernel:do_deploy"

do_install() {
    install -d ${D}${sysconfdir}/xen ${D}${localstatedir}/lib/xen/images/guest1
    install -m 0644 ${DEPLOY_DIR_IMAGE}/${KERNEL_IMAGETYPE} \
        ${D}${localstatedir}/lib/xen/images/guest1/Image
    cp --sparse=always --dereference ${DEPLOY_DIR_IMAGE}/pi4-guest1.ext4 \
        ${D}${localstatedir}/lib/xen/images/guest1/rootfs.ext4
    install -m 0644 ${DEPLOY_DIR_IMAGE}/pi4-guest1.manifest \
        ${D}${localstatedir}/lib/xen/images/guest1/guest.manifest
    chmod 0600 ${D}${localstatedir}/lib/xen/images/guest1/rootfs.ext4
    sed -e 's/@@GUEST_MEMORY@@/${PI4_GUEST1_MEMORY_MIB}/g' \
        -e 's/@@GUEST_VCPUS@@/${PI4_GUEST1_VCPUS}/g' \
        ${WORKDIR}/guest1.cfg.in > ${D}${sysconfdir}/xen/guest1.cfg
    chmod 0644 ${D}${sysconfdir}/xen/guest1.cfg
}

# Record and compare the actual files produced by the dependency tasks. The
# exported whole-card image must pass the same comparisons after packaging.
do_install[postfuncs] += "pi4_guest1_provenance"
python pi4_guest1_provenance() {
    import hashlib
    import json
    from pathlib import Path

    def artifact(path):
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}

    deploy = Path(d.getVar('DEPLOY_DIR_IMAGE'))
    target = Path(d.getVar('D') + d.getVar('localstatedir')) / 'lib/xen/images/guest1'
    sources = {
        'Image': deploy / d.getVar('KERNEL_IMAGETYPE'),
        'rootfs.ext4': deploy / 'pi4-guest1.ext4',
        'guest.manifest': deploy / 'pi4-guest1.manifest',
    }
    artifacts = {}
    for name, source in sources.items():
        artifacts[name] = artifact(source)
        if artifacts[name] != artifact(target / name):
            bb.fatal('Installed guest payload differs from BitBake deploy output: ' + name)
    kernel = json.loads((deploy / 'pi4-xen-kernel.json').read_text())
    if kernel['machine'] != d.getVar('MACHINE'):
        bb.fatal('Guest kernel was built for a different MACHINE')
    metadata = {
        'schema_version': 1,
        'build_system': 'yocto-bitbake',
        'guest_image_recipe': 'pi4-guest1-image',
        'machine': d.getVar('MACHINE'),
        'distro': d.getVar('DISTRO'),
        'kernel': kernel,
        'artifacts': artifacts,
    }
    path = target / 'provenance.json'
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + '\n')
    path.chmod(0o644)
}

FILES:${PN} = "${sysconfdir}/xen/guest1.cfg ${localstatedir}/lib/xen/images/guest1"
CONFFILES:${PN} = "${sysconfdir}/xen/guest1.cfg"
RDEPENDS:${PN} = "xen-tools-xl xen-tools-scripts-block util-linux-losetup"

# The kernel is an Image payload, not a userspace ELF to strip or debug-split.
INHIBIT_PACKAGE_STRIP = "1"
INHIBIT_PACKAGE_DEBUG_SPLIT = "1"
