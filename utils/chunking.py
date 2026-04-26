from pathlib import Path
from typing import List, Dict
import re

# ── Pre-compiled regex patterns ────────────────────────────────────────────────
# Compiling once at module level avoids re-compiling the same pattern on every
# line of every file, which was the primary cause of slow chunking.

# Cleanup pass
_RE_IMG      = re.compile(r"<!--\s*image\s*-->", re.IGNORECASE)
_RE_FORMULA  = re.compile(r"<!--\s*formula-not-decoded\s*-->", re.IGNORECASE)
_RE_COMMENT  = re.compile(r"<!--.*?-->", re.DOTALL)
_RE_NL4      = re.compile(r"\n{4,}")
_RE_SPACES   = re.compile(r"[ \t]+")
_RE_CAMEL    = re.compile(r"([a-z])([A-Z])")

# Word-segmentation guards (applied per line)
_RE_HEADER_LINE  = re.compile(r"^#{1,6}\s+")
_RE_LIST_LINE    = re.compile(r"^[\*\-\+]\s+|^(\d+\.)\s+|^>\s+")
_RE_TABLE_SEP    = re.compile(r"^\|[\-\:\|\s]+\|\s*$")
_RE_WORD_PFX     = re.compile(r"^[\W_]*")
_RE_WORD_SFX     = re.compile(r"[\W_]*$")

# Section parser
_RE_HEADER       = re.compile(r"^(#{1,6})\s+(.*)")
_RE_LIST_START   = re.compile(r"^[\*\-\+]\s+|^(\d+\.)\s+")
_RE_LIST_NESTED  = re.compile(r"^[\t ]*[\*\-\+]\s+|^[\t ]*(\d+\.)\s+|^[\t ]{2,}")
_RE_ORDERED      = re.compile(r"^\d+\.\s+")

# Force-split
_RE_SENTENCE     = re.compile(r"(?<=[.!?])\s+")

# wordsegment is loaded lazily on first use to avoid a ~2 s startup penalty
# on every pipeline run (the corpus is only needed for long CamelCase Latin tokens).
_ws_loaded = False

# Files larger than this (in characters) skip the word-by-word CamelCase
# segmentation loop.  On large English books (1–2 MB) that loop would call
# _RE_WORD_PFX / _RE_WORD_SFX on every word across 50 000+ lines; at negligible
# quality loss we just skip it — _RE_CAMEL already splits the common cases.
_MAX_WS_CHARS = 300_000  # ~300 KB


def _ensure_ws() -> None:
    """Load wordsegment corpus once, on first actual need."""
    global _ws_loaded
    if not _ws_loaded:
        from wordsegment import load as _ws_load
        _ws_load()
        _ws_loaded = True


def _segment(word: str) -> list[str]:
    """Thin wrapper that ensures the corpus is loaded before calling segment()."""
    _ensure_ws()
    from wordsegment import segment
    return segment(word)


