# ACL and attr release archive authentication

The Yocto versions remain ACL 2.3.2 and attr 2.5.1. Their original gzip
archives were unavailable through the configured network, so the layer selects
the same upstream releases in XZ format from Debian's source pool. These are
upstream source archives, not Debian binaries or a prebuilt operating system.

`verified-archives.json` records both archive hashes and the authentication
chain. `signature.log` contains the actual successful `gpgv` output using the
environment's preinstalled Debian archive keyring. The corresponding signed
`InRelease` files and source-package stanzas are included here.

Verification performed on 2026-10-28:

1. Verify Debian's `InRelease` signatures using its preinstalled archive keyring.
2. Match each compressed `Sources.xz` file's length and SHA256 against the
   signed release's `main/source/Sources.xz` entry.
3. Match each downloaded upstream XZ archive's length and SHA256 against that
   source package's `Checksums-Sha256` entry.
4. Check the unchanged Yocto license-file MD5 values, including attr's two
   source-file license excerpts. All passed.
5. Apply the original Yocto patches: one for attr and two for ACL. All passed.

The verified full source indexes remain in
`local/source-mirror-probes/debian-source-auth/Sources.xz` (Bookworm) and
`local/crypto-mirrors/debian-trixie-auth/Sources.xz` (Trixie). Their exact hashes,
lengths and upstream URLs are recorded in the JSON; later Debian point
releases can change the current index. The Bookworm index is also retained in
the adjacent `gnu-xz` evidence directory. This source verification is separate
from the final Yocto image build and QEMU boot results.
