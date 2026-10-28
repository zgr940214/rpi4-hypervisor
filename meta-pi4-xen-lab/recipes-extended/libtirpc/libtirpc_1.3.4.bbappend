# Fixed upstream libtirpc-1-3-4 release commit. The autotools class generates
# configure and Makefile.in; the original patches and license checks remain.
SRC_URI:remove = "${SOURCEFORGE_MIRROR}/${BPN}/${BP}.tar.bz2"
SRC_URI:append = " git://github.com/linux-nfs/libtirpc.git;protocol=https;nobranch=1;destsuffix=${BP}"
SRCREV = "e86eef35f3628b3adf388a522ab5731bb4487f34"
