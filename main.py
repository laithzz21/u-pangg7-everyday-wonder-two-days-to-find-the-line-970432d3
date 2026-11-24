#!/usr/bin/env python3
"""Entry for make.fun bounty: everyday wonder — two days to find the line.

One sentence, at most 200 characters: a small everyday moment made strange
and new — a lift door opens on the wrong floor, and a familiar hallway
suddenly feels like somewhere never seen before. Prints the entry to stdout
and writes a copy to ``/output/entry.txt`` (or ``$MAKEFUN_OUTPUT`` when set).
Python 3.13, stdlib only, deterministic.
"""

import hashlib
import os
import sys

ENTRY = (
    "The lift door opened on the wrong floor, and for one second the "
    "hallway I had walked a hundred times felt like somewhere I had "
    "never been."
)

MAX_CHARS = 200
MIN_CHARS = 1
MIN_WORDS = 8
MAX_WORDS = 40
OUTPUT_FILENAME = "entry.txt"


def normalize_text(text: str) -> str:
    """Collapse runs of whitespace to a single space and strip the ends."""
    collapsed = " ".join(text.split())
    return collapsed


def count_words(text: str) -> int:
    """Number of whitespace-separated words in the entry."""
    return len(text.split())


def count_sentences(text: str) -> int:
    """Count sentence-ending punctuation marks in the entry."""
    return sum(1 for ch in text if ch in ".!?")


def sha256_hex(data: str) -> str:
    """SHA-256 of the UTF-8 encoding of ``data``, as a hex string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def has_repeated_word(text: str) -> bool:
    """True if any word appears twice in a row (a copy-paste slip)."""
    words = [w.strip(".,!?").lower() for w in text.split()]
    return any(a == b for a, b in zip(words, words[1:]))


def validate(text: str) -> None:
    """The entry must be a single sentence of 1-200 characters, with no
    stray whitespace or control characters that would break the count.
    """
    if not MIN_CHARS <= len(text) <= MAX_CHARS:
        raise ValueError(
            f"entry must be {MIN_CHARS}-{MAX_CHARS} characters, got {len(text)}"
        )
    if "\n" in text or "\r" in text or "\t" in text:
        raise ValueError("entry must be a single line with no tabs")
    if text != text.strip():
        raise ValueError("entry must not start or end with whitespace")
    if any(ord(ch) < 0x20 for ch in text):
        raise ValueError("entry must not contain control characters")
    if any(ord(ch) > 0x7E for ch in text):
        raise ValueError("entry must be plain printable ASCII only")
    if "  " in text:
        raise ValueError("entry must not contain double spaces")
    if count_sentences(text) != 1 or not text.endswith("."):
        raise ValueError("entry must be exactly one sentence ending with a period")
    words = count_words(text)
    if not MIN_WORDS <= words <= MAX_WORDS:
        raise ValueError(f"entry must be {MIN_WORDS}-{MAX_WORDS} words, got {words}")
    if has_repeated_word(text):
        raise ValueError("entry must not repeat a word twice in a row")
    if not text[0].isupper():
        raise ValueError("entry must start with a capital letter")


def describe(text: str) -> dict:
    """Small report used for the stderr summary line."""
    return {
        "chars": len(text),
        "words": count_words(text),
        "sentences": count_sentences(text),
        "sha256": sha256_hex(text + "\n"),
    }


def resolve_out_dir() -> str:
    """Prefer $MAKEFUN_OUTPUT, then /output, falling back to ./output."""
    requested = os.environ.get("MAKEFUN_OUTPUT") or "/output"
    try:
        os.makedirs(requested, exist_ok=True)
        probe = os.path.join(requested, ".write_probe")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return requested
    except OSError:
        fallback = os.path.join(os.getcwd(), "output")
        os.makedirs(fallback, exist_ok=True)
        return fallback


def write_entry(out_dir: str, text: str) -> str:
    """Write ``text`` to ``entry.txt`` in ``out_dir`` and verify it.

    The file is read back and compared byte for byte, including its
    SHA-256, before the run is allowed to succeed. Returns the path.
    """
    path = os.path.join(out_dir, OUTPUT_FILENAME)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    with open(path, "r", encoding="utf-8") as f:
        written = f.read()
    if written != text:
        raise RuntimeError("verification failed: written entry does not match")
    if os.path.getsize(path) != len(text.encode("utf-8")):
        raise RuntimeError("verification failed: written file size mismatch")
    if sha256_hex(written) != sha256_hex(text):
        raise RuntimeError("verification failed: written entry hash mismatch")
    return path


def main() -> int:
    text = normalize_text(ENTRY)
    if text != ENTRY:
        print("warning: normalisation changed the entry", file=sys.stderr)
    validate(text)
    # The stdout print is the entry; it must succeed before anything else.
    print(text, flush=True)
    stats = describe(text)
    print(
        f"entry ok: {stats['chars']} chars, {stats['words']} words, "
        f"sha256 {stats['sha256'][:16]}...",
        file=sys.stderr,
    )
    try:
        out_dir = resolve_out_dir()
        path = write_entry(out_dir, text)
        print(f"wrote {path}", file=sys.stderr)
    except OSError as exc:
        # File output is a convenience copy only; the printed entry is
        # already out, so a failed write must not fail the run.
        print(f"warning: could not write entry.txt: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
