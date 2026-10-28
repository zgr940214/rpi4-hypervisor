# The fixed Ubuntu builder does not need binaries that can be moved to older
# glibc hosts. In that explicit host mode build pseudo against the builder's
# libc, avoiding the optional prebuilt compatibility libraries entirely.
SRC_URI:remove:class-native = "${@'http://downloads.yoctoproject.org/mirror/sources/pseudo-prebuilt-2.33.tar.xz;subdir=git/prebuilt;name=prebuilt file://older-glibc-symbols.patch' if d.getVar('PI4_XEN_FIXED_NATIVE_HOST') == '1' else ''}"
