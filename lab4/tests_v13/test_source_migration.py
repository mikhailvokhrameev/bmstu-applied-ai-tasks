"""The resume migration admits one auditable parser fix, never a formula change."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab4.optimizer_v13 import journal
from lab4.optimizer_v13.metrics import BASELINE


class SourceMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lib = self.root / 'lib'
        self.lib.mkdir()
        self.before = {'journal.py': 'a' * 64,
                       'owl_bridge/ProposalSyntax.java': 'b' * 64,
                       'metrics.py': 'c' * 64,
                       'runtime.py': 'd' * 64,
                       'prompts/proposal.txt': 'e' * 64}
        self.after = dict(self.before, **{'journal.py': 'f' * 64,
                                        'owl_bridge/ProposalSyntax.java': '1' * 64})
        config = b'{}'
        self.meta = dict(schema=journal.SCHEMA, methodology=journal.METHODOLOGY,
                         phase='debug', source_sha256=self.before,
                         baseline_counts=journal.BASELINE_INVENTORY,
                         baseline_metrics=asdict(BASELINE),
                         core_sha256=journal.CORE_SHA256,
                         config_sha256=journal.digest(config),
                         environment=dict(libraries={}))
        self.raw = journal.encoded(self.meta)
        (self.root / 'metadata.json').write_bytes(self.raw)
        (self.root / 'metadata.sha256').write_text(journal.digest(self.raw))
        (self.root / 'config.yaml').write_bytes(config)
        self.proof = dict(metadata_sha256=journal.digest(self.raw),
                          config_sha256=self.meta['config_sha256'],
                          sources_before=self.before, sources_after=self.after,
                          changed=['journal.py', 'owl_bridge/ProposalSyntax.java'],
                          reason='Treat an undefined OWL prefix as a parse error; retain original metadata.')

    def save_proof(self, proof=None, valid_seal=True):
        proof = deepcopy(self.proof if proof is None else proof)
        proof.pop('payload_sha256', None)
        proof['payload_sha256'] = journal.digest(journal.encoded(proof)) if valid_seal else '0' * 64
        (self.root / 'source-migration.json').write_bytes(journal.encoded(proof))

    def resume(self, sources=None):
        with patch.object(journal, 'LIB', self.lib), \
             patch.object(journal, 'source_inventory', return_value=self.after if sources is None else sources), \
             patch.object(journal, '_run', return_value='resume accepted'):
            return journal.resume(self.root, runtime={})

    def test_parser_fix_is_accepted_without_rewriting_original_metadata(self):
        self.save_proof()
        original_proof = (self.root / 'source-migration.json').read_bytes()
        self.assertEqual(self.resume(), 'resume accepted')
        self.assertEqual((self.root / 'metadata.json').read_bytes(), self.raw)
        self.assertEqual((self.root / 'metadata.sha256').read_text(), journal.digest(self.raw))
        self.assertEqual((self.root / 'source-migration.json').read_bytes(), original_proof)

    def test_missing_or_corrupted_proof_rejects_the_migration(self):
        with self.assertRaisesRegex(journal.JournalError, 'invalid source migration'):
            self.resume()
        self.save_proof(valid_seal=False)
        with self.assertRaisesRegex(journal.JournalError, 'proof checksum'):
            self.resume()
        (self.root / 'source-migration.json').write_text('{')
        with self.assertRaisesRegex(journal.JournalError, 'invalid source migration'):
            self.resume()

    def test_all_pinned_proof_fields_and_exact_changed_list_are_required(self):
        cases = [
            ('metadata_sha256', '0' * 64),
            ('config_sha256', '0' * 64),
            ('sources_before', self.after),
            ('sources_after', self.before),
            ('changed', ['journal.py']),
            ('changed', ['journal.py', 'owl_bridge/ProposalSyntax.java', 'journal.py']),
            ('changed', ['journal.py', 'owl_bridge/ProposalSyntax.java', 'metrics.py']),
            ('reason', ''),
            ('reason', None),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                proof = deepcopy(self.proof)
                proof[key] = value
                self.save_proof(proof)
                with self.assertRaisesRegex(journal.JournalError, 'invalid source migration'):
                    self.resume()

    def test_formula_runtime_prompt_and_other_source_changes_cannot_be_authorized(self):
        for name in ('metrics.py', 'runtime.py', 'prompts/proposal.txt'):
            with self.subTest(name=name):
                sources = dict(self.after)
                sources[name] = '2' * 64
                proof = deepcopy(self.proof)
                proof['sources_after'] = sources
                proof['changed'].append(name)
                self.save_proof(proof)
                with self.assertRaisesRegex(journal.JournalError, 'migration scope'):
                    self.resume(sources)

    def test_added_removed_or_only_one_changed_source_is_rejected(self):
        cases = [dict(self.after, new_file='2' * 64),
                 {name: value for name, value in self.after.items() if name != 'metrics.py'},
                 dict(self.before, **{'journal.py': 'f' * 64})]
        for sources in cases:
            with self.subTest(sources=sources):
                proof = deepcopy(self.proof)
                proof['sources_after'] = sources
                proof['changed'] = sorted(name for name in set(self.before) | set(sources)
                                          if self.before.get(name) != sources.get(name))
                self.save_proof(proof)
                with self.assertRaisesRegex(journal.JournalError, 'implementation or prompt changed'):
                    self.resume(sources)

    def test_unchanged_source_inventory_still_needs_no_migration(self):
        self.assertEqual(self.resume(self.before), 'resume accepted')

    def test_valid_migration_does_not_bypass_config_baseline_or_library_guards(self):
        self.save_proof()
        (self.root / 'config.yaml').write_bytes(b'{"changed":true}')
        with self.assertRaisesRegex(journal.JournalError, 'configuration changed'):
            self.resume()
        (self.root / 'config.yaml').write_bytes(b'{}')
        with patch.object(journal, 'BASELINE_INVENTORY', dict(journal.BASELINE_INVENTORY, A=999)):
            with self.assertRaisesRegex(journal.JournalError, 'baseline changed'):
                self.resume()
        (self.lib / 'unexpected.jar').write_bytes(b'synthetic changed dependency')
        with self.assertRaisesRegex(journal.JournalError, 'incompatible libraries'):
            self.resume()


if __name__ == '__main__':
    unittest.main()
