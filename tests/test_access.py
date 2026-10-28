import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    'configure_access', Path(__file__).resolve().parents[1] / 'scripts/configure-access.py')
ACCESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ACCESS)


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.original_root = ACCESS.ROOT
        self.addCleanup(setattr, ACCESS, 'ROOT', self.original_root)
        ACCESS.ROOT = Path(self.temp.name)
        self.credentials = ACCESS.ROOT / 'local/credentials'
        with contextlib.redirect_stdout(io.StringIO()):
            ACCESS.main()

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.credentials.iterdir()}

    def test_repeated_setup_keeps_usable_matching_credentials(self):
        before = self.snapshot()
        with contextlib.redirect_stdout(io.StringIO()):
            ACCESS.main()
        self.assertEqual(before, self.snapshot())
        self.assertTrue(all(p.stat().st_mode & 0o077 == 0 for p in self.credentials.iterdir()))

    def test_missing_password_does_not_replace_old_hash(self):
        (self.credentials / 'root-password.txt').unlink()
        before = self.snapshot()
        with self.assertRaisesRegex(SystemExit, 'both exist'):
            ACCESS.main()
        self.assertEqual(before, self.snapshot())

    def test_fresh_git_checkout_permissions_are_repaired_before_key_use(self):
        before = self.snapshot()
        for path in self.credentials.iterdir():
            path.chmod(0o644)
        with contextlib.redirect_stdout(io.StringIO()):
            ACCESS.main()
        self.assertEqual(before, self.snapshot())
        self.assertTrue(all(p.stat().st_mode & 0o077 == 0 for p in self.credentials.iterdir()))

    def test_missing_hash_does_not_replace_existing_password(self):
        (self.credentials / 'root-password.sha512').unlink()
        before = self.snapshot()
        with self.assertRaisesRegex(SystemExit, 'both exist'):
            ACCESS.main()
        self.assertEqual(before, self.snapshot())

    def test_mismatched_password_is_detected(self):
        (self.credentials / 'root-password.txt').write_text('incorrect-test-password\n')
        with self.assertRaisesRegex(SystemExit, 'password and hash do not match'):
            ACCESS.main()

    def test_mismatched_public_key_is_detected(self):
        (self.credentials / 'id_ed25519.pub').write_text('ssh-ed25519 incorrect-test-key\n')
        with self.assertRaisesRegex(SystemExit, 'SSH keys do not match'):
            ACCESS.main()


if __name__ == '__main__':
    unittest.main()
