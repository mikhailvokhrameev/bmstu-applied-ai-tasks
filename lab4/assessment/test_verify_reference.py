"""Regression checks for a false PASS on corrupted published reference metrics."""
import contextlib
import csv
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

if __package__:
    from . import verify_reference
else:
    import verify_reference


class PublishedReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='videocard-reference-test-')
        self.addCleanup(self.temporary.cleanup)
        self.fixtures = Path(self.temporary.name) / 'fixtures'
        shutil.copytree(verify_reference.HERE / 'fixtures', self.fixtures)

    def verify(self):
        with contextlib.redirect_stdout(io.StringIO()):
            verify_reference.main(self.fixtures)

    def test_published_reference_passes(self):
        self.verify()

    def test_wrong_m6_rejected_even_when_csv_agrees(self):
        path = self.fixtures / 'expected.json'
        data = json.loads(path.read_text())
        data['cases'][0]['M6'] = 999
        path.write_text(json.dumps(data))
        # Synchronize CSV, so the semantic M6 check must catch the corruption.
        with (self.fixtures / 'expected.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data['cases'][0]))
            writer.writeheader()
            writer.writerows(data['cases'])
        with self.assertRaisesRegex(AssertionError, 'M6'):
            self.verify()

    def test_csv_divergence_rejected(self):
        path = self.fixtures / 'expected.csv'
        with path.open(newline='') as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames
            rows = list(reader)
        rows[0]['M6'] = '999'
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(AssertionError, 'CSV differs from JSON.*M6'):
            self.verify()


if __name__ == '__main__':
    unittest.main(verbosity=2)
