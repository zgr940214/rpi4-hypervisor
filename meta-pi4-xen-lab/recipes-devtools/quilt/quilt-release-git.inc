# Upstream v0.67 mirrored by Sailfish OS; includes release-generated configure.
# This preserves quilt-native's bootstrap path without an autotools dependency.
SRC_URI:remove = "${SAVANNAH_GNU_MIRROR}/quilt/quilt-${PV}.tar.gz"
SRC_URI:append = " git://github.com/sailfishos-mirror/quilt.git;protocol=https;nobranch=1;destsuffix=quilt-${PV}"
SRCREV = "1731753a56234abc9a367f0e476bd5eeec126fde"

# Git checkout timestamps need not retain the archive's generated-file order.
# The native recipe deliberately uses the committed configure without autoreconf.
do_configure:prepend:class-native() {
    touch ${S}/configure
}
