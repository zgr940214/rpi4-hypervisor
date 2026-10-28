# Use the official libgpg-error-1.48 release commit. Preserve the recipe's
# patches and all license checks, including its header/source snippets.
# The existing autotools class regenerates the omitted release build files.
SRC_URI:remove = "${GNUPG_MIRROR}/libgpg-error/libgpg-error-${PV}.tar.bz2"
SRC_URI:append = " git://github.com/gpg/libgpg-error.git;protocol=https;nobranch=1;destsuffix=${BP}"
SRCREV = "77b7c5ff6b756870811acaff53df0ebf1e5c2368"
