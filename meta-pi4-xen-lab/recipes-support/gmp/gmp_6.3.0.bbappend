# Same upstream tar stream in XZ form, pinned to an immutable mirror commit.
# Identity proof: decompressing this file and recompressing with bzip2 -9
# reproduces Poky's ORIGINAL ac28211a... tar.bz2 SHA256 exactly. Thus this
# selects a known matching source archive rather than accepting new code.
SRC_URI:remove = "https://gmplib.org/download/${BPN}/${BP}${REVISION}.tar.bz2"
SRC_URI:append = " https://raw.githubusercontent.com/spleen1981/GMP_tarballs/135946054b0ee10925d9fb58edab7e90d9606145/gmp-6.3.0.tar.xz"
SRC_URI[sha256sum] = "a3c2b80201b89e68616f4ad30bc66aee4927c3ce50e33929ca819d5c43538898"
