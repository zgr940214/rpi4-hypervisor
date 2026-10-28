# Same upstream popt-1.19-release commit. The existing autotools/gettext
# classes generate configure; the original license checksum remains in force.
SRC_URI:remove = "http://ftp.rpm.org/popt/releases/popt-1.x/${BP}.tar.gz"
SRC_URI:append = " git://github.com/rpm-software-management/popt.git;protocol=https;nobranch=1;destsuffix=${BP}"
SRCREV = "916e61045d268f7e37ade5ec047eb77e8299e6ad"
# Unlike a release archive, Git has no gettext-generated config.rpath.
# Match AC_CONFIG_AUX_DIR so autotools stages it in the required directory.
AUTOTOOLS_AUXDIR = "${S}/build-aux"
do_configure:prepend() {
    install -d ${AUTOTOOLS_AUXDIR}
}
