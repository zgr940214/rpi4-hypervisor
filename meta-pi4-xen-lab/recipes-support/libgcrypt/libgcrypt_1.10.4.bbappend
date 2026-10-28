# Use the official libgcrypt-1.10.4 release commit. The Git checkout keeps
# the release tag available to autogen.sh's version detection; the base
# recipe still applies every patch and verifies its original license hashes.
SRC_URI:remove = "${GNUPG_MIRROR}/libgcrypt/libgcrypt-${PV}.tar.bz2"
SRC_URI:append = " git://github.com/gpg/libgcrypt.git;protocol=https;nobranch=1;destsuffix=${BP}"
SRCREV = "d365a41094571f2cce18f27b53ffdceb540f77bb"
