# Same upstream version, explicitly selecting Ubuntu's XZ source artifact.
# Its SHA256 is authenticated by Noble's signed universe Sources index.
SRC_URI:remove = "${SAVANNAH_GNU_MIRROR}/lzip/lzlib/lzlib-${PV}.tar.gz"
SRC_URI:append = " https://archive.ubuntu.com/ubuntu/pool/universe/l/lzlib/lzlib_${PV}.orig.tar.xz;downloadfilename=lzlib-${PV}.tar.xz"
SRC_URI[sha256sum] = "decd2ef0752a20e77bd13b4c10bbadd5b0289166895a5808f8911ebd9709f324"
