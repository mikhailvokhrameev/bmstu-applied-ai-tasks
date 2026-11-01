"""Испытания BinaryMutation по плану ТР-ВМ-001 (ТЗ, разд. 6)."""

import contextlib
import io
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import binary_mutation as bm  # noqa: E402

# Таблица 1 ТЗ: (исходная строка, позиция мутации, ожидаемый результат).
CONTROL_EXAMPLES = [
    ("00000", 2, "01000"),
    ("11111", 3, "11011"),
    ("101010", 6, "101011"),
    ("0", 1, "1"),
    ("1001", 2, "1101"),
]


def differing_positions(a: str, b: str) -> list[int]:
    """Номера (с единицы) позиций, в которых строки различаются."""
    return [i + 1 for i, (x, y) in enumerate(zip(a, b)) if x != y]


class ControlExamplesTest(unittest.TestCase):
    """Критерии прохождения (п. 6.6): результат совпадает с ожидаемым,
    длина не изменена, различается ровно один разряд — выбранный."""

    def test_five_control_examples(self):
        for bits, position, expected in CONTROL_EXAMPLES:
            with self.subTest(bits=bits, position=position):
                got_position, result = bm.mutate(bits, position)
                self.assertEqual(got_position, position)
                self.assertEqual(result, expected)
                self.assertEqual(len(result), len(bits))
                self.assertEqual(differing_positions(bits, result), [position])


class InvalidInputTest(unittest.TestCase):
    """Некорректный вход: понятная ошибка, мутация не выполняется (п. 4.2)."""

    def test_invalid_string(self):
        for bits in ("", "10a1", "102", "1 0", "abc"):
            with self.subTest(bits=bits):
                with self.assertRaises(ValueError):
                    bm.mutate(bits, 1)

    def test_position_out_of_range(self):
        for position in (0, -1, 6):
            with self.subTest(position=position):
                with self.assertRaises(ValueError):
                    bm.mutate("00000", position)


class RandomPositionTest(unittest.TestCase):
    def test_random_position_in_range_and_single_flip(self):
        rng = random.Random(0)
        bits = "101010"
        for _ in range(200):
            position, result = bm.mutate(bits, rng=rng)
            self.assertTrue(1 <= position <= len(bits))
            self.assertEqual(differing_positions(bits, result), [position])

    def test_seed_is_reproducible(self):
        first = bm.mutate("1100110011", rng=random.Random(42))
        second = bm.mutate("1100110011", rng=random.Random(42))
        self.assertEqual(first, second)


class CliTest(unittest.TestCase):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = bm.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_output_contains_source_position_and_result(self):
        code, out, _ = self.run_cli(["1001", "--position", "2"])
        self.assertEqual(code, 0)
        self.assertEqual(
            out.splitlines(),
            ["Исходная строка: 1001", "Позиция мутации: 2", "Строка после мутации: 1101"],
        )

    def test_error_message_and_no_result(self):
        code, out, err = self.run_cli(["10a1", "--position", "2"])
        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("Ошибка", err)


if __name__ == "__main__":
    unittest.main()
