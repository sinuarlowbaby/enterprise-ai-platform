"""
Base abstractions, block data models, and parser interface.
"""

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO


class BlockType(str, Enum):
    """Semantic block classification for layout elements."""
    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    CODE = "code"
    METADATA = "metadata"


@dataclass
class DocumentBlock:
    """
    Individual structured layout block extracted from a document.

    Attributes:
        text: Raw text content of the block.
        block_type: Semantic classification (heading, paragraph, table, etc.).
        page_number: 1-indexed page where the block appears.
        heading_level: Heading hierarchy level (1 for H1, 2 for H2, etc.), if applicable.
        section_path: Breadcrumb of parent headings leading to this block (e.g. ["1. Overview", "1.1 Goals"]).
        metadata: Block-specific layout attributes (bbox, font_size, row_count, etc.).
    """
    text: str
    block_type: BlockType = BlockType.PARAGRAPH
    page_number: int = 1
    heading_level: int | None = None
    section_path: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """
    Structured document representation resulting from parser extraction.

    Attributes:
        title: Extracted or inferred document title.
        source_filename: Name of the input document file.
        file_type: MIME type or extension identifier (e.g. "application/pdf").
        total_pages: Total count of pages in the document (1 for single-page formats).
        blocks: Sequenced list of layout blocks in reading order.
        metadata: Global document metadata (author, created_date, word_count, etc.).
    """
    source_filename: str
    file_type: str
    title: str | None = None
    total_pages: int = 1
    blocks: list[DocumentBlock] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Returns all block texts concatenated with double newlines."""
        return "\n\n".join(b.text for b in self.blocks if b.text.strip())

    @property
    def section_headings(self) -> list[str]:
        """Returns list of distinct heading texts in document sequence."""
        return [b.text for b in self.blocks if b.block_type in (BlockType.HEADING, BlockType.TITLE)]


class BaseParser(ABC):
    """Abstract interface for all layout-aware document parsers."""

    @abstractmethod
    def parse(
        self,
        content: str | Path | bytes | BinaryIO,
        filename: str = "document",
        **kwargs: Any,
    ) -> ParsedDocument:
        """
        Parses document content into structured DocumentBlocks with layout metadata.

        Args:
            content: File path, byte buffer, or file-like object.
            filename: Original file name used for tracking and type inference.
            **kwargs: Parser-specific arguments (e.g. font thresholds).

        Returns:
            ParsedDocument containing sequenced blocks, titles, and section paths.
        """
        pass

    async def aparse(
        self,
        content: str | Path | bytes | BinaryIO,
        filename: str = "document",
        **kwargs: Any,
    ) -> ParsedDocument:
        """Asynchronous execution of parse() offloaded to a worker thread."""
        return await asyncio.to_thread(self.parse, content, filename=filename, **kwargs)
