# Same pigz 2.8 upstream release, pinned to the commit behind annotated tag v2.8.
# Keep the recipe patches and license checks; do not relabel a different archive.
SRC_URI:remove = "http://zlib.net/${BPN}/fossils/${BP}.tar.gz"
SRC_URI:append = " git://github.com/madler/pigz.git;protocol=https;nobranch=1"
SRCREV = "fe4894f57739e3039a2ffc2a2a360d35e19bacbe"
S = "${WORKDIR}/git"
