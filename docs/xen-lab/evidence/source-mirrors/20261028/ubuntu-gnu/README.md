# Same-version Ubuntu source archives

Bash 5.2.21 and lzlib 1.14 retain their recipe versions and original license checksums. Bash retains all original Poky patches, which applied successfully in the recorded preflight. The recipes explicitly select the Ubuntu XZ artifacts; the original GNU gzip checksums were not claimed to match these files.

`signature.log` records verification of Noble InRelease with the Ubuntu archive keyring from the official Ubuntu build-container base. InRelease authenticates `main/source/Sources.xz` and `universe/source/Sources.xz`; each index authenticates the selected `.orig.tar.xz`. `verification.json` records those index and archive digests, and the selected package stanzas are included. The full indices are available at `https://archive.ubuntu.com/ubuntu/dists/noble/{main,universe}/source/Sources.xz`; their original hashes can be checked against the included signed InRelease. They remain cached locally in `local/source-mirror-probes/ubuntu-source-auth/`, rather than duplicating 21 MB in Git.

The Gperf 3.1 Debian source archive is authenticated by the adjacent `gnu-xz/` Bookworm InRelease/Sources.xz chain and `gperf.sources`. Its packaging is a Git archive (not the GNU distribution gzip), so the recipe uses a distinct `gperf-3.1-debian.orig.tar.gz` cache filename and its authenticated SHA256. Both original license hashes and both original patches passed. No Debian binary or prebuilt operating-system image is used.

These checks establish source and patch compatibility; formal BitBake build results are reported separately.
