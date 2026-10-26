"""BinaryMutation: программа, реализующая простую бинарную мутацию.

Бинарная мутация здесь — инверсия одного выбранного бита двоичной строки
(0 -> 1, 1 -> 0); остальные разряды не меняются (ТЗ, разд. 1).
Позиции нумеруются слева направо, начиная с единицы (ТЗ, п. 6.8).
"""

import argparse
import random
import sys


def validate_bits(bits: str) -> None:
    """Проверяет входную строку: не пуста и состоит только из символов 0 и 1."""
    if bits == "":
        raise ValueError("пустая строка: длина должна быть не менее одного символа")
    bad = sorted({ch for ch in bits if ch not in "01"})
    if bad:
        raise ValueError(
            "строка должна состоять только из символов 0 и 1, "
            f"найдены недопустимые символы: {' '.join(repr(ch) for ch in bad)}"
        )


def validate_position(position: int, length: int) -> None:
    """Проверяет, что номер позиции лежит в диапазоне от 1 до длины строки."""
    if not 1 <= position <= length:
        raise ValueError(
            f"позиция {position} вне допустимого диапазона от 1 до {length}"
        )


def flip_bit(bit: str) -> str:
    """Инверсия одного бита: '0' -> '1', '1' -> '0'."""
    return "1" if bit == "0" else "0"


def mutate(
    bits: str, position: int | None = None, rng: random.Random | None = None
) -> tuple[int, str]:
    """Выполняет простую бинарную мутацию.

    Возвращает пару (номер мутированного разряда, строка после мутации).
    Если position не задан, позиция выбирается случайно из диапазона 1..len(bits);
    для воспроизводимости можно передать генератор rng с фиксированным seed.
    Некорректный вход приводит к ValueError, мутация при этом не выполняется.
    """
    validate_bits(bits)
    if position is None:
        position = (rng or random.Random()).randint(1, len(bits))
    validate_position(position, len(bits))

    index = position - 1  # позиции нумеруются с единицы, индексы строки — с нуля
    # Инвертируется только бит в выбранной позиции, срезы слева и справа сохраняются.
    mutated = bits[:index] + flip_bit(bits[index]) + bits[index + 1 :]
    return position, mutated


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Простая бинарная мутация: инверсия одного бита двоичной строки."
    )
    parser.add_argument(
        "bits",
        nargs="?",
        help="двоичная строка из символов 0 и 1 (если не указана, запрашивается с клавиатуры)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--position",
        type=int,
        help="фиксированная позиция мутации (1..длина строки) для тестового режима",
    )
    group.add_argument(
        "--seed",
        type=int,
        help="начальное значение генератора для воспроизводимого случайного выбора позиции",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Получение входной строки: из аргумента командной строки или с клавиатуры.
    bits = args.bits if args.bits is not None else input("Введите двоичную строку: ")
    bits = bits.strip()

    rng = random.Random(args.seed) if args.seed is not None else None
    try:
        position, mutated = mutate(bits, args.position, rng)
    except ValueError as error:
        # При ошибке входных данных выводится сообщение, мутация не выполняется.
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    print(f"Исходная строка: {bits}")
    print(f"Позиция мутации: {position}")
    print(f"Строка после мутации: {mutated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
