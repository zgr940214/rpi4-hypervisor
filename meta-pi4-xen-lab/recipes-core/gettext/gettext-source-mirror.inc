# Preserve the upstream gettext 0.22.5 release and the exact gnulib commit
# recorded by that release's Git submodule. These fixed Git sources replace
# the unavailable distribution archive; its original checksum stays unchanged.
SRC_URI:remove = "${GNU_MIRROR}/gettext/gettext-${PV}.tar.gz"
SRC_URI:prepend = "git://github.com/autotools-mirror/gettext.git;protocol=https;nobranch=1;name=gettext;destsuffix=gettext-${PV} git://github.com/coreutils/gnulib.git;protocol=https;nobranch=1;name=gnulib;destsuffix=gettext-gnulib "
SRCREV_gettext = "0d53c885229fc59ca3ce6a8e70fb3f6d59ece361"
SRCREV_gnulib = "dd801be6c84325d140c67ec9869b3844bc5550ac"
SRCREV_FORMAT = "gettext_gnulib"
