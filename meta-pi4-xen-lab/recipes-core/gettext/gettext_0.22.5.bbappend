require gettext-source-mirror.inc

# Release Git trees omit generated parsers that the distribution tarball
# includes. Generate them through upstream's normal Makefile rules.
DEPENDS:append = " bison-native"

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
