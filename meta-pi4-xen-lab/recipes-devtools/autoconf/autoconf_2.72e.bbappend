# Preserve release 2.72e using the commit behind its upstream annotated tag.
# Git sources need generated configure/Makefile.in before Poky's existing
# no-man.patch is applied. Upstream bootstrap uses Autoconf FROM THIS SOURCE,
# with the fixed Ubuntu build host's Automake, GNU M4 and Perl as bootstrap tools.
# Evidence: docs/xen-lab/evidence/source-mirrors/20261028/autoconf/.
SRC_URI:remove = "https://alpha.gnu.org/gnu/autoconf/${BP}.tar.gz"
SRC_URI:append = " git://github.com/autotools-mirror/autoconf.git;protocol=https;nobranch=1"
SRCREV = "ba087b38f8fb360674db5ece1d3e0394dc6a998a"
S = "${WORKDIR}/git"

do_unpack[postfuncs] += "pi4_autoconf_source_bootstrap"
pi4_autoconf_source_bootstrap() {
    for tool in /usr/bin/aclocal /usr/bin/automake /usr/bin/m4 /usr/bin/perl; do
        test -x "$tool" || bbfatal "Missing build-host bootstrap tool: $tool"
    done
    cd ${S}
    # git-version-gen supports this file for release trees without local tags.
    printf '%s\n' '${PV}' > .tarball-version
    ACLOCAL=/usr/bin/aclocal AUTOMAKE=/usr/bin/automake \
        M4=/usr/bin/m4 PERL=/usr/bin/perl ./bootstrap -v
}
