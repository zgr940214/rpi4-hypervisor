# Mirror the upstream v1.2 release and import precisely the gnulib revision
# recorded in its version.sh. Both revisions are fixed; the original recipe
# license checks still apply to the release source.
SRC_URI:remove = "${GNU_MIRROR}/libunistring/libunistring-${PV}.tar.gz"
SRC_URI:append = " \
    git://github.com/GitMirroring/libunistring.git;protocol=https;nobranch=1;name=libunistring;destsuffix=${BP} \
    git://github.com/coreutils/gnulib.git;protocol=https;nobranch=1;name=gnulib;destsuffix=gnulib \
"
SRCREV_libunistring = "479b580dedca32662b34336183abfec95b71c42e"
SRCREV_gnulib = "5828723e285945975dbb3d2e89cd8854d5b7a075"
SRCREV_FORMAT = "libunistring_gnulib"

do_configure:prepend() {
    cd ${S}
    # Avoid autogen.sh's optional network request for texinfo.tex. Its own
    # fallback uses this exact file from the release's gnulib checkout.
    install -m 0644 ${WORKDIR}/gnulib/build-aux/texinfo.tex ${S}/build-aux/texinfo.tex
    touch ${S}/ChangeLog
    GNULIB_SRCDIR=${WORKDIR}/gnulib ./autogen.sh
    cd ${B}
}
