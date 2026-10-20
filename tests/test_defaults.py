"""Verify the generated password, account preservation and file permissions."""
import importlib.util
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_defaults', ROOT / 'scripts/prepare_defaults.py')
defaults = importlib.util.module_from_spec(spec)
spec.loader.exec_module(defaults)


class DefaultsTests(unittest.TestCase):
    def test_root_password_hash_and_existing_system_accounts(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = pathlib.Path(temporary) / 'upstream-shadow'
            target = pathlib.Path(temporary) / 'files/etc/shadow'
            source.write_text('root:::0:99999:7:::\nnobody:*:0:0:99999:7:::\n')
            defaults.prepare_shadow(source, target)
            lines = target.read_text().splitlines()
            digest = lines[0].split(':')[1]
            verification = subprocess.run(['openssl', 'passwd', '-6', '-salt', digest.split('$')[2], '-stdin'],
                                          input='password\n', text=True, capture_output=True, check=True)
            self.assertEqual(digest, verification.stdout.strip())
            self.assertEqual(lines[1], 'nobody:*:0:0:99999:7:::')
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_missing_root_does_not_produce_an_unusable_shadow(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = pathlib.Path(temporary) / 'shadow'
            source.write_text('nobody:*:0:0:99999:7:::\n')
            target = pathlib.Path(temporary) / 'out'
            with self.assertRaises(ValueError):
                defaults.prepare_shadow(source, target)
            self.assertFalse(target.exists())
