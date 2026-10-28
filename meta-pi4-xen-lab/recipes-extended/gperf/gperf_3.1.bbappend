# Debian's same-release source packaging is a Git archive, not byte-identical
# to the GNU distribution tarball. Select it explicitly under a distinct
# filename. Bookworm's signed Sources index authenticates this artifact;
# both upstream license checksums and both Poky patches remain unchanged.
SRC_URI:remove = "${GNU_MIRROR}/${BPN}/${BP}.tar.gz"
SRC_URI:append = " https://deb.debian.org/debian/pool/main/g/gperf/gperf_${PV}.orig.tar.gz;downloadfilename=gperf-${PV}-debian.orig.tar.gz"
SRC_URI[sha256sum] = "1f88819b78187350e7e6ca24b5e15cbf4083659773508d3f018b9b525e9d1cb8"
SRC_URI[md5sum] = "190817525c915818ed1118a9ffdeb02f"
