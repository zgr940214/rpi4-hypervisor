FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

# Validate the actual built payloads before compiling boot.scr. Image header
# sizes include the in-memory span, which can exceed the file's byte count.
python do_validate_pi4_payloads() {
    import struct
    from pathlib import Path
    deploy = Path(d.getVar('DEPLOY_DIR_IMAGE'))
    for name, limit in (('xen-' + d.getVar('MACHINE'), 0x00e00000),
                        (d.getVar('KERNEL_IMAGETYPE'), 0x03f00000)):
        path = deploy / name
        size = path.stat().st_size
        with path.open('rb') as stream:
            header = stream.read(64)
        if len(header) != 64 or header[56:60] != b'ARM\x64':
            bb.fatal('%s is not an AArch64 Image' % path)
        memsize = struct.unpack_from('<Q', header, 16)[0]
        if not size or not memsize or max(size, memsize) > limit:
            bb.fatal('%s exceeds its checked boot memory window' % path)
    dtb = deploy / 'bcm2711-rpi-4-b.dtb'
    if dtb.stat().st_size > 0x000f0000:
        bb.fatal('Pi4 DTB exceeds the boot script DTB reservation')
}
do_validate_pi4_payloads[depends] += "virtual/kernel:do_deploy xen:do_deploy"
addtask validate_pi4_payloads after do_prepare_recipe_sysroot before do_compile

do_deploy:append() {
    install -m 0644 ${WORKDIR}/boot.cmd ${DEPLOYDIR}/boot.cmd
}
