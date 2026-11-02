"""Verify portable working-material archives with synthetic source trees."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from lab4.scripts.package import ROOT, REQUIRED, build_package, verify_archive


class PackageTests(unittest.TestCase):
    def source_tree(self, root):
        for name in REQUIRED:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture\n')
        harness = root / 'lab2/tests/harness/src/Main.java'
        harness.parent.mkdir(parents=True, exist_ok=True)
        harness.write_text('class Main {}\n')
        # A real self-contained CLI source verifies the unpacked layout.
        script = root / 'lab4/scripts/package.py'
        script.parent.mkdir(parents=True)
        script.write_bytes((ROOT / 'lab4/scripts/package.py').read_bytes())
        return root

    def test_extractable_archive_preserves_sources_and_excludes_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.source_tree(Path(directory) / 'source')
            for name in ('lab4/optimizer/__pycache__/x.pyc', 'lab4/models/blob.bin',
                         'lab4/cache/data', 'lab4/optimizer/.env',
                         'lab2/tests/results/run.log', 'lab2/tests/harness/lib/owl.jar'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('excluded')
            output = Path(directory) / 'working.zip'
            result = build_package(root, output)
            self.assertTrue(result['missing_specification'])
            self.assertEqual(verify_archive(output), result)
            unpacked = Path(directory) / 'unpacked'
            with zipfile.ZipFile(output) as archive:
                self.assertTrue(set(REQUIRED) <= set(archive.namelist()))
                self.assertFalse(any('excluded' == archive.read(name).decode() for name in archive.namelist()))
                archive.extractall(unpacked)
            for name in REQUIRED:
                self.assertEqual((unpacked / name).read_bytes(), (root / name).read_bytes())
            proc = subprocess.run([sys.executable, str(unpacked / 'lab4/scripts/package.py'), '--help'],
                                  text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('--output', proc.stdout)
            original = output.read_bytes()
            with self.assertRaises(FileExistsError):build_package(root, output)
            self.assertEqual(output.read_bytes(), original)

    def test_rejects_symlink_and_missing_required_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.source_tree(Path(directory) / 'source')
            link = root / 'lab4/outside.py'
            link.symlink_to(Path(directory) / 'outside.py')
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                build_package(root, Path(directory) / 'unsafe.zip')
            link.unlink()
            (root / 'lab2/ontology/videocard.owl').unlink()
            with self.assertRaisesRegex(ValueError, 'Missing required source'):
                build_package(root, Path(directory) / 'missing.zip')

    def test_verifier_rejects_traversal_and_changed_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            unsafe = Path(directory) / 'unsafe.zip'
            with zipfile.ZipFile(unsafe, 'w') as archive:
                archive.writestr('../outside', 'x')
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                verify_archive(unsafe)
            corrupt = Path(directory) / 'corrupt.zip'
            manifest = dict(sha256={'README.md': '0' * 64})
            with zipfile.ZipFile(corrupt, 'w') as archive:
                archive.writestr('README.md', 'changed')
                archive.writestr('WORKING_MATERIALS.json', json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'checksum'):
                verify_archive(corrupt)


if __name__ == '__main__':
    unittest.main()
