# Use upstream v2.12.10's immutable release commit. Existing license checks
# and all Scarthgap patches still apply; autotools regenerates configure.
SRC_URI:remove = "${GNOME_MIRROR}/${GNOMEBN}/${@gnome_verdir('${PV}')}/${GNOMEBN}-${PV}.tar.${GNOME_COMPRESS_TYPE};name=archive"
SRC_URI:append = " git://github.com/GNOME/libxml2.git;protocol=https;nobranch=1;destsuffix=${BP}"
SRCREV = "02d577715e1951cf114ca4e9adaf5605156c4f4c"
