# Same upstream release in XZ format, authenticated through Debian's signed
# source index. All upstream recipe patches and license checks remain active.
# Evidence: docs/xen-lab/evidence/source-mirrors/20261028/acl-attr-xz/.
SRC_URI:remove = "${SAVANNAH_GNU_MIRROR}/acl/${BP}.tar.gz"
SRC_URI:append = " https://deb.debian.org/debian/pool/main/a/acl/acl_${PV}.orig.tar.xz;downloadfilename=acl-${PV}.tar.xz"
SRC_URI[sha256sum] = "97203a72cae99ab89a067fe2210c1cbf052bc492b479eca7d226d9830883b0bd"
