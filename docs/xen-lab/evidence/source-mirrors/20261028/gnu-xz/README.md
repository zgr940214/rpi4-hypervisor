# GNU source archive format selection

Automake1.16.5, patch2.7.6 and libtool2.4.7 now select the same-version XZ source distribution from Debian's upstream archive mirror. The original gzip artifact hashes are not treated as matching these XZ files. Package versions, licence checks and existing Yocto patches remain unchanged.

Verification performed: installed `/usr/share/keyrings/debian-archive-keyring.gpg` verifies `InRelease`; its SHA256 entry authenticates `Sources.xz`; each saved package stanza's `Checksums-Sha256` authenticates the downloaded `.orig.tar.xz`. `signature.log` preserves the actual GPG verification. GPG's generic web-of-trust warning is separate from the explicitly selected Debian archive keyring trust anchor. Full source-index input is retained for repeatable verification. Source archives themselves remain only in the download cache.

The following source names are mapped to BitBake download names: `automake-1.16_1.16.5.orig.tar.xz`→`automake-1.16.5.tar.xz`, `patch_2.7.6.orig.tar.xz`→`patch-2.7.6.tar.xz`, `libtool_2.4.7.orig.tar.xz`→`libtool-2.4.7.tar.xz`. See `verified-alternate-archives.json` for exact hashes and mirror URLs.
