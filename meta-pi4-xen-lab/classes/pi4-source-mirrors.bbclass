# Distribution mirrors sometimes rename byte-identical archives. BitBake's
# PREMIRRORS preserves the original basename in the remote URL, so use explicit
# source URLs with downloadfilename while retaining every original checksum.
python () {
    import os
    import bb.fetch2

    words = (d.getVar("PI4_XEN_ARCHIVE_MIRRORS") or "").split()
    if len(words) % 2:
        bb.fatal("PI4_XEN_ARCHIVE_MIRRORS must contain original/mirror URL pairs")
    mirrors = dict(zip(words[::2], words[1::2]))
    original = (d.getVar("SRC_URI") or "").split()
    updated = []
    for uri in original:
        source, *parameters = uri.split(";")
        mirror = mirrors.get(source)
        if mirror:
            if not any(item.startswith("downloadfilename=") for item in parameters):
                filename = os.path.basename(bb.fetch2.decodeurl(source)[2])
                parameters.append("downloadfilename=" + filename)
            uri = ";".join([mirror] + parameters)
        updated.append(uri)
    if updated != original:
        d.setVar("SRC_URI", " ".join(updated))
}
