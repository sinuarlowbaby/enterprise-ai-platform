"""
Parser Factory and Document Ingestion Dispatcher.
"""

from pathlib import Path
from typing import Any, BinaryIO

from knowledge.parsers.base import BaseParser, ParsedDocument
from knowledge.parsers.docx import DocxParser
from knowledge.parsers.markdown import MarkdownParser
from knowledge.parsers.pdf import PyMuPDFParser
from knowledge.parsers.text import TextParser


class ParserFactory:
    """
    Factory resolving the appropriate parser for a given file format or MIME type.
    """

    _EXTENSION_MAP: dict[str, type[BaseParser]] = {
        ".pdf": PyMuPDFParser,
        ".docx": DocxParser,
        ".doc": DocxParser,
        ".md": MarkdownParser,
        ".markdown": MarkdownParser,
        ".txt": TextParser,
        ".log": TextParser,
        ".json": TextParser,
        ".yaml": TextParser,
        ".yml": TextParser,
    }

    _MIME_MAP: dict[str, type[BaseParser]] = {
        "application/pdf": PyMuPDFParser,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxParser,
        "application/msword": DocxParser,
        "text/markdown": MarkdownParser,
        "text/x-markdown": MarkdownParser,
        "text/plain": TextParser,
    }

    @classmethod
    def get_parser(cls, filename_or_mime: str) -> BaseParser:
        """
        Instantiates and returns the matching BaseParser.

        Args:
            filename_or_mime: File path, file name, or MIME type string.

        Returns:
            Configured parser instance.
        """
        clean_input = filename_or_mime.lower().strip()

        # Check MIME type exact match
        if clean_input in cls._MIME_MAP:
            return cls._MIME_MAP[clean_input]()

        # Check file extension
        ext = Path(clean_input).suffix.lower()
        if ext in cls._EXTENSION_MAP:
            return cls._EXTENSION_MAP[ext]()

        # Default fallback to TextParser
        return TextParser()

    @classmethod
    def parse(
        cls,
        content: str | Path | bytes | BinaryIO,
        filename: str = "document",
        mime_type: str | None = None,
        **kwargs: Any,
    ) -> ParsedDocument:
        """
        Dispatches parsing of the provided document content using the resolved parser.
        """
        key = mime_type or filename
        parser = cls.get_parser(key)
        return parser.parse(content, filename=filename, **kwargs)

    @classmethod
    async def aparse(
        cls,
        content: str | Path | bytes | BinaryIO,
        filename: str = "document",
        mime_type: str | None = None,
        **kwargs: Any,
    ) -> ParsedDocument:
        """Asynchronous dispatch of document parsing."""
        key = mime_type or filename
        parser = cls.get_parser(key)
        return await parser.aparse(content, filename=filename, **kwargs)
