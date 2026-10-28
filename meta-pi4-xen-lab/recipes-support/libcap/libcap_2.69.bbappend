# Fixed upstream libcap-2.69 release commit from the kernel.org Git mirror.
# The original recipe's patches, version, and license checks are retained.
SRC_URI:remove = "${KERNELORG_MIRROR}/linux/libs/security/linux-privs/${BPN}2/${BPN}-${PV}.tar.xz"
SRC_URI:append = " git://github.com/kernelorg-mirror/libs_libcap_libcap.git;protocol=https;nobranch=1;destsuffix=${BP}"
SRCREV = "8bed80f9b54b7bd2a1ee1fdc2124a094733c9356"
