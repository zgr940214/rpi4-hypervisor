# Build the same upstream release from its immutable Git tag commit. This is
# an explicit source-form change, not a checksum substitution for the tarball.
SRC_URI:remove = "http://www.python.org/ftp/python/${PV}/Python-${PV}.tar.xz"
SRC_URI:append = " git://github.com/python/cpython.git;protocol=https;nobranch=1"
SRCREV = "e848e4b09ca4bc67c0041c9ce7526dae471d4c36"
S = "${WORKDIR}/git"
