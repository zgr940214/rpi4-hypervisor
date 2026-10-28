# Same upstream QEMU release from its immutable Git tag. Fetch its required
# keymap and floating-point sources at the revisions in that release's wrap
# files; configure keeps --disable-download and the tests remain enabled.
SRC_URI:remove = "https://download.qemu.org/${BPN}-${PV}.tar.xz"
SRC_URI:append = " \
    git://github.com/qemu/qemu.git;protocol=https;nobranch=1;name=qemu \
    git://gitlab.com/qemu-project/keycodemapdb.git;protocol=https;nobranch=1;name=keycodemap;destsuffix=git/subprojects/keycodemapdb \
    git://gitlab.com/qemu-project/berkeley-softfloat-3.git;protocol=https;nobranch=1;name=softfloat;destsuffix=git/subprojects/berkeley-softfloat-3 \
    git://gitlab.com/qemu-project/berkeley-testfloat-3.git;protocol=https;nobranch=1;name=testfloat;destsuffix=git/subprojects/berkeley-testfloat-3 \
    "
SRCREV_qemu = "317c999868dfbc6e4630a39ca10cf189b81d17ad"
SRCREV_keycodemap = "f5772a62ec52591ff6870b7e8ef32482371f22c6"
SRCREV_softfloat = "b64af41c3276f97f0e181920400ee056b9c88037"
SRCREV_testfloat = "e7af9751d9f9fd3b47911f51a5cfd08af256a9ab"
SRCREV_FORMAT = "qemu_keycodemap_softfloat_testfloat"
S = "${WORKDIR}/git"

# This host tool executes AArch64 target programs during the Pi4 image build.
QEMU_TARGETS = "aarch64"

python do_unpack:append() {
    import shutil
    from pathlib import Path
    source = Path(d.getVar('S'))
    for project in ('berkeley-softfloat-3', 'berkeley-testfloat-3'):
        shutil.copytree(source / 'subprojects/packagefiles' / project,
                        source / 'subprojects' / project, dirs_exist_ok=True)
}
