# Upstream's 3.0.17 tag has the same source Makefiles as the release archive.
# Preserve all Yocto patches and existing licence checks.
SRC_URI:remove = "${SOURCEFORGE_MIRROR}/${BPN}/files/${BP}.tar.bz2"
SRC_URI:append = " git://github.com/ncroxon/gnu-efi.git;protocol=https;nobranch=1;destsuffix=${BP}"
SRCREV = "24c80efc1af996bf8252f4a2f5ffc02d8c44640b"
