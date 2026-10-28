require gettext-source-mirror.inc

# This recipe installs M4 macros only. Supply the files imported from gnulib
# by upstream autogen.sh without bootstrapping the unrelated gettext programs.
do_unpack[postfuncs] += "pi4_gettext_minimal_sources"
pi4_gettext_minimal_sources() {
    install -d ${S}/gettext-runtime/gnulib-m4 ${S}/build-aux
    for file in host-cpu-c-abi.m4 lib-ld.m4 lib-link.m4 lib-prefix.m4; do
        cp ${WORKDIR}/gettext-gnulib/m4/$file ${S}/gettext-runtime/gnulib-m4/
    done
    cp ${WORKDIR}/gettext-gnulib/m4/build-to-host.m4 ${S}/gettext-runtime/m4/
    cp ${WORKDIR}/gettext-gnulib/build-aux/config.rpath ${S}/build-aux/
}
