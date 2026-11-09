from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from lab4.optimizer import embedding_server as backend


class FakeEngine:
    repo = 'sentence-transformers/LaBSE'
    metadata = dict(version=backend.SERVER_VERSION, commit_sha='a' * 40,
                    weights=[dict(path='2_Dense/model.safetensors', sha256='b' * 64)],
                    snapshot_sha256='c' * 64, device='cpu', max_seq_length=256,
                    embedding_dimension=2)

    def __init__(self):
        self.calls = []

    def encode(self, texts, truncate=False):
        self.calls.append((texts, truncate))
        return [[1., 0.] for _ in texts]


class FakeSocket:
    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = io.BytesIO()

    def makefile(self, *args):
        return self.input

    def sendall(self, value):
        self.output.write(value)

    def settimeout(self, timeout):
        pass


class EmbeddingServerTests(unittest.TestCase):
    def request(self, engine, method, path, payload=None):
        body = b'' if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        header = f'{method} {path} HTTP/1.0\r\nContent-Length: {len(body)}\r\n\r\n'.encode()
        socket = FakeSocket(header + body)
        backend.make_handler(engine)(socket, ('127.0.0.1', 12345), SimpleNamespace())
        head, raw = socket.output.getvalue().split(b'\r\n\r\n', 1)
        return int(head.split()[1]), json.loads(raw)

    def snapshot_fixture(self, path):
        path.mkdir(parents=True, exist_ok=True)
        modules = [dict(idx=index, name=str(index), path=folder, type=kind)
                   for index, (folder, kind) in enumerate(zip(
                       ['', '1_Pooling', '2_Dense', '3_Normalize'], backend.PIPELINE))]
        (path / 'modules.json').write_text(json.dumps(modules))
        (path / 'config.json').write_text('{}')
        (path / 'model.safetensors').write_bytes(b'backbone weights')
        pool = path / '1_Pooling'
        pool.mkdir()
        (pool / 'config.json').write_text(json.dumps(dict(pooling_mode_cls_token=True,
                                                        pooling_mode_mean_tokens=False,
                                                        pooling_mode_max_tokens=False)))
        dense = path / '2_Dense'
        dense.mkdir()
        (dense / 'config.json').write_text('{}')
        (dense / 'model.safetensors').write_bytes(b'trained dense weights')
        (path / '3_Normalize').mkdir()
        return modules

    def record_fixture(self, path, modules, repo=FakeEngine.repo):
        record = dict(schema=1, repo=repo, commit_sha='a' * 40,
                      modules=modules, files=backend.assets(path))
        (path / backend.PROVENANCE).write_text(json.dumps(record))
        return record

    def test_http_matches_embed_protocol_for_string_and_batch_without_input_logs(self):
        engine = FakeEngine()
        log = io.StringIO()
        with redirect_stdout(log), redirect_stderr(log):
            status, result = self.request(engine, 'POST', '/api/embed',
                                           dict(model=engine.repo, input=['Русский текст', 'Другой текст'], truncate=False))
            self.assertEqual(status, 200)
            self.assertEqual(result['embeddings'], [[1., 0.], [1., 0.]])
            status, result = self.request(engine, 'POST', '/api/embed', dict(input='Один текст'))
            self.assertEqual(status, 200)
        self.assertEqual(engine.calls, [(['Русский текст', 'Другой текст'], False), (['Один текст'], False)])
        self.assertEqual(log.getvalue(), '')

    def test_http_exposes_pinned_commit_weights_and_actual_engine_configuration(self):
        engine = FakeEngine()
        for method, path, payload in [('GET', '/api/version', None),
                                      ('POST', '/api/show', dict(model=engine.repo))]:
            with self.subTest(path=path):
                status, result = self.request(engine, method, path, payload)
                self.assertEqual(status, 200)
                for key in ('commit_sha', 'weights', 'device', 'max_seq_length'):
                    self.assertEqual(result[key], engine.metadata[key])
        status, result = self.request(engine, 'GET', '/api/tags')
        self.assertEqual(result['models'][0]['name'], engine.repo)

    def test_http_rejects_bad_requests_and_does_not_echo_engine_exceptions(self):
        engine = FakeEngine()
        for payload in (dict(input=[]), dict(input=[7]), dict(input=''),
                        dict(input='text', model='different'), dict(input='text', truncate='false')):
            with self.subTest(payload=payload):
                self.assertEqual(self.request(engine, 'POST', '/api/embed', payload)[0], 400)
        engine.encode = Mock(side_effect=RuntimeError('PRIVATE INPUT MUST NOT BE LOGGED'))
        log = io.StringIO()
        with redirect_stdout(log), redirect_stderr(log):
            status, result = self.request(engine, 'POST', '/api/embed', dict(input='PRIVATE INPUT MUST NOT BE LOGGED'))
        self.assertEqual((status, result), (500, dict(error='embedding_engine_failure')))
        self.assertEqual(log.getvalue(), '')
        engine.encode = Mock(return_value=[[float('nan'), 0.]])
        self.assertEqual(self.request(engine, 'POST', '/api/embed', dict(input='text'))[0], 500)

    def test_pipeline_requires_cls_dense_and_normalize(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            modules = self.snapshot_fixture(path)
            self.assertEqual(backend.validate_pipeline(path), modules)
            (path / '2_Dense/model.safetensors').unlink()
            with self.assertRaisesRegex(ValueError, 'Dense'):
                backend.validate_pipeline(path)
            (path / '2_Dense/model.safetensors').write_bytes(b'dense')
            (path / '1_Pooling/config.json').write_text(json.dumps(dict(
                pooling_mode_cls_token=True, pooling_mode_mean_tokens=True)))
            with self.assertRaisesRegex(ValueError, 'CLS-only'):
                backend.validate_pipeline(path)
            modules[-1]['type'] = 'custom_remote_code.Evil'
            (path / 'modules.json').write_text(json.dumps(modules))
            with self.assertRaisesRegex(ValueError, 'complete labse'):
                backend.validate_pipeline(path)

    def e5_fixture(self, path):
        path.mkdir(parents=True, exist_ok=True)
        modules = [dict(idx=index, name=str(index), path=folder, type=kind)
                   for index, (folder, kind) in enumerate(zip(
                       ['', '1_Pooling', '2_Normalize'], backend.E5_PIPELINE))]
        (path / 'modules.json').write_text(json.dumps(modules))
        (path / 'config.json').write_text('{}')
        (path / 'model.safetensors').write_bytes(b'full E5 transformer weights')
        pool = path / '1_Pooling'
        pool.mkdir()
        (pool / 'config.json').write_text(json.dumps(dict(
            word_embedding_dimension=1024, pooling_mode_cls_token=False,
            pooling_mode_mean_tokens=True, pooling_mode_max_tokens=False,
            pooling_mode_mean_sqrt_len_tokens=False, pooling_mode_weightedmean_tokens=False,
            pooling_mode_lasttoken=False)))
        (path / '2_Normalize').mkdir()
        return modules

    def test_e5_profile_preserves_mean_normalize_without_inventing_dense(self):
        repo = 'intfloat/multilingual-e5-large-instruct'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            modules = self.e5_fixture(path)
            self.assertEqual(backend.validate_pipeline(path, repo), modules)
            self.assertFalse((path / '2_Dense').exists())
            with self.assertRaisesRegex(ValueError, 'complete labse'):
                backend.validate_pipeline(path, FakeEngine.repo)
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                backend.validate_pipeline(path, 'unknown/model')
            (path / '1_Pooling/config.json').write_text(json.dumps(dict(
                pooling_mode_cls_token=True, pooling_mode_mean_tokens=False)))
            with self.assertRaisesRegex(ValueError, 'mean-only'):
                backend.validate_pipeline(path, repo)

    def test_e5_engine_reports_actual_metadata_and_applies_no_second_instruction(self):
        repo = 'intfloat/multilingual-e5-large-instruct'
        with tempfile.TemporaryDirectory() as tmp, patch.object(backend, 'HF_ROOT', Path(tmp)):
            path, cache = Path(tmp) / 'snapshot', Path(tmp) / 'cache'
            modules = self.e5_fixture(path)
            self.record_fixture(path, modules, repo)
            model = SimpleNamespace(device='mps:0', max_seq_length=512, eval=Mock(),
                                    get_sentence_embedding_dimension=lambda: 1024,
                                    tokenizer=lambda texts, **kwargs: dict(input_ids=[[1, 2] for _ in texts]),
                                    encode=Mock(return_value=SimpleNamespace(tolist=lambda: [[1.] + [0.] * 1023])))
            constructor = Mock(return_value=model)
            with patch.dict('sys.modules', {'sentence_transformers': SimpleNamespace(SentenceTransformer=constructor)}), \
                    patch('importlib.metadata.version', return_value='fake-version'), patch.dict('os.environ', clear=False):
                engine = backend.SentenceTransformerEngine(repo, 'a' * 40, path, cache, 'mps')
                text = 'Instruct: Retrieve semantically similar text.\nQuery: Метка. Определение.'
                self.assertEqual(len(engine.encode([text])[0]), 1024)
            self.assertEqual(engine.metadata['pipeline_profile'], 'e5-mean')
            self.assertEqual(engine.metadata['device'], 'mps:0')
            self.assertEqual(engine.metadata['max_seq_length'], 512)
            self.assertEqual(engine.metadata['embedding_dimension'], 1024)
            self.assertEqual(len(engine.metadata['weights']), 1)
            self.assertEqual(model.encode.call_args.args[0], [text])
            constructor.assert_called_once_with(str(path.resolve()), device='mps', cache_folder=str(cache.resolve()),
                                                token=False, trust_remote_code=False, local_files_only=True)

    def test_e5_rejects_labse_dense_pipeline_and_custom_remote_modules(self):
        repo = 'intfloat/multilingual-e5-large-instruct'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            self.snapshot_fixture(path)
            with self.assertRaisesRegex(ValueError, 'complete e5'):
                backend.validate_pipeline(path, repo)
            modules = json.loads((path / 'modules.json').read_text())
            modules[0]['type'] = 'custom_remote.Transformer'
            (path / 'modules.json').write_text(json.dumps(modules))
            with self.assertRaisesRegex(ValueError, 'complete e5'):
                backend.validate_pipeline(path, repo)

    def test_offline_snapshot_requires_provenance_and_detects_dense_weight_changes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(backend, 'HF_ROOT', Path(tmp)):
            path, cache = Path(tmp) / 'snapshot', Path(tmp) / 'cache'
            modules = self.snapshot_fixture(path)
            with self.assertRaises(FileNotFoundError):
                backend.prepare_snapshot(FakeEngine.repo, 'a' * 40, path, cache)
            record = self.record_fixture(path, modules)
            actual_path, actual = backend.prepare_snapshot(FakeEngine.repo, 'a' * 40, path, cache)
            self.assertEqual((actual_path, actual), (path.resolve(), record))
            with self.assertRaisesRegex(ValueError, 'provenance'):
                backend.prepare_snapshot(FakeEngine.repo, 'b' * 40, path, cache)
            (path / '2_Dense/model.safetensors').write_bytes(b'changed dense weights')
            with self.assertRaisesRegex(ValueError, 'changed'):
                backend.prepare_snapshot(FakeEngine.repo, 'a' * 40, path, cache)

    def test_public_download_pins_commit_and_never_uses_token_or_remote_code(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(backend, 'HF_ROOT', Path(tmp)):
            path, cache = Path(tmp) / 'snapshot', Path(tmp) / 'cache'
            def download(**kwargs):
                self.snapshot_fixture(path)
                return str(path)
            hub = SimpleNamespace(HfApi=Mock(return_value=SimpleNamespace(model_info=Mock(
                return_value=SimpleNamespace(sha='a' * 40)))), snapshot_download=Mock(side_effect=download))
            with patch.dict('sys.modules', {'huggingface_hub': hub}):
                _, record = backend.prepare_snapshot(FakeEngine.repo, 'a' * 40, path, cache, download=True)
            self.assertFalse(hub.snapshot_download.call_args.kwargs['token'])
            self.assertEqual(hub.snapshot_download.call_args.kwargs['revision'], 'a' * 40)
            self.assertEqual(hub.snapshot_download.call_args.kwargs['allow_patterns'],
                             ['*.json', '*.safetensors', '*.model', '*.txt'])
            self.assertEqual(record['commit_sha'], 'a' * 40)
            self.assertTrue((path / backend.PROVENANCE).is_file())

    def test_engine_loads_local_full_pipeline_and_rejects_silent_truncation(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(backend, 'HF_ROOT', Path(tmp)):
            path, cache = Path(tmp) / 'snapshot', Path(tmp) / 'cache'
            modules = self.snapshot_fixture(path)
            self.record_fixture(path, modules)
            model = SimpleNamespace(device='cpu', max_seq_length=3, eval=Mock(),
                                    get_sentence_embedding_dimension=lambda: 2,
                                    tokenizer=lambda texts, **kwargs: dict(input_ids=[list(range(len(text))) for text in texts]),
                                    encode=Mock(return_value=SimpleNamespace(tolist=lambda: [[1., 0.]])))
            constructor = Mock(return_value=model)
            with patch.dict('sys.modules', {'sentence_transformers': SimpleNamespace(SentenceTransformer=constructor)}), \
                    patch('importlib.metadata.version', return_value='fake-version'), patch.dict('os.environ', clear=False):
                engine = backend.SentenceTransformerEngine(FakeEngine.repo, 'a' * 40, path, cache, 'cpu')
                self.assertEqual(engine.encode(['тест'], truncate=True), [[1., 0.]])
                with self.assertRaisesRegex(ValueError, 'truncation disabled'):
                    engine.encode(['тест'], truncate=False)
            constructor.assert_called_once_with(str(path.resolve()), device='cpu', cache_folder=str(cache.resolve()),
                                                token=False, trust_remote_code=False, local_files_only=True)
            self.assertEqual(engine.metadata['max_seq_length'], 3)
            self.assertEqual(engine.metadata['device'], 'cpu')
            self.assertEqual(len(engine.metadata['weights']), 2)
            self.assertFalse(model.encode.call_args.kwargs['normalize_embeddings'])

    def test_nonlocal_bind_and_unpinned_revision_are_rejected(self):
        with self.assertRaisesRegex(ValueError, '127.0.0.1'):
            backend.make_server(FakeEngine(), host='0.0.0.0')
        with self.assertRaisesRegex(ValueError, 'commit SHA'):
            backend.prepare_snapshot(FakeEngine.repo, 'main', 'irrelevant', 'irrelevant')


if __name__ == '__main__':
    unittest.main()
