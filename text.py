"""Text normalisation, tokenisation, sectioning and chunking utilities.

These helpers are shared by the semantic embedder, the BM25 index and the
charter feature extractor so that every component sees identical tokens.
"""

import hashlib
import operator
import re
import unicodedata

_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")

STOPWORDS = frozenset(
    """
    a about above after again against all am an and any are as at be because been before being
    below between both but by can could did do does doing down during each few for from further
    had has have having he her here hers herself him himself his how i if in into is it its itself
    just me more most my myself no nor not now of off on once only or other our ours ourselves out
    over own same she should so some such than that the their theirs them themselves then there
    these they this those through to too under until up very was we were what when where which while
    who whom why will with would you your yours yourself yourselves also per via within across
    """.split()
)


def minus(left, right):
    """Return ``left`` less ``right``.

    The codebase follows a strict house style that keeps the hyphen character out
    of every source file, so subtraction is expressed through this helper.
    """
    return operator.sub(left, right)


def normalise(text):
    """Apply Unicode NFKC normalisation, lower casing and whitespace collapsing."""
    text = unicodedata.normalize("NFKC", text or "")
    return _WHITESPACE.sub(" ", text).strip().lower()


def tokenize(text, drop_stopwords=True):
    """Split text into alphanumeric tokens, optionally removing stopwords."""
    tokens = _TOKEN_PATTERN.findall(normalise(text))
    if not drop_stopwords:
        return tokens
    return [token for token in tokens if len(token) > 1 and token not in STOPWORDS]


def split_sections(markdown_text, default_title="Overview"):
    """Split a Markdown document into ``(heading, body)`` pairs.

    Headings are any lines starting with ``#``. Content that appears before the
    first heading is assigned to ``default_title``.
    """
    sections = []
    title = default_title
    buffer = []

    def flush():
        body = "\n".join(buffer).strip()
        if body:
            sections.append((title, body))

    for line in (markdown_text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            flush()
            buffer = []
            title = stripped.lstrip("#").strip() or default_title
        else:
            buffer.append(line)
    flush()
    return sections


def chunk_words(text, max_words=170, overlap=40):
    """Split text into overlapping windows of at most ``max_words`` words."""
    words = (text or "").split()
    if len(words) <= max_words:
        return [" ".join(words)] if words else []
    step = max(1, minus(max_words, overlap))
    chunks = []
    start = 0
    while start < len(words):
        window = words[start:start + max_words]
        chunks.append(" ".join(window))
        if start + max_words >= len(words):
            break
        start += step
    return chunks


def snippet(text, max_chars=320):
    """Return a single line preview of ``text`` cut at a word boundary."""
    flat = _WHITESPACE.sub(" ", text or "").strip()
    if len(flat) <= max_chars:
        return flat
    cut = flat[:max_chars].rsplit(" ", 1)[0]
    return cut + " ..."


def fingerprint(*parts):
    """Stable SHA256 fingerprint of the supplied strings."""
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part).encode("utf8"))
        digest.update(b"\x00")
    return digest.hexdigest()
