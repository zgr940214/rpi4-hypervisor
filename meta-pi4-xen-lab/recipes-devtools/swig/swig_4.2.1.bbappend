# Build the upstream v4.2.1 Git release; existing autotools and bison-native
# dependencies regenerate the release's configure files and parser.
SRC_URI:remove = "${SOURCEFORGE_MIRROR}/${BPN}/${BPN}-${PV}.tar.gz"
SRC_URI:append = " git://github.com/swig/swig.git;protocol=https;nobranch=1"
SRCREV = "b592468f522cf7f4a0812493bfa07cbe60679d7c"
S = "${WORKDIR}/git"
