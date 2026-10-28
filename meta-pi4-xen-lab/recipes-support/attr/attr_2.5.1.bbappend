# Same upstream release in XZ format, authenticated through Debian's signed
# source index. All upstream recipe patches and license checks remain active.
# Evidence: docs/xen-lab/evidence/source-mirrors/20261028/acl-attr-xz/.
SRC_URI:remove = "${SAVANNAH_GNU_MIRROR}/attr/${BP}.tar.gz"
SRC_URI:append = " https://deb.debian.org/debian/pool/main/a/attr/attr_${PV}.orig.tar.xz;downloadfilename=attr-${PV}.tar.xz"
SRC_URI[sha256sum] = "db448a626f9313a1a970d636767316a8da32aede70518b8050fa0de7947adc32"
