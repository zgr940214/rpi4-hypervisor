#!/usr/bin/env python3
"""Fill BitBake's download cache from mirrors, accepting only recipe SHA256s.

Input is source-manifest.py's expanded metadata. No checksum is rewritten and
the normal proxy/TLS configuration is preserved. BitBake verifies cached bytes
again when its own fetch task executes.
"""
import argparse
import bz2
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import lzma
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(data)
    return result.hexdigest()


def candidates(source, allowed):
    """Candidate existence is not trusted: every response must match SHA256."""
    original = source['url'].split(';', 1)[0]
    parsed = urlsplit(original)
    name = Path(source['localpath']).name
    urls = []
    if parsed.hostname in allowed:
        urls.append(original.replace('http://', 'https://', 1))
    if parsed.hostname != 'mirror.bazel.build':
        urls.append('https://mirror.bazel.build/' + parsed.netloc + parsed.path)
        normalized = re.sub(r'/{2,}', '/', parsed.path)
        if normalized != parsed.path:
            urls.append('https://mirror.bazel.build/' + parsed.netloc + normalized)
    if parsed.hostname == 'ftpmirror.gnu.org':
        urls.append('https://mirror.bazel.build/ftp.gnu.org' + parsed.path)
    if parsed.hostname == 'ftp.debian.org':
        urls.append('https://deb.debian.org' + parsed.path)
    github_tar = re.fullmatch(r'/repos/([^/]+)/([^/]+)/tarball/([^/]+)', parsed.path)
    if parsed.hostname == 'api.github.com' and github_tar:
        owner, repo, revision = github_tar.groups()
        urls.append(f'https://codeload.github.com/{owner}/{repo}/legacy.tar.gz/{revision}')
    if name == 'unzip60.tar.gz':
        urls.append('https://deb.debian.org/debian/pool/main/u/unzip/unzip_6.0.orig.tar.gz')
    match = re.fullmatch(r'(.+?)[_-](\d[^/]*?)(\.tar\.(?:gz|xz|bz2|lz|lzma|zst)|\.tgz|\.zip)', name)
    if match:
        package, version, extension = match.groups()
        gnu_package = {'libmpc': 'mpc'}.get(package, package)
        urls.append(f'https://mirror.bazel.build/ftp.gnu.org/gnu/{gnu_package}/{name}')
        if package == 'zlib':
            urls.append(f'https://github.com/madler/zlib/releases/download/v{version}/{name}')
        if package == 'openssl':
            urls.append(f'https://github.com/openssl/openssl/releases/download/openssl-{version}/{name}')
        if package == 'Python':
            urls.append(f'https://github.com/python/cpython/releases/download/v{version}/{name}')
        if package == 'curl':
            urls.append(f'https://github.com/curl/curl/releases/download/curl-{version.replace(".", "_")}/{name}')
        if package == 'libarchive':
            urls.append(f'https://github.com/libarchive/libarchive/releases/download/v{version}/{name}')
        aliases = {'xz': ['xz-utils'], 'libcap': ['libcap2'], 'mpfr': ['mpfr4'],
                   'mpc': ['mpclib3'], 'libmpc': ['mpclib3'],
                   'automake': ['automake-1.16', 'automake-1.17'],
                   'Python': ['python' + '.'.join(version.split('.')[:2])],
                   'libpam': ['pam'], 'shadow': ['shadow'], 'libnsl': ['libnsl'],
                   'gptfdisk': ['gdisk'], 'e2fsprogs': ['e2fsprogs'], 'lzo': ['lzo2'],
                   'lua': ['lua' + '.'.join(version.split('.')[:2])], 'libtasn1': ['libtasn1-6']}
        if package == 'libedit' and re.fullmatch(r'\d{8}-3\.1', version):
            version = '3.1-' + version.split('-')[0]
        for source_name in aliases.get(package, [package]):
            prefix = source_name[:4] if source_name.startswith('lib') else source_name[0]
            archive = f'{source_name}_{version}.orig{extension}'
            paths = [f'pool/main/{prefix}/{source_name}/{archive}']
            if package == 'base-passwd':
                paths.append(f'pool/main/{prefix}/{source_name}/{source_name}_{version}{extension}')
            for path in paths:
                urls.append('https://deb.debian.org/debian/' + path)
                urls.append('https://archive.ubuntu.com/ubuntu/' + path)
            urls.append(f'https://archive.ubuntu.com/ubuntu/pool/universe/{prefix}/{source_name}/{archive}')
    # Only ordinary requests to explicitly permitted mirror hosts. Never change
    # host resolution, proxy selection, or certificate checking.
    return list(dict.fromkeys(url for url in urls if urlsplit(url).hostname in allowed))


