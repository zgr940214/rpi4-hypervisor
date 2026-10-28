# scripts/container.sh pins the native build host to Ubuntu 22.04. Native
# tools are built for this host; target libc is still compiled by Yocto.
INHERIT:remove = "uninative"
PI4_XEN_FIXED_NATIVE_HOST = "1"
BB_HASHSERVE = ""
BB_SIGNATURE_HANDLER = "OEBasicHash"
SSTATE_MIRRORS = ""
CONNECTIVITY_CHECK_URIS = "https://github.com/yoctoproject/poky"
