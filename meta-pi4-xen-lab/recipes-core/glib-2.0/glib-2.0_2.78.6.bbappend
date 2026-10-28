# Use the immutable upstream 2.78.6 release commit when GNOME's release
# archive host is unavailable. Keep the recipe's patches and license checks.
SRC_URI:remove = "${GNOME_MIRROR}/glib/${SHRT_VER}/glib-${PV}.tar.xz"
SRC_URI:append = " \
    git://github.com/GNOME/glib.git;protocol=https;nobranch=1;name=glib;destsuffix=glib-${PV} \
    git://github.com/GNOME/gvdb.git;protocol=https;nobranch=1;name=gvdb;destsuffix=glib-${PV}/subprojects/gvdb \
"
SRCREV_glib = "d40f72e98e4734ba826ba9a278814530720ba760"
# This is the gitlink recorded by GLib's 2.78.6 release, not a moving branch.
SRCREV_gvdb = "0854af0fdb6d527a8d1999835ac2c5059976c210"
SRCREV_FORMAT = "glib_gvdb"
