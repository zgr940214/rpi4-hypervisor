FROM pi4-xen-build:scarthgap
USER root
RUN --mount=type=secret,id=ca_bundle,mode=0444,required=true \
    set -eu; \
    printf 'Acquire::https::CaInfo "/run/secrets/ca_bundle";\n' > /etc/apt/apt.conf.d/99-session-ca; \
    dpkg --add-architecture arm64; \
    sed -i 's/^deb /deb [arch=amd64] /' /etc/apt/sources.list; \
    printf '%s\n' \
      'deb [arch=arm64] https://ports.ubuntu.com/ubuntu-ports jammy main universe' \
      'deb [arch=arm64] https://ports.ubuntu.com/ubuntu-ports jammy-updates main universe' \
      'deb [arch=arm64] https://ports.ubuntu.com/ubuntu-ports jammy-security main universe' \
      > /etc/apt/sources.list.d/arm64.list; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      qemu-system-arm qemu-utils qemu-user-static gcc-aarch64-linux-gnu \
      g++-aarch64-linux-gnu acpica-tools autoconf automake libtool pkg-config \
      libyajl-dev:arm64 libaio-dev:arm64 libfdt-dev:arm64 libncurses-dev:arm64 \
      liblzma-dev:arm64 zlib1g-dev:arm64 libzstd-dev:arm64 uuid-dev:arm64 \
      libbz2-dev:arm64; \
    rm -f /etc/apt/apt.conf.d/99-session-ca; \
    rm -rf /var/lib/apt/lists/*
USER builder
WORKDIR /work
