# Same opkg v0.6.3 release, pinned in the Yocto contributor's upstream mirror.
# Existing autotools dependencies regenerate configure and all patches remain.
SRC_URI:remove = "http://downloads.yoctoproject.org/releases/${BPN}/${BPN}-${PV}.tar.gz"
SRC_URI:append = " git://github.com/moto-timo/opkg.git;protocol=https;nobranch=1;destsuffix=${BPN}-${PV}"
SRCREV = "96c7fdef4112b97929053316bf4c5a136de71ef8"
