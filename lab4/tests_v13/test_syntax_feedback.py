import json
import unittest

from lab4.optimizer_v13.bridge import cache_info, clear_caches
from lab4.optimizer_v13.proposals import ProposalError, parse_proposal


class SyntaxFeedbackTests(unittest.TestCase):
    def test_unknown_prefix_is_feedback_and_worker_accepts_next_proposal(self):
        clear_caches()
        try:
            axiom = 'SubClassOf(vc:Fresh vc:VideoCardModel)'
            invalid = dict(rationale='Проверка неизвестного префикса', add=[axiom], remove=[])
            with self.assertRaises(ProposalError) as caught:
                parse_proposal(json.dumps(invalid, ensure_ascii=False))
            diagnostic = caught.exception.diagnostic
            self.assertEqual(diagnostic['field'], 'add')
            self.assertEqual(diagnostic['index'], 0)
            self.assertEqual(diagnostic['axiom'], axiom)
            self.assertTrue(diagnostic['detail'])
            valid = dict(rationale='Проверка допустимого синтаксиса',
                         add=['FunctionalObjectProperty(:usesGPU)'], remove=[])
            parsed = parse_proposal(json.dumps(valid, ensure_ascii=False))
            self.assertEqual(parsed.add, valid['add'])
            self.assertEqual(cache_info()['worker_requests'], 2)
        finally:
            clear_caches()


if __name__ == '__main__':
    unittest.main()
