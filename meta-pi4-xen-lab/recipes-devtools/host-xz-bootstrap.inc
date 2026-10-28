# Early native build tools are prerequisites of xz-native. Their explicitly
# selected XZ source archives must use the fixed build host's decompressor,
# otherwise base.bbclass's unpack dependency creates a cycle. This include is
# required only by these bootstrap recipes, not globally.
python __anonymous() {
    if bb.data.inherits_class('native', d):
        dependencies = (d.getVarFlag('do_unpack', 'depends') or '').split()
        d.setVarFlag('do_unpack', 'depends', ' '.join(
            item for item in dependencies
            if item != 'xz-native:do_populate_sysroot'))
}

do_unpack[prefuncs] += "pi4_bootstrap_host_xz"
python pi4_bootstrap_host_xz() {
    if not bb.data.inherits_class('native', d):
        return
    import os
    host_xz = '/usr/bin/xz'
    if not os.access(host_xz, os.X_OK):
        bb.fatal('The fixed build host must provide /usr/bin/xz for bootstrap unpack')
    tools = os.path.join(d.getVar('WORKDIR'), 'pi4-host-unpack-tools')
    bb.utils.mkdirhier(tools)
    link = os.path.join(tools, 'xz')
    if not os.path.lexists(link):
        os.symlink(host_xz, link)
    if os.path.realpath(link) != host_xz:
        bb.fatal('Unexpected bootstrap XZ tool: %s' % link)
    # Only this task receives the pinned executable. Normal fetch/unpack and
    # checksum verification stay intact; no liblzma dependency is suppressed.
    d.prependVar('PATH', tools + ':')
}
