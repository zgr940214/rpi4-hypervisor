#!/bin/bash
set -euo pipefail
cd /work/local/crypto-mirrors/libtirpc
autoreconf -fiv
./configure --disable-gssapi --disable-authdes
make -j2
./configure --version
cd /work/local/crypto-mirrors/libcap
make -j2 PAM_CAP=no GOLANG=no DYNAMIC=yes USE_GPERF=no RAISE_SETFCAP=no
LD_LIBRARY_PATH="$PWD/libcap" ./progs/capsh --print
