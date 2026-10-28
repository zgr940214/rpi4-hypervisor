require gettext-source-mirror.inc

# Release Git trees omit generated parsers and gperf lookup headers that the
# distribution tarball includes. Generate them through upstream Makefile rules.
DEPENDS:append = " bison-native gperf-native"

# Upstream imports gnulib and generates configure/Makefile.in before Poky's
# patches. The build container supplies the documented Autoconf 2.71 and
# Automake 1.16 bootstrap tools; this step runs entirely from fixed sources.
do_unpack[postfuncs] += "pi4_gettext_source_bootstrap"
pi4_gettext_source_bootstrap() {
    for tool in /usr/bin/autoconf /usr/bin/autoheader /usr/bin/aclocal /usr/bin/automake; do
        test -x "$tool" || bbfatal "Missing build-host bootstrap tool: $tool"
    done
    cd ${S}
    printf '%s\n' '${PV}' > .tarball-version
    PATH=/usr/bin:/bin GNULIB_SRCDIR=${WORKDIR}/gettext-gnulib ./autogen.sh
    # autogen's --local-symlink imports are regular files in release archives.
    # Materialize them so the unchanged recipe patches can edit their copies.
    find ${S} -type l -exec sh -c '
        for file; do
            if test -f "$file"; then
                cp -pL "$file" "$file.pi4-copy" && mv -f "$file.pi4-copy" "$file" || exit 1
            fi
        done
    ' sh {} +
}

# This is an auxiliary historical-data source, not the gettext implementation.
# Upstream explicitly requires archive.dir.tar from an installed release when
# building Git. All 50 snapshots understood by autopoint 0.22.5 are present;
# its 0.22.5 snapshot matches all 22 original release files byte-for-byte.
# The main source revision, PV, ARCHIVE_VERSION and licenses stay at 0.22.5.
FILESEXTRAPATHS:prepend := "${THISDIR}/files:"
SRC_URI:append = " https://deb.debian.org/debian/pool/main/g/gettext/gettext_0.23.1.orig.tar.xz;name=autopoint_history;downloadfilename=gettext-autopoint-history-0.23.1.tar.xz;unpack=0 file://0001-build-skip-generated-manuals.patch"
SRC_URI[autopoint_history.sha256sum] = "c1f97a72a7385b7e71dd07b5fea6cdaf12c9b88b564976b23bd8c11857af2970"

do_unpack[postfuncs] += "pi4_gettext_history_unpack"
python pi4_gettext_history_unpack() {
    import hashlib
    import os
    import tarfile

    source = os.path.join(d.getVar("WORKDIR"), "gettext-autopoint-history-0.23.1.tar.xz")
    with tarfile.open(source, "r:xz") as archive:
        member = archive.getmember("gettext-0.23.1/gettext-tools/misc/archive.dir.tar")
        if not member.isfile():
            bb.fatal("Expected regular upstream autopoint history archive")
        data = archive.extractfile(member).read()
    if hashlib.sha256(data).hexdigest() != "418bf9988aec981b047e88823abe97e3306e2578d845a223038a3097d62d8623":
        bb.fatal("Unexpected upstream autopoint history archive")
    destination = os.path.join(d.getVar("S"), "gettext-tools/misc/archive.dir.tar")
    with open(destination, "wb") as output:
        output.write(data)
}
