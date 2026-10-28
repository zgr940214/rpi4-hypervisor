#!/usr/bin/env python3
"""Generate only build/conf files; preserve manual edits by refusing conflicts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    conf = ROOT / "build/conf"
    conf.mkdir(parents=True, exist_ok=True)
    layers = ["poky/meta", "poky/meta-poky", "meta-openembedded/meta-oe",
              "meta-openembedded/meta-python", "meta-openembedded/meta-networking",
              "meta-openembedded/meta-filesystems", "meta-raspberrypi", "meta-virtualization"]
    bblayers = 'POKY_BBLAYERS_CONF_VERSION = "2"\nBBPATH = "${TOPDIR}"\nBBFILES ?= ""\nBBLAYERS = " \\\n'
    bblayers += ''.join(f'  /work/.cache/sources/{layer} \\\n' for layer in layers)
    bblayers += '  /work/meta-pi4-xen-lab \\\n"\n'
    local = '''MACHINE = "raspberrypi4-64"
DISTRO = "pi4-xen"
PACKAGE_CLASSES = "package_ipk"
DL_DIR = "/work/.cache/downloads"
SSTATE_DIR = "/work/.cache/sstate"
BB_NUMBER_THREADS = "2"
PARALLEL_MAKE = "-j 2"
INHERIT += "rm_work buildhistory"
BUILDHISTORY_COMMIT = "0"
BB_DISKMON_DIRS = "STOPTASKS,${TMPDIR},3G,100K STOPTASKS,${DL_DIR},3G,100K HALT,${TMPDIR},1G,10K"
CONF_VERSION = "2"
require /work/local/generated/access.inc
require /work/meta-pi4-xen-lab/conf/build-host.inc
include /work/local/site.conf
'''
    for name, contents in [("bblayers.conf", bblayers), ("local.conf", local)]:
        target = conf / name
        previous = contents.replace('require /work/meta-pi4-xen-lab/conf/build-host.inc\n', '')
        if target.exists() and target.read_text() not in (contents, previous):
            raise SystemExit(f"Refusing to overwrite edited {target}; use local/site.conf for overrides")
        target.write_text(contents)
    print("Build configuration prepared in /work/build; overrides: local/site.conf")


if __name__ == "__main__":
    main()
