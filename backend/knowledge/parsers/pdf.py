"""
PyMuPDF Layout-Aware PDF Parser.

Extracts text blocks, font metrics, bounding boxes, section hierarchies,
and page numbers using fitz (PyMuPDF).
"""

from collections import Counter
import io
from pathlib import Path
from typing import Any, BinaryIO
import fitz  # PyMuPDF

from knowledge.parsers.base import BaseParser, BlockType, DocumentBlock, ParsedDocument


class PyMuPDFParser(BaseParser):
    """
    Layout-aware PDF parser utilizing PyMuPDF (fitz).

    Features:
    - Analyzes font size distribution to infer body text vs. headings.
    - Discovers title from PDF metadata or largest font on page 1.
    - Maintains a section hierarchy breadcrumb (e.g. ['Chapter 1', 'Section 1.2']).
    - Captures 1-indexed page numbers and block bounding boxes.
    """

    def __init__(
        self,
        h1_font_delta: float = 3.5,
        h2_font_delta: float = 1.8,
        min_heading_chars: int = 3,
        max_heading_chars: int = 160,
    ) -> None:
        self.h1_font_delta = h1_font_delta
        self.h2_font_delta = h2_font_delta
        self.min_heading_chars = min_heading_chars
        self.max_heading_chars = max_heading_chars

    def parse(
        self,
        content: str | Path | bytes | BinaryIO,
        filename: str = "document.pdf",
        **kwargs: Any,
    ) -> ParsedDocument:
        doc = self._open_document(content)

        try:
            total_pages = len(doc)
            raw_metadata = doc.metadata or {}

            # Phase 1: Scan span font sizes across pages to compute body font size
            body_font_size = self._compute_body_font_size(doc)

            # Phase 2: Extract layout blocks with font & position inspection
            blocks: list[DocumentBlock] = []
            heading_stack: list[tuple[int, str]] = []  # [(level, heading_text)]
            discovered_title: str | None = raw_metadata.get("title")

            if discovered_title and not discovered_title.strip():
                discovered_title = None

            for page_idx in range(total_pages):
                page = doc[page_idx]
                page_num = page_idx + 1
                page_dict = page.get_text("dict", flags=fitz.TEXTFLAGS_SEARCH)

                # Blocks in page dict: blocks -> lines -> spans
                for b_idx, block in enumerate(page_dict.get("blocks", [])):
                    if block.get("type") != 0:  # 0 is text block, 1 is image
                        continue

                    block_text, avg_font_size, is_bold, bbox = self._extract_block_info(block)
                    clean_text = block_text.strip()
                    if not clean_text:
                        continue

                    # Determine block type and heading level
                    block_type, heading_level = self._classify_block(
                        clean_text,
                        avg_font_size,
                        is_bold,
                        body_font_size,
                        page_num,
                    )

                    # Title detection fallback from page 1 largest header
                    if page_num == 1 and not discovered_title and block_type in (BlockType.TITLE, BlockType.HEADING):
                        if avg_font_size > (body_font_size + self.h1_font_delta):
                            discovered_title = clean_text

                    # Update heading stack
                    if block_type in (BlockType.TITLE, BlockType.HEADING):
                        lvl = heading_level or 1
                        # Pop headings at same or deeper level
                        while heading_stack and heading_stack[-1][0] >= lvl:
                            heading_stack.pop()
                        heading_stack.append((lvl, clean_text))

                    current_section_path = [h[1] for h in heading_stack]

                    doc_block = DocumentBlock(
                        text=clean_text,
                        block_type=block_type,
                        page_number=page_num,
                        heading_level=heading_level,
                        section_path=list(current_section_path),
                        metadata={
                            "bbox": bbox,
                            "font_size": round(avg_font_size, 2),
                            "is_bold": is_bold,
                            "block_index": b_idx,
                        },
                    )
                    blocks.append(doc_block)

            return ParsedDocument(
                source_filename=filename,
                file_type="application/pdf",
                title=discovered_title,
                total_pages=total_pages,
                blocks=blocks,
                metadata={
                    "author": raw_metadata.get("author"),
                    "subject": raw_metadata.get("subject"),
                    "producer": raw_metadata.get("producer"),
                    "creation_date": raw_metadata.get("creationDate"),
                    "estimated_body_font_size": body_font_size,
                },
            )
        finally:
            doc.close()

    def _open_document(self, content: str | Path | bytes | BinaryIO) -> fitz.Document:
        """Opens a PyMuPDF Document from filepath, bytes, or file-like stream."""
        if isinstance(content, (str, Path)):
            return fitz.open(str(content))
        elif isinstance(content, bytes):
            return fitz.open(stream=content, filetype="pdf")
        elif hasattr(content, "read"):
            stream_bytes = content.read()
            return fitz.open(stream=stream_bytes, filetype="pdf")
        raise ValueError(f"Unsupported content type for PDF parser: {type(content)}")

    def _compute_body_font_size(self, doc: fitz.Document) -> float:
        """Scans sampled spans to find the statistical mode (most frequent) font size."""
        font_counter: Counter[float] = Counter()
        # Inspect up to first 10 pages for font size distribution
        sample_pages = min(len(doc), 10)
        for i in range(sample_pages):
            page_dict = doc[i].get_text("dict")
            for block in page_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if len(text) > 3:
                                size = round(span.get("size", 10.0), 1)
                                font_counter[size] += len(text)

        if font_counter:
            return font_counter.most_common(1)[0][0]
        return 10.0  # standard fallback font size

    def _extract_block_info(self, block: dict[str, Any]) -> tuple[str, float, bool, list[float]]:
        """Extracts text, average font size, bold flag, and bbox from a block dictionary."""
        lines = block.get("lines", [])
        line_texts: list[str] = []
        total_font_size = 0.0
        span_count = 0
        is_bold = False

        for line in lines:
            line_str = "".join(span.get("text", "") for span in line.get("spans", ""))
            line_texts.append(line_str)
            for span in line.get("spans", []):
                span_text = span.get("text", "").strip()
                if span_text:
                    total_font_size += span.get("size", 10.0) * len(span_text)
                    span_count += len(span_text)
                    # Check bold flags (bit 4 or 'bold' in font name)
                    flags = span.get("flags", 0)
                    font_name = span.get("font", "").lower()
                    if (flags & 2 ** 4) or "bold" in font_name or "black" in font_name:
                        is_bold = True

        avg_font_size = (total_font_size / span_count) if span_count > 0 else 10.0
        full_text = "\n".join(line_texts)
        bbox = list(block.get("bbox", [0.0, 0.0, 0.0, 0.0]))
        return full_text, avg_font_size, is_bold, bbox

    def _classify_block(
        self,
        text: str,
        font_size: float,
        is_bold: bool,
        body_font_size: float,
        page_num: int,
    ) -> tuple[BlockType, int | None]:
        """Classifies text block based on font size differentials and length."""
        text_len = len(text)
        is_short = text_len <= self.max_heading_chars and "\n\n" not in text

        # H1 or Title
        if font_size >= (body_font_size + self.h1_font_delta) and is_short:
            if page_num == 1 and font_size >= (body_font_size + self.h1_font_delta * 1.5):
                return BlockType.TITLE, 1
            return BlockType.HEADING, 1

        # H2
        if font_size >= (body_font_size + self.h2_font_delta) and is_short:
            return BlockType.HEADING, 2

        # H3: Bold short text with slight elevation or body size
        if is_bold and is_short and font_size >= (body_font_size - 0.5):
            return BlockType.HEADING, 3

        # List item
        if text.startswith(("- ", "• ", "* ", "– ")) or (len(text) > 3 and text[:2].isdigit() and text[2:4] in (". ", ") ")):
            return BlockType.LIST, None

        return BlockType.PARAGRAPH, None
