from __future__ import annotations

import re

WORD_RE = re.compile(r"[A-Za-z0-9'’]+")
ROMAN_MARKER_RE = re.compile(r"\b([IVXLCDM]{1,10})(?=\s*[:.)])")

ROMAN_MAP = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
    "D": 500,
    "M": 1000,
}


def normalize_word(word: str) -> str:
    normalized = word.lower().replace("’", "'")
    normalized = normalized.replace("'", "")
    normalized = re.sub(r"[^a-z0-9]+", "", normalized)
    return normalized


def normalize_alignment_tokens(word: str) -> list[str]:
    normalized = normalize_word(word)
    if not normalized:
        return []

    if normalized.isdigit():
        numeric = int(normalized)
        if 0 <= numeric <= 100:
            return [normalize_word(token) for token in int_to_words(numeric).split() if token]

    return [normalized]


def roman_to_int(value: str) -> int | None:
    if not value:
        return None

    value = value.upper()
    if any(char not in ROMAN_MAP for char in value):
        return None

    total = 0
    previous = 0
    for char in reversed(value):
        current = ROMAN_MAP[char]
        if current < previous:
            total -= current
        else:
            total += current
            previous = current

    if total <= 0:
        return None

    return total


def int_to_words(value: int) -> str:
    ones = [
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
    ]
    tens = [
        "",
        "",
        "twenty",
        "thirty",
        "forty",
        "fifty",
        "sixty",
        "seventy",
        "eighty",
        "ninety",
    ]

    if value < 0:
        raise ValueError("value must be >= 0")
    if value < 20:
        return ones[value]
    if value < 100:
        tens_value, remainder = divmod(value, 10)
        return tens[tens_value] if remainder == 0 else f"{tens[tens_value]} {ones[remainder]}"
    if value == 100:
        return "one hundred"
    return str(value)
