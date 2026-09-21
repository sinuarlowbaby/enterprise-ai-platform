"""
Document Parsers Package.

Provides layout-aware parsers for PDF, DOCX, Markdown, and TXT with
automatic metadata and section hierarchy extraction.
"""

from knowledge.parsers.base import BaseParser, BlockType, DocumentBlock, ParsedDocument
from knowledge.parsers.docx import DocxParser
from knowledge.parsers.factory import ParserFactory
from knowledge.parsers.markdown import MarkdownParser
from knowledge.parsers.pdf import PyMuPDFParser
from knowledge.parsers.text import TextParser

__all__ = [
    "BaseParser",
    "BlockType",
    "DocumentBlock",
    "ParsedDocument",
    "PyMuPDFParser",
    "DocxParser",
    "MarkdownParser",
    "TextParser",
    "ParserFactory",
]
