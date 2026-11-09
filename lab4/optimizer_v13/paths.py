"""Source-controlled paths for repository and canonical delivery layouts."""
import json
from pathlib import Path


OPTIMIZER = Path(__file__).resolve().parent
_delivery_root = OPTIMIZER.parent
_marker = _delivery_root / 'DELIVERY_MANIFEST.json'
IS_DELIVERY = _marker.is_file()
if IS_DELIVERY:
    if json.loads(_marker.read_text(encoding='utf-8')).get('layout') != 'videocard-nn-delivery-v1':
        raise ValueError('Unsupported ontology delivery layout')
    ROOT = _delivery_root
    TESTS = ROOT / 'tests'
    ASSESSMENT = ROOT / 'docs/assessment'
    DOCS = ROOT / 'docs'
    SCRIPTS = ROOT / 'scripts'
    SPEC = DOCS / 'tz_videokarta_lr4_nn_v1.3.docx'
    REQUIREMENTS = ROOT / 'requirements.txt'
    CORE = ROOT / 'ontology/1.0.0/videocard.owl'
    HARNESS = TESTS / 'harness'
    EXPECTED = TESTS / 'expected.json'
else:
    ROOT = OPTIMIZER.parents[1]
    TESTS = ROOT / 'lab4/tests_v13'
    ASSESSMENT = ROOT / 'lab4/assessment'
    DOCS = ROOT / 'lab4/docs'
    SCRIPTS = ROOT / 'lab4/scripts'
    SPEC = ROOT / 'lab4/tz_videokarta_lr4_nn_v1.3.docx'
    REQUIREMENTS = ROOT / 'lab4/requirements.txt'
    CORE = ROOT / 'lab2/ontology/videocard.owl'
    HARNESS = ROOT / 'lab2/tests/harness'
    EXPECTED = ROOT / 'lab2/tests/expected.json'
LIB = HARNESS / 'lib'
