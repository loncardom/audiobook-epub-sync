from audiobook_epub_sync.text import normalize_alignment_tokens


def test_normalize_alignment_tokens_converts_small_numbers_to_words() -> None:
    assert normalize_alignment_tokens("14") == ["fourteen"]


def test_normalize_alignment_tokens_keeps_large_numbers_as_digits() -> None:
    assert normalize_alignment_tokens("2061") == ["2061"]
