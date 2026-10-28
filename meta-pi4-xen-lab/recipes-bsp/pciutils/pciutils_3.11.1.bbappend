# Same upstream v3.11.1 release, including its checked-in pci.ids database.
SRC_URI:remove = "${KERNELORG_MIRROR}/software/utils/pciutils/pciutils-${PV}.tar.xz"
SRC_URI:append = " git://github.com/pciutils/pciutils.git;protocol=https;nobranch=1;destsuffix=${BP}"
SRCREV = "08f8e6666a69595ba4532f16a46b9dc46b677860"
