# Same upstream v2.6.4 release. Preserve patches and license checks;
# the inherited autotools/gettext classes regenerate release build files.
SRC_URI:remove = "${KERNELORG_MIRROR}/linux/utils/${BPN}/${BP}.tar.xz"
SRC_URI:append = " git://github.com/legionus/kbd.git;protocol=https;nobranch=1;destsuffix=${BP}"
SRCREV = "d27e4a38e7cb0a0ff0665e8017425911a7cc04f0"
# Match AC_CONFIG_AUX_DIR when autotools supplies gettext's config.rpath.
AUTOTOOLS_AUXDIR = "${S}/config"
do_configure:prepend() {
    install -d ${AUTOTOOLS_AUXDIR}
    # Normally supplied by autopoint, which Yocto intentionally excludes.
    install -m 0644 ${STAGING_DATADIR_NATIVE}/gettext/ABOUT-NLS ${S}/ABOUT-NLS
}

# Git omits generated parser.c/parser.h and the standard gettext ABOUT-NLS.
DEPENDS:append = " bison-native gettext-native"
