from __future__ import annotations

from pathlib import Path

from .models import EpubWord
from .text import ROMAN_MARKER_RE, WORD_RE, int_to_words, normalize_word, roman_to_int


def _css_path(element) -> str:
    parts: list[str] = []
    current = element
    while current is not None and getattr(current, "name", None) not in ("[document]", None):
        name = current.name
        parent = current.parent
        if parent is None or getattr(parent, "find_all", None) is None:
            parts.append(name)
            break

        siblings = [sibling for sibling in parent.find_all(name, recursive=False)]
        if len(siblings) > 1:
            index = siblings.index(current) + 1
            parts.append(f"{name}:nth-of-type({index})")
        else:
            parts.append(name)
        current = parent

    return " > ".join(reversed(parts))


def _token_matches(text: str) -> list[tuple[int, int, str, str]]:
    matches: list[tuple[int, int, str, str]] = []
    for match in ROMAN_MARKER_RE.finditer(text):
        matches.append((match.start(1), match.end(1), "roman", match.group(1)))
    for match in WORD_RE.finditer(text):
        matches.append((match.start(), match.end(), "word", match.group(0)))
    matches.sort(key=lambda item: (item[0], 0 if item[2] == "roman" else 1, -(item[1] - item[0])))
    return matches


def _align_tokens(kind: str, word: str) -> list[str]:
    if kind == "roman":
        numeric = roman_to_int(word)
        if numeric is not None:
            return [normalize_word(token) for token in int_to_words(numeric).split() if token]

    normalized = normalize_word(word)
    return [normalized] if normalized else []


def extract_epub_words(epub_path: Path) -> list[EpubWord]:
    try:
        from bs4 import BeautifulSoup, NavigableString
        from ebooklib import epub
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Missing EPUB extraction dependencies: {exc}") from exc

    if not epub_path.exists():
        raise FileNotFoundError(f"EPUB file not found: {epub_path}")

    book = epub.read_epub(str(epub_path))
    spine = [item_id for item_id, _linear in book.spine]

    words: list[EpubWord] = []
    word_index = 0

    for spine_index, item_id in enumerate(spine):
        item = book.get_item_with_id(item_id)
        if item is None:
            continue

        href = item.file_name
        content = item.get_content()
        soup = BeautifulSoup(content, "lxml") if content else None
        if soup is None:
            continue

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        root = soup.body if soup.body is not None else soup
        element_offsets: dict[tuple[int, str, str], int] = {}

        for node in root.descendants:
            if not isinstance(node, NavigableString):
                continue

            text = str(node)
            if not text.strip():
                continue

            parent = node.parent
            path = _css_path(parent)
            key = (spine_index, href, path)
            offset = element_offsets.get(key, 0)

            last_end = -1
            for start, end, kind, raw_word in _token_matches(text):
                if start < last_end:
                    continue
                last_end = end

                cfi = f"spine={spine_index};href={href};path={path};w={offset}"
                words.append(
                    EpubWord(
                        index=word_index,
                        word=raw_word,
                        spine=spine_index,
                        href=href,
                        path=path,
                        cfi=cfi,
                        align_tokens=_align_tokens(kind, raw_word),
                    )
                )
                word_index += 1
                offset += 1

            element_offsets[key] = offset

    return words
