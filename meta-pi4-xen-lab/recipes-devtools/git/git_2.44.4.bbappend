# Same upstream 2.44.4 release, pinned to the commit behind tag v2.44.4.
# Keep the distribution patches and licence checks; autoreconf regenerates configure.
SRC_URI:remove = "${KERNELORG_MIRROR}/software/scm/git/git-${PV}.tar.gz;name=tarball"
SRC_URI:append = " git://github.com/git/git.git;protocol=https;nobranch=1;destsuffix=git-${PV}"
SRCREV = "080b728d4b2bbdd2c0b9eb9ed6a41195f8303088"

# Release tarballs contain this file. Keep the release version independent of
# patch dirtiness and the shallow checkout's Git history.
python do_unpack:append() {
    import os
    with open(os.path.join(d.getVar("S"), "version"), "w") as stream:
        stream.write(d.getVar("PV") + "\n")
}
