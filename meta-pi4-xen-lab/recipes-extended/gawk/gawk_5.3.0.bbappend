# Exact commit behind upstream's gawk-5.3.0 release tag. This mirror includes
# generated configure/Makefile.in; all original Poky patches apply unchanged.
SRC_URI:remove = "${GNU_MIRROR}/gawk/gawk-${PV}.tar.gz"
SRC_URI:append = " git://github.com/GitMirroring/gawk.git;protocol=https;nobranch=1"
SRCREV = "5efd1487e16e68a1bb52fa5ca997d2d51182bff2"
S = "${WORKDIR}/git"
