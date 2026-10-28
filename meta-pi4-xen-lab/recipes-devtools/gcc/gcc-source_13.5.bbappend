# Use the same GCC 13.5.0 release from the upstream GitHub Git mirror when the
# distribution archive host is unavailable. This is an explicit source-format
# change: Git verifies the fixed release commit, not the archive's SHA256.
# destsuffix preserves the directory consumed by gcc-cross/libgcc/gcc-runtime.
BASEURI = "git://github.com/gcc-mirror/gcc.git;protocol=https;nobranch=1;destsuffix=gcc-${PV}"
SRCREV = "0bba35ae26a574150f6d1ae55f8ab1f4c2314a56"
