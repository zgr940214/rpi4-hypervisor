# Use the same upstream Linux 6.6 release from its Git mirror when the
# distribution archive host is unavailable. The fixed commit verifies this
# explicit Git source alternative; the original archive checksum is unchanged.
# Preserve the standard libc headers, patches, license check and source layout.
SRC_URI:remove = "${KERNELORG_MIRROR}/linux/kernel/v${HEADER_FETCH_VER}/linux-${PV}.tar.${KORG_ARCHIVE_COMPRESSION}"
SRC_URI:prepend = "git://github.com/torvalds/linux.git;protocol=https;nobranch=1;destsuffix=linux-${PV} "
SRCREV = "ffc253263a1375a65fa6c9f62a893e9767fbebfa"
