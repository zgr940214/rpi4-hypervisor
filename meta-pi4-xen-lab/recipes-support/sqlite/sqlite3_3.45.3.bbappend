# Same SQLite 3.45.3 release from its official Git mirror. Generate the upstream
# amalgamation before Poky's existing patches, which modify sqlite3.c/shell.c.
# The immutable commit identifies this source alternative; the archive checksum
# and original sqlite3.h license checksum remain unchanged.
SRC_URI:remove = "http://www.sqlite.org/2024/sqlite-autoconf-${SQLITE_PV}.tar.gz"
SRC_URI:prepend = "git://github.com/sqlite/sqlite.git;protocol=https;nobranch=1;destsuffix=sqlite-source "
SRCREV = "b74eb00e2cb05d9749859e6fbe77d229ad1dc1e1"

do_unpack[postfuncs] += "pi4_sqlite_source_bootstrap"
pi4_sqlite_source_bootstrap() {
    for tool in /usr/bin/cc /usr/bin/make /usr/bin/tclsh; do
        test -x "$tool" || bbfatal "Missing build-host bootstrap tool: $tool"
    done
    test "$(cat ${WORKDIR}/sqlite-source/VERSION)" = "${PV}" || \
        bbfatal "SQLite Git release version does not match recipe"

    rm -rf ${WORKDIR}/sqlite-bootstrap ${S}
    mkdir -p ${WORKDIR}/sqlite-bootstrap
    (
        cd ${WORKDIR}/sqlite-bootstrap
        # This stage only generates C sources with host tools. The normal
        # autotools tasks subsequently compile the patched sources for each
        # native or target variant using its own Yocto compiler and flags.
        export PATH=/usr/bin:/bin CONFIG_SITE=/dev/null
        export CC=/usr/bin/cc CXX=/usr/bin/c++ CPP='/usr/bin/cc -E'
        export BUILD_CC=/usr/bin/cc CFLAGS= CPPFLAGS= LDFLAGS=
        export BUILD_CFLAGS= BUILD_LDFLAGS= MAKEFLAGS=
        ${WORKDIR}/sqlite-source/configure --disable-tcl --disable-readline
        /usr/bin/make -j1 sqlite3.c sqlite3.h sqlite3ext.h shell.c sqlite3rc.h \
            BCC=/usr/bin/cc CC=/usr/bin/cc TCLSH_CMD=/usr/bin/tclsh
    )

    # Assemble the same autoconf layout as upstream tool/mkautoconfamal.sh.
    # Yocto's autotools class generates configure and Makefile.in later.
    cp -R ${WORKDIR}/sqlite-source/autoconf ${S}
    for file in sqlite3.c sqlite3.h sqlite3ext.h shell.c sqlite3rc.h; do
        cp ${WORKDIR}/sqlite-bootstrap/$file ${S}/
    done
    cp ${WORKDIR}/sqlite-source/sqlite3.1 ${WORKDIR}/sqlite-source/sqlite3.pc.in ${S}/
    cp ${WORKDIR}/sqlite-source/src/sqlite3.rc ${WORKDIR}/sqlite-source/tool/Replace.cs ${S}/
    sed -i 's/--SQLITE-VERSION--/${PV}/g' ${S}/configure.ac
}
