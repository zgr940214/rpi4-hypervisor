#!/usr/bin/env python3
"""Export resolved source URLs and existing checksums from the selected build.

Run after `bitbake -g pi4-xen-dom0-image`, in the initialized BitBake build
environment. This inspects metadata only and never downloads or trusts a mirror.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.cache/sources/poky/bitbake/lib'))
import bb.fetch2
import bb.tinfoil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--buildlist', type=Path, default=Path('pn-buildlist'))
    parser.add_argument('--output', type=Path, default=ROOT / 'local/source-manifest.json')
    args = parser.parse_args()
    sources = []
    with bb.tinfoil.Tinfoil(setup_logging=False) as info:
        info.prepare(quiet=2)
        for recipe in args.buildlist.read_text().splitlines():
            data = info.parse_recipe(recipe)
            data.setVar('BB_NO_NETWORK', '1')
            uris = (data.getVar('SRC_URI') or '').split()
            fetch = bb.fetch2.Fetch(uris, data, cache=False)
            for uri, source in fetch.ud.items():
                if source.type == 'file':
                    continue
                sources.append({'recipe': recipe, 'version': data.getVar('PV'),
                                'url': uri, 'type': source.type,
                                'localpath': fetch.localpath(uri),
                                'sha256': getattr(source, 'sha256_expected', None),
                                'md5': getattr(source, 'md5_expected', None),
                                'revisions': getattr(source, 'revisions', {}),
                                'branches': getattr(source, 'branches', {})})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'sources': sources}, indent=2, sort_keys=True) + '\n')
    print(f'Recorded {len(sources)} resolved source entries in {args.output}')


if __name__ == '__main__':
    main()
