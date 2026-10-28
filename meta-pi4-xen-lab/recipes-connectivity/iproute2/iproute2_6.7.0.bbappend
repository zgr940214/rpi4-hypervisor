# Same upstream v6.7.0 release, fetched by its immutable Git commit.
SRC_URI:remove = "${KERNELORG_MIRROR}/linux/utils/net/${BPN}/${BP}.tar.xz"
SRC_URI:append = " git://github.com/iproute2/iproute2.git;protocol=https;nobranch=1;destsuffix=${BP}"
SRCREV = "3dc3445bbfa9b84d4166e5837f8d5a4994faf2e7"
