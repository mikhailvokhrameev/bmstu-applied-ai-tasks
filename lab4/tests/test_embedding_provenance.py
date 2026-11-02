import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab4.optimizer.prepare import verify_sentence_transformer


class EmbeddingProvenanceTests(unittest.TestCase):
    model = 'sentence-transformers/LaBSE'
    revision = 'a' * 40

    def fixture(self, root):
        snapshot = root / '.local-runtime/hf/snapshots/labse'
        snapshot.mkdir(parents=True)
        payloads = {'model.safetensors': b'backbone weights',
                    '2_Dense/model.safetensors': b'trained dense weights',
                    'modules.json': b'[]', 'config.json': b'{}'}
        files = []
        for relative, content in sorted(payloads.items()):
            path = snapshot / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            files.append(dict(path=relative, sha256=hashlib.sha256(content).hexdigest(), bytes=len(content)))
        fingerprint = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        show = dict(model=self.model, backend='sentence-transformers', commit_sha=self.revision,
                    snapshot=str(snapshot), files=files,
                    weights=[item for item in files if item['path'].endswith('.safetensors')],
                    snapshot_sha256=fingerprint, device='cpu', max_seq_length=256,
                    packages=dict(torch='fake', sentence_transformers='fake'))
        self.record(snapshot, show)
        return snapshot, show

    def record(self, snapshot, show, **overrides):
        record = dict(schema=1, repo=self.model, commit_sha=self.revision, files=show['files'])
        record.update(overrides)
        (snapshot / '.embedding-snapshot.json').write_text(json.dumps(record))

    def test_valid_snapshot_is_hashed_independently_and_returns_complete_manifest_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            snapshot, show = self.fixture(root)
            with patch('lab4.optimizer.prepare.ROOT', root):
                verified = verify_sentence_transformer(show, self.model, self.revision)
        self.assertEqual(verified['revision'], self.revision)
        self.assertEqual(verified['sha256'], show['snapshot_sha256'])
        self.assertEqual(verified['sha256_kind'], 'complete inference asset manifest')
        self.assertEqual(verified['snapshot'], str(snapshot))
        self.assertEqual(verified['weights'], show['weights'])
        self.assertEqual((verified['device'], verified['max_seq_length']), ('cpu', 256))

    def test_backbone_and_dense_weight_changes_are_detected_even_with_unchanged_size(self):
        for name in ('model.safetensors', '2_Dense/model.safetensors'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                snapshot, show = self.fixture(root)
                weight = snapshot / name
                weight.write_bytes(b'x' * weight.stat().st_size)
                with patch('lab4.optimizer.prepare.ROOT', root), \
                        self.assertRaisesRegex(ValueError, 'checksum/size'):
                    verify_sentence_transformer(show, self.model, self.revision)

    def test_revision_model_backend_and_sidecar_identity_mismatches_are_rejected(self):
        changes = [('api-model', dict(model='different/model'), {}, self.revision),
                   ('api-backend', dict(backend='ollama'), {}, self.revision),
                   ('api-commit', dict(commit_sha='b' * 40), {}, self.revision),
                   ('unfixed-commit', {}, {}, 'main'),
                   ('record-model', {}, dict(repo='different/model'), self.revision),
                   ('record-commit', {}, dict(commit_sha='b' * 40), self.revision)]
        for name, api_change, record_change, revision in changes:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                snapshot, show = self.fixture(root)
                self.record(snapshot, show, **record_change)
                with patch('lab4.optimizer.prepare.ROOT', root), self.assertRaises(ValueError):
                    verify_sentence_transformer({**show, **api_change}, self.model, revision)

    def test_traversal_absolute_paths_and_symlink_escape_are_rejected(self):
        for kind in ('traversal', 'absolute', 'symlink'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                snapshot, show = self.fixture(root)
                outside = snapshot.parent / 'outside.safetensors'
                outside.write_bytes(b'outside weights')
                if kind == 'traversal':
                    relative = '../outside.safetensors'
                elif kind == 'absolute':
                    relative = str(outside)
                else:
                    (snapshot / 'link.safetensors').symlink_to(outside)
                    relative = 'link.safetensors'
                item = dict(path=relative, bytes=outside.stat().st_size,
                            sha256=hashlib.sha256(outside.read_bytes()).hexdigest())
                show['files'].append(item)
                show['weights'].append(item)
                self.record(snapshot, show)
                with patch('lab4.optimizer.prepare.ROOT', root), \
                        self.assertRaisesRegex(ValueError, 'asset (path|inventory)'):
                    verify_sentence_transformer(show, self.model, self.revision)

    def test_undeclared_asset_and_duplicate_manifest_entry_are_rejected(self):
        for kind in ('undeclared', 'duplicate'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                snapshot, show = self.fixture(root)
                if kind == 'undeclared':
                    (snapshot / 'extra_active_weight.safetensors').write_bytes(b'undeclared weights')
                else:
                    show['files'].append(copy.deepcopy(show['files'][0]))
                    self.record(snapshot, show)
                with patch('lab4.optimizer.prepare.ROOT', root), \
                        self.assertRaisesRegex(ValueError, 'actual asset inventory mismatch'):
                    verify_sentence_transformer(show, self.model, self.revision)

    def test_download_cache_metadata_does_not_change_inference_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            snapshot, show = self.fixture(root)
            cache = snapshot / '.cache/huggingface/download'
            cache.mkdir(parents=True)
            (cache / 'modules.json.metadata').write_text('download progress metadata')
            with patch('lab4.optimizer.prepare.ROOT', root):
                verified = verify_sentence_transformer(show, self.model, self.revision)
            self.assertEqual(verified['sha256'], show['snapshot_sha256'])

    def test_snapshot_outside_project_hf_storage_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            _, show = self.fixture(root)
            with patch('lab4.optimizer.prepare.ROOT', root / 'other-project'), \
                    self.assertRaisesRegex(ValueError, 'inside project'):
                verify_sentence_transformer(show, self.model, self.revision)

    def test_api_inventory_weights_and_fingerprint_cannot_disagree_with_snapshot(self):
        changes = [('files', lambda show: show['files'][:-1]),
                   ('weights', lambda show: show['weights'][:1]),
                   ('snapshot_sha256', lambda show: '0' * 64)]
        for field, change in changes:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                _, show = self.fixture(root)
                show[field] = change(copy.deepcopy(show))
                with patch('lab4.optimizer.prepare.ROOT', root), self.assertRaisesRegex(ValueError, 'mismatch'):
                    verify_sentence_transformer(show, self.model, self.revision)

    def test_forged_server_and_sidecar_hashes_cannot_replace_real_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            snapshot, show = self.fixture(root)
            show['files'][0]['sha256'] = '0' * 64
            self.record(snapshot, show)
            with patch('lab4.optimizer.prepare.ROOT', root), \
                    self.assertRaisesRegex(ValueError, 'checksum/size'):
                verify_sentence_transformer(show, self.model, self.revision)


if __name__ == '__main__':
    unittest.main()