def adaptive_chunk_markdown(
    file_path: Path = None,
    text: str = None,
    min_size: int = 300,
    max_size: int = 1500,   # wider than Vilo (1200) — Arabic PDFs are denser
    overlap: int = 150,      # more overlap — food-safety regulations span sentences
) -> List[Dict]:
    """
    Semantically chunks a Markdown document into structured pieces.

    Understands: headers, code blocks, tables, lists, blockquotes, paragraphs.
    Each chunk carries a metadata dict with section context, size, source file,
    and content type — ready to be enriched with cluster/file metadata upstream.

    Args:
        file_path: Path to a .md file (reads the file if text is not provided)
        text:      Raw markdown string (takes priority over file_path)
        min_size:  Minimum characters before a new section triggers a split
        max_size:  Target maximum chunk size in characters
        overlap:   Characters of previous chunk included at the start of next chunk

    Returns:
        List of {"text": str, "metadata": dict} dicts
    """
    if text is None:
        if file_path is None:
            return [{"text": "", "metadata": {"error": "No file_path or text provided"}}]
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return [{"text": "", "metadata": {"error": str(e), "source_file": file_path.name}}]

    source_name = file_path.name if file_path else "Unknown"

    if not text.strip():
        return [{"text": "", "metadata": {"warning": "Empty file", "source_file": source_name}}]

    # ── Clean markup noise (uses pre-compiled patterns) ───────────────────────
    text = _RE_IMG.sub("", text)
    text = _RE_FORMULA.sub("[Formula]", text)
    text = _RE_COMMENT.sub("", text)

    html_entities = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&#39;": "'", "&nbsp;": " ", "&apos;": "'",
    }
    for entity, char in html_entities.items():
        text = text.replace(entity, char)

    text = _RE_NL4.sub("\n\n\n", text)
    text = _RE_SPACES.sub(" ", text)
    text = _RE_CAMEL.sub(r"\1 \2", text)

    # ── Word-segmentation for CamelCase runs (Latin text only) ───────────────
    # Skipped for large files (> _MAX_WS_CHARS) because the per-word regex loop
    # is O(n_lines × n_words) and becomes prohibitively slow on multi-MB books.
    # The _RE_CAMEL pre-pass above already handles the common camelCase patterns.
    if len(text) <= _MAX_WS_CHARS:
        _lines = []
        for line in text.split("\n"):
            s = line.strip()

            # Skip structural markdown lines — no CamelCase processing needed.
            if (
                s.startswith(("```", "|"))
                or _RE_HEADER_LINE.match(s)
                or _RE_LIST_LINE.match(s)
                or _RE_TABLE_SEP.match(s)
            ):
                _lines.append(line)
                continue

            # Fast-path: if the line contains no ASCII alphabetic characters
            # (e.g. pure Arabic, numbers, punctuation) there is nothing to segment.
            if not any(ch.isascii() and ch.isalpha() for ch in line):
                _lines.append(line)
                continue

            words = []
            for word in line.split():
                prefix = _RE_WORD_PFX.match(word).group()
                suffix = _RE_WORD_SFX.search(word).group()
                core = word[len(prefix): len(word) - len(suffix) if suffix else None]

                if len(core) > 12 and core.isalpha() and not core.isupper():
                    segs = _segment(core.lower())   # lazy-loads corpus on first call
                    if len(segs) > 1 and all(len(w) > 1 for w in segs):
                        words.append(prefix + " ".join(segs) + suffix)
                        continue
                words.append(word)
            _lines.append(" ".join(words))

        text = "\n".join(_lines)
    # else: large file — skip segmentation, _RE_CAMEL already handled camelCase

    lines = text.split("\n")

    # ── Parse into semantic sections ──────────────────────────────────────────
    sections = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Headers
        header_match = _RE_HEADER.match(stripped)
        if header_match:
            level = len(header_match.group(1))
            sections.append(("header", line, i, i + 1, level))
            i += 1
            continue

        # Code blocks
        if stripped.startswith("```"):
            start = i
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                i += 1
            i += 1
            content = "\n".join(lines[start:i])
            sections.append(("code", content, start, i, 0))
            continue

        # Tables
        if stripped.startswith("|") and stripped.endswith("|"):
            start = i
            i += 1
            if i < len(lines) and _RE_TABLE_SEP.match(lines[i].strip()):
                i += 1
            while (
                i < len(lines)
                and lines[i].strip().startswith("|")
                and not _RE_TABLE_SEP.match(lines[i].strip())
            ):
                i += 1
            content = "\n".join(lines[start:i])
            sections.append(("table", content, start, i, 0))
            continue

        # Lists
        if _RE_LIST_START.match(stripped):
            start = i
            while i < len(lines):
                curr = lines[i].strip()
                if not curr or not _RE_LIST_NESTED.match(curr):
                    break
                i += 1
            content = "\n".join(lines[start:i])
            sections.append(("list", content, start, i, 0))
            continue

        # Blockquotes
        if stripped.startswith(">"):
            start = i
            while i < len(lines) and lines[i].strip().startswith(">"):
                i += 1
            content = "\n".join(lines[start:i])
            sections.append(("quote", content, start, i, 0))
            continue

        # Paragraphs
        start = i
        para_lines = []
        while i < len(lines):
            curr = lines[i].strip()
            if (
                not curr
                or curr.startswith(("```", "|"))
                or _RE_HEADER_LINE.match(curr)
                or curr.startswith(">")
                or _RE_LIST_START.match(curr)
                or _RE_ORDERED.match(curr)
            ):
                break
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            content = "\n".join(para_lines)
            sections.append(("paragraph", content, start, i, 0))

    # ── Assemble chunks with overlap ──────────────────────────────────────────
    chunks = []
    current_text = ""
    current_sections = []
    header_stack = []

    for sec_type, content, line_start, line_end, level in sections:
        content_size = len(content)
        current_size = len(current_text)

        if sec_type == "header":
            header_text = content.lstrip("# ").strip()
            header_stack = [h for h in header_stack if h[1] < level]
            header_stack.append((header_text, level))

        should_split = (
            (sec_type == "header" and current_size >= min_size)
            or (sec_type in ("code", "table") and content_size > min_size and current_size >= min_size)
            or (current_size + content_size + 50 > max_size and current_size > 0)
        )

        if should_split and current_text.strip():
            header_path = " > ".join(h[0] for h in header_stack) if header_stack else "Root"
            chunks.append({
                "text": current_text.strip(),
                "metadata": {
                    "header": header_path,
                    "sections": current_sections.copy(),
                    "size": len(current_text.strip()),
                    "source_file": source_name,
                    "chunk_type": "mixed" if len(set(current_sections)) > 1 else current_sections[0],
                },
            })
            current_text = (current_text[-overlap:] + "\n\n" + content) if overlap > 0 and len(current_text) > overlap else content
            current_sections = [sec_type]
        else:
            current_text = (current_text + "\n\n" + content) if current_text else content
            if sec_type not in current_sections:
                current_sections.append(sec_type)

    # Final chunk
    if current_text.strip():
        header_path = " > ".join(h[0] for h in header_stack) if header_stack else "Root"
        chunks.append({
            "text": current_text.strip(),
            "metadata": {
                "header": header_path,
                "sections": current_sections,
                "size": len(current_text.strip()),
                "source_file": source_name,
                "chunk_type": "mixed" if len(set(current_sections)) > 1 else current_sections[0],
            },
        })

    # Fallback: document too small to split
    if not chunks and text.strip():
        chunks.append({
            "text": text.strip(),
            "metadata": {
                "header": "Root",
                "sections": ["full_document"],
                "size": len(text.strip()),
                "source_file": source_name,
                "note": "Single chunk — document too small to split",
            },
        })

    # ── Force-split oversized chunks at sentence boundaries ──────────────────
    final_chunks = []
    for chunk in chunks:
        if chunk["metadata"]["size"] > max_size * 1.8:
            sentences = _RE_SENTENCE.split(chunk["text"])
            sub = ""
            for sent in sentences:
                if len(sub) + len(sent) > max_size and sub:
                    final_chunks.append({
                        "text": sub.strip(),
                        "metadata": {**chunk["metadata"], "size": len(sub.strip()), "note": "force_split_large"},
                    })
                    sub = sent
                else:
                    sub = (sub + " " + sent) if sub else sent
            if sub.strip():
                final_chunks.append({
                    "text": sub.strip(),
                    "metadata": {**chunk["metadata"], "size": len(sub.strip())},
                })
        else:
            final_chunks.append(chunk)

    return final_chunks
