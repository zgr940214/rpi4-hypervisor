"""Mirror staging must retain recipe checksums and existing cache contents."""
import bz2
import hashlib
import importlib.util
import io
import lzma
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('mirror_sources', Path(__file__).resolve().parents[1] / 'scripts/mirror-sources.py')
MIRRORS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIRRORS)


class MirrorSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = b'original upstream source bytes'
        self.source = {'recipe': 'test-native', 'url': 'https://mirror.example/test-1.0.tar.gz',
                       'localpath': '/work/downloads/test-1.0.tar.gz',
                       'sha256': hashlib.sha256(self.payload).hexdigest()}

    def test_verified_bytes_are_staged(self):
        with patch.object(MIRRORS, 'urlopen', return_value=io.BytesIO(self.payload)):
            result = MIRRORS.download(self.source, self.root, {'mirror.example'})
        self.assertEqual(result['status'], 'MIRROR_VERIFIED')
        self.assertEqual((self.root / 'test-1.0.tar.gz').read_bytes(), self.payload)
        self.assertFalse(list(self.root.glob('*.mirror-part')))

    def test_mismatched_mirror_is_not_cached(self):
        with patch.object(MIRRORS, 'urlopen', return_value=io.BytesIO(b'wrong source')):
            result = MIRRORS.download(self.source, self.root, {'mirror.example'})
        self.assertEqual(result['status'], 'UNRESOLVED')
        self.assertEqual(result['attempts'][0]['status'], 'HASH_MISMATCH')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_cache_mismatch_is_preserved_not_overwritten(self):
        cached = self.root / 'test-1.0.tar.gz'
        cached.write_bytes(b'user-owned existing archive')
        with patch.object(MIRRORS, 'urlopen') as fetch:
            result = MIRRORS.download(self.source, self.root, {'mirror.example'})
        fetch.assert_not_called()
        self.assertEqual(result['status'], 'EXISTING_CACHE_MISMATCH')
        self.assertEqual(cached.read_bytes(), b'user-owned existing archive')

    def test_verified_cache_needs_no_network(self):
        (self.root / 'test-1.0.tar.gz').write_bytes(self.payload)
        with patch.object(MIRRORS, 'urlopen') as fetch:
            result = MIRRORS.download(self.source, self.root, set())
        fetch.assert_not_called()
        self.assertEqual(result['status'], 'CACHED_VERIFIED')

    def test_unpinned_archive_is_refused(self):
        self.source['sha256'] = None
        with patch.object(MIRRORS, 'urlopen') as fetch:
            result = MIRRORS.download(self.source, self.root, {'mirror.example'})
        fetch.assert_not_called()
        self.assertEqual(result['status'], 'NO_RECIPE_SHA256')

    def test_denied_original_host_is_not_requested(self):
        urls = MIRRORS.candidates(self.source, {'mirror.bazel.build'})
        self.assertTrue(urls)
        self.assertTrue(all(url.startswith('https://mirror.bazel.build/') for url in urls))

    def test_gcc_canonical_mirror_preserves_version_directory(self):
        self.source.update(url='https://ftpmirror.gnu.org/gnu/gcc/gcc-13.5.0/gcc-13.5.0.tar.xz', localpath='/work/downloads/gcc-13.5.0.tar.xz')
        urls = MIRRORS.candidates(self.source, {'mirror.bazel.build'})
        self.assertIn('https://mirror.bazel.build/ftp.gnu.org/gnu/gcc/gcc-13.5.0/gcc-13.5.0.tar.xz', urls)

    def test_debian_native_archive_preserves_original_path(self):
        self.source.update(url='https://ftp.debian.org/debian/pool/main/n/netbase/netbase_6.4.tar.xz', localpath='/work/downloads/netbase_6.4.tar.xz')
        urls = MIRRORS.candidates(self.source, {'deb.debian.org'})
        self.assertIn('https://deb.debian.org/debian/pool/main/n/netbase/netbase_6.4.tar.xz', urls)

    def test_recompression_must_match_original_archive_hash(self):
        expected = bz2.compress(self.payload, compresslevel=9)
        self.source.update(url='https://gmplib.org/download/gmp/gmp-6.3.0.tar.bz2',
                           localpath='/work/downloads/gmp-6.3.0.tar.bz2',
                           sha256=hashlib.sha256(expected).hexdigest())
        with patch.object(MIRRORS, 'urlopen', return_value=io.BytesIO(lzma.compress(self.payload))):
            result = MIRRORS.download(self.source, self.root, {'raw.githubusercontent.com'})
        self.assertEqual(result['status'], 'MIRROR_VERIFIED')
        self.assertEqual(result['transformation'], 'xz-to-bzip2-9')
        self.assertEqual((self.root / 'gmp-6.3.0.tar.bz2').read_bytes(), expected)


if __name__ == '__main__':
    unittest.main()