def download(source, downloads, allowed, timeout=20):
    name = Path(source['localpath']).name
    expected = source.get('sha256')
    result = {'name': name, 'recipe': source['recipe'], 'sha256': expected, 'attempts': []}
    if not re.fullmatch(r'[a-fA-F0-9]{64}', expected or ''):
        return dict(result, status='NO_RECIPE_SHA256')
    target = downloads / name
    if target.exists():
        if digest(target) == expected:
            return dict(result, status='CACHED_VERIFIED')
        return dict(result, status='EXISTING_CACHE_MISMATCH')
    attempts = [(url, None) for url in candidates(source, allowed)]
    if name == 'gmp-6.3.0.tar.bz2' and 'raw.githubusercontent.com' in allowed:
        attempts.append(('https://raw.githubusercontent.com/spleen1981/GMP_tarballs/main/gmp-6.3.0.tar.xz', 'xz-to-bzip2-9'))
    for url, transformation in attempts:
        temporary = None
        try:
            checksum = hashlib.sha256()
            with tempfile.NamedTemporaryFile(prefix=name + '.', suffix='.mirror-part', dir=downloads, delete=False) as stream:
                temporary = Path(stream.name)
                with urlopen(url, timeout=timeout) as response:
                    while True:
                        data = response.read(1024 * 1024)
                        if not data:
                            break
                        checksum.update(data)
                        stream.write(data)
            if transformation:
                # Reconstruct the exact ORIGINAL checksum-pinned archive. This
                # does not authorize a new checksum or a repacked source tree.
                with tempfile.NamedTemporaryFile(prefix=name + '.', suffix='.mirror-part', dir=downloads, delete=False) as stream:
                    converted = Path(stream.name)
                try:
                    with lzma.open(temporary, 'rb') as src, bz2.open(converted, 'wb', compresslevel=9) as dst:
                        while True:
                            data = src.read(1024 * 1024)
                            if not data:
                                break
                            dst.write(data)
                    temporary.unlink()
                    temporary = converted
                except Exception:
                    converted.unlink(missing_ok=True)
                    raise
                actual = digest(temporary)
            else:
                actual = checksum.hexdigest()
            if actual != expected:
                result['attempts'].append({'url': url, 'status': 'HASH_MISMATCH', 'sha256': actual})
                continue
            if target.exists():
                if digest(target) != expected:
                    return dict(result, status='EXISTING_CACHE_MISMATCH')
            else:
                temporary.replace(target)
                temporary = None
            return dict(result, status='MIRROR_VERIFIED', mirror=url, transformation=transformation, bytes=target.stat().st_size)
        except Exception as exc:
            result['attempts'].append({'url': url, 'status': 'FETCH_FAILED', 'error': str(exc)})
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return dict(result, status='UNRESOLVED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'local/source-manifest.json')
    parser.add_argument('--downloads', type=Path, default=ROOT / '.cache/downloads')
    parser.add_argument('--output', type=Path, default=ROOT / 'local/source-mirrors.json')
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--timeout', type=int, default=20)
    parser.add_argument('--only', action='append', help='Resolve only this exact archive filename; may repeat')
    args = parser.parse_args()
    sources = json.loads(args.manifest.read_text())['sources']
    policy_path = Path('/etc/codex/network-policy.json')
    if policy_path.is_file():
        policy = json.loads(policy_path.read_text())
        allowed = {rule['host'] for rule in policy['http_network_policy'].get('egress_rules', [])}
    else:
        # Outside a managed executor, use the caller's normal network and TLS
        # configuration. This branch never modifies routes or proxy settings.
        allowed = {urlsplit(item['url'].split(';', 1)[0]).hostname for item in sources}
        allowed.update(['mirror.bazel.build', 'github.com', 'codeload.github.com',
                        'raw.githubusercontent.com', 'deb.debian.org', 'archive.ubuntu.com'])
    selected = {}
    for item in sources:
        if item['type'] in ('http', 'https', 'ftp'):
            if args.only and Path(item['localpath']).name not in args.only:
                continue
            key = (Path(item['localpath']).name, item.get('sha256'))
            selected.setdefault(key, item)
    names = {}
    for (name, checksum) in selected:
        if name in names and names[name] != checksum:
            raise SystemExit(f'Conflicting recipe hashes for the same download filename: {name}')
        names[name] = checksum
    args.downloads.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(download, item, args.downloads, allowed, args.timeout) for item in selected.values()]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            args.output.write_text(json.dumps({'scope': 'Exact recipe SHA256 source mirrors', 'archives': sorted(results, key=lambda x: x['name'])}, indent=2) + '\n')
            print(result['status'] + ': ' + result['name'], flush=True)
    failed = [r for r in results if r['status'] not in ('CACHED_VERIFIED', 'MIRROR_VERIFIED')]
    print(f'Verified {len(results) - len(failed)}/{len(results)} source archives', flush=True)
    return int(bool(failed))


if __name__ == '__main__':
    raise SystemExit(main())
