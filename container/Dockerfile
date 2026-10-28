FROM ubuntu:22.04@sha256:e0f80c829509ef4df9e76bd8944eb7b8ec25cbb379b112a7f9448b2c77a77c9b

# Supply a combined CA bundle as a BuildKit secret in managed environments.
RUN --mount=type=secret,id=ca_bundle,mode=0444 \
    set -eu; \
    if [ -f /run/secrets/ca_bundle ]; then \
      printf 'Acquire::https::CaInfo "/run/secrets/ca_bundle";\n' > /etc/apt/apt.conf.d/99-session-ca; \
    fi; \
    sed -i 's|http://archive.ubuntu.com|https://archive.ubuntu.com|g; s|http://security.ubuntu.com|https://security.ubuntu.com|g' /etc/apt/sources.list; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      autoconf automake bash bc bison build-essential ca-certificates chrpath cpio curl debianutils \
      device-tree-compiler diffstat e2fsprogs file flex gawk git iproute2 \
      iputils-ping libacl1 liblz4-tool libncurses-dev libssl-dev locales \
      mtools openssh-client openssl patch python3 python3-git python3-jinja2 \
      python3-pexpect python3-pip python3-subunit rsync socat texinfo unzip \
      tcl util-linux wget xz-utils zstd; \
    locale-gen en_US.UTF-8; \
    rm -f /etc/apt/apt.conf.d/99-session-ca; \
    rm -rf /var/lib/apt/lists/*

RUN useradd --uid 1000 --create-home --shell /bin/bash builder
ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
USER builder
WORKDIR /work
