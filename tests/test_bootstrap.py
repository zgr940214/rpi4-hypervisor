"""Exercise pinned mirror retrieval against real temporary Git repositories."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location('bootstrap', Path(__file__).resolve().parents[1] / 'scripts/bootstrap.py')
BOOTSTRAP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOOTSTRAP)


@unittest.skipUnless(shutil.which('git'), 'requires Git')
class BootstrapMirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.seed = self.root / 'seed'
        self.seed.mkdir()
        self.git(self.seed, 'init', '-q')
        self.git(self.seed, 'config', 'user.name', 'Mirror Test')
        self.git(self.seed, 'config', 'user.email', 'mirror-test@example.invalid')
        (self.seed / 'payload').write_text('pinned source\n')
        self.git(self.seed, 'add', 'payload')
        self.git(self.seed, 'commit', '-qm', 'Pinned source')
        self.revision = self.git(self.seed, 'rev-parse', 'HEAD')
        # The mirror's branch tip is newer than the requested fixed revision.
        (self.seed / 'payload').write_text('newer source\n')
        self.git(self.seed, 'commit', '-qam', 'Newer branch tip')
        self.mirror = self.root / 'mirror.git'
        subprocess.run(['git', 'clone', '--bare', str(self.seed), str(self.mirror)],
                       check=True, capture_output=True, text=True)
        self.canonical = (self.root / 'unreachable-upstream.git').as_uri()
        self.lock = {'repositories': [{'name': 'fixture', 'url': self.canonical,
                                      'mirrors': [self.mirror.as_uri()], 'commit': self.revision}]}
        (self.root / 'sources.lock.json').write_text(json.dumps(self.lock))
        self.checkout = self.root / '.cache/sources/fixture'

    @staticmethod
    def git(path, *args):
        return subprocess.check_output(['git', '-C', str(path), *args], text=True, stderr=subprocess.PIPE).strip()

    def bootstrap(self):
        with patch.object(BOOTSTRAP, 'ROOT', self.root), redirect_stdout(io.StringIO()):
            BOOTSTRAP.main()

    def test_mirror_fetches_exact_pin_and_preserves_canonical_origin(self):
        self.bootstrap()
        self.assertEqual(self.git(self.checkout, 'rev-parse', 'HEAD'), self.revision)
        self.assertEqual((self.checkout / 'payload').read_text(), 'pinned source\n')
        self.assertEqual(self.git(self.checkout, 'remote', 'get-url', 'origin'), self.canonical)
        self.assertEqual(self.git(self.checkout, 'status', '--porcelain'), '')

    def test_repeat_reuses_verified_checkout_without_available_remote(self):
        self.bootstrap()
        self.mirror.rename(self.root / 'mirror-offline.git')
        self.bootstrap()
        self.assertEqual(self.git(self.checkout, 'rev-parse', 'HEAD'), self.revision)

    def test_dirty_checkout_is_preserved_and_rejected(self):
        self.bootstrap()
        (self.checkout / 'payload').write_text('user edit\n')
        with self.assertRaisesRegex(SystemExit, 'Preserve local changes'):
            self.bootstrap()
        self.assertEqual((self.checkout / 'payload').read_text(), 'user edit\n')

    def test_unconfigured_origin_is_rejected_even_with_correct_commit(self):
        self.bootstrap()
        self.git(self.checkout, 'remote', 'set-url', 'origin', (self.root / 'other.git').as_uri())
        with self.assertRaisesRegex(SystemExit, 'unexpected origin'):
            self.bootstrap()


if __name__ == '__main__':
    unittest.main()
