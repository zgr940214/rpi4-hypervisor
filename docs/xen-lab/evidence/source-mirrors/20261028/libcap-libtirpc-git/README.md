# libcap and libtirpc fixed release sources

The layer selects the same upstream versions from immutable Git release
commits because the original archive hosts were unavailable. The existing
Yocto patches, license checks and source-directory layout are preserved.
The JSON files record release tags, commit and tree identities, and checks.

Both source repositories passed `git fsck --full`. All original target
patches applied: four for libcap 2.69 and three for libtirpc 1.3.4. The original
recipe's license-file MD5 values also passed, including libtirpc's source
license excerpt and libcap's optional PAM license.

`native-build.log` records a successful offline host build in the existing
`pi4-xen-qemu:4.19` container, after applying those patches. libtirpc's normal
autotools generation, configure, and compilation passed. libcap's plain
Makefiles compiled its shared libraries and tools with PAM and Go disabled.
This standalone bootstrap check used `USE_GPERF=no`; the unchanged Yocto
recipe uses its `gperf-native` dependency with `USE_GPERF=yes`.

`libcap-built-library-check.log` confirms that the resulting `capsh` loaded
the newly built `libcap.so.2` and executed successfully. `check-native.sh`
records the build commands. These checks establish release-source build
feasibility; Yocto cross compilation and the full Pi4 image's QEMU boot are
separate validation steps.
