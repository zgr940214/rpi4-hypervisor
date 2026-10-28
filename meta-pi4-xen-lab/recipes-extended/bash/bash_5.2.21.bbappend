# Same upstream version, explicitly selecting Ubuntu's XZ source artifact.
# The signed Noble Sources index authenticates this SHA256; existing patches
# and COPYING checksum were checked unchanged. See source-mirrors evidence.
SRC_URI:remove = "${GNU_MIRROR}/bash/${BP}.tar.gz;name=tarball"
SRC_URI:append = " https://archive.ubuntu.com/ubuntu/pool/main/b/bash/bash_${PV}.orig.tar.xz;name=tarball;downloadfilename=bash-${PV}.tar.xz"
SRC_URI[tarball.sha256sum] = "ec21ab4efd6bd7a6e2802fbda622b81bfc43a8095d721234d4bf075797683014"
