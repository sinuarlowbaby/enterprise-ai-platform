"""
Plain Text Document Parser.

Robust plain text parser with multi-encoding detection and section heuristics.
"""

from pathlib import Path
import re
from typing import Any, BinaryIO

from knowledge.parsers.base import BaseParser, BlockType, DocumentBlock, ParsedDocument


class TextParser(BaseParser):
    """
    Parser for Plain Text (.txt) files.

    Features:
    - Multi-encoding resilience (utf-8, utf-8-sig, cp1252, latin-1).
    - Heuristic heading and title detection for uppercase or numbered section headers.
    - Preserves paragraph separations and list structures.
    """

    HEADING_REGEX = re.compile(
        r"^(?:(?:[0-9]{1,2}(?:\.[0-9]{1,2})*|[A-Z]\.)\s+([^\n]+)|([A-Z0-9\s,\-\:]{4,80}))$"
    )

    def parse(
        self,
        content: str | Path | bytes | BinaryIO,
        filename: str = "document.txt",
        **kwargs: Any,
    ) -> ParsedDocument:
        text = self._read_text_with_encoding_fallback(content)

        blocks: list[DocumentBlock] = []
        heading_stack: list[str] = []
        title: str | None = None

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        for idx, para in enumerate(paragraphs):
            lines = para.splitlines()
            first_line = lines[0].strip()

            # First paragraph heuristic for document title
            if idx == 0 and len(first_line) < 100 and not first_line.endswith("."):
                title = first_line
                blocks.append(
                    DocumentBlock(
                        text=first_line,
                        block_type=BlockType.TITLE,
                        page_number=1,
                        heading_level=1,
                        section_path=[first_line],
                    )
                )
                heading_stack = [first_line]
                # If there are remaining lines in the first paragraph, add them as paragraph
                rest = "\n".join(lines[1:]).strip()
                if rest:
                    blocks.append(
                        DocumentBlock(
                            text=rest,
                            block_type=BlockType.PARAGRAPH,
                            page_number=1,
                            section_path=list(heading_stack),
                        )
                    )
                continue

            # Check if first line of paragraph is a heading
            match = self.HEADING_REGEX.match(first_line)
            is_all_caps = first_line.isupper() and len(first_line) > 3 and not first_line.endswith(".")

            if (match or is_all_caps) and len(first_line) <= 100:
                heading_text = first_line
                heading_stack = [heading_text]
                blocks.append(
                    DocumentBlock(
                        text=heading_text,
                        block_type=BlockType.HEADING,
                        page_number=1,
                        heading_level=2,
                        section_path=list(heading_stack),
                    )
                )
                rest = "\n".join(lines[1:]).strip()
                if rest:
                    blocks.append(
                        DocumentBlock(
                            text=rest,
                            block_type=BlockType.PARAGRAPH,
                            page_number=1,
                            section_path=list(heading_stack),
                        )
                    )
                continue

            # Check for lists
            if first_line.startswith(("- ", "* ", "• ")) or (len(first_line) > 2 and first_line[:2].isdigit() and first_line[2] in (".", ")")):
                block_type = BlockType.LIST
            else:
                block_type = BlockType.PARAGRAPH

            blocks.append(
                DocumentBlock(
                    text=para,
                    block_type=block_type,
                    page_number=1,
                    section_path=list(heading_stack),
                )
            )

        return ParsedDocument(
            source_filename=filename,
            file_type="text/plain",
            title=title,
            total_pages=1,
            blocks=blocks,
            metadata={
                "line_count": len(text.splitlines()),
                "char_count": len(text),
            },
        )

    def _read_text_with_encoding_fallback(self, content: str | Path | bytes | BinaryIO) -> str:
        """Attempts reading text with common encodings in order."""
        raw_bytes: bytes

        if isinstance(content, Path) or (isinstance(content, str) and "\n" not in content and Path(content).exists()):
            raw_bytes = Path(content).read_bytes()
        elif isinstance(content, str):
            return content
        elif isinstance(content, bytes):
            raw_bytes = content
        elif hasattr(content, "read"):
            data = content.read()
            raw_bytes = data if isinstance(data, bytes) else str(data).encode("utf-8")
        else:
            raise ValueError(f"Unsupported content type for Text parser: {type(content)}")

        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        for enc in encodings:
            try:
                return raw_bytes.decode(enc)
            except UnicodeDecodeError:
                continue

        return raw_bytes.decode("utf-8", errors="replace")
