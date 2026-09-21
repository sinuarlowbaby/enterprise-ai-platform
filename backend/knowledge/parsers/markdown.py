"""
Markdown Document Parser.

Parses Markdown text, frontmatter metadata, and heading hierarchies (#, ##, ###).
"""

from pathlib import Path
import re
from typing import Any, BinaryIO

from knowledge.parsers.base import BaseParser, BlockType, DocumentBlock, ParsedDocument


class MarkdownParser(BaseParser):
    """
    Parser for Markdown (.md, .markdown) files.

    Features:
    - Extracts YAML frontmatter metadata (title, author, tags).
    - Preserves ATX (#, ##, ###) heading hierarchies and breadcrumb section paths.
    - Captures fenced code blocks, lists, and tables intact.
    """

    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")

    def parse(
        self,
        content: str | Path | bytes | BinaryIO,
        filename: str = "document.md",
        **kwargs: Any,
    ) -> ParsedDocument:
        text = self._read_text(content)

        # 1. Extract YAML frontmatter if present
        frontmatter_meta, body_text = self._extract_frontmatter(text)

        title = frontmatter_meta.get("title")

        # 2. Parse blocks by line
        blocks: list[DocumentBlock] = []
        heading_stack: list[tuple[int, str]] = []

        lines = body_text.splitlines()
        current_block_lines: list[str] = []
        current_block_type: BlockType = BlockType.PARAGRAPH
        in_code_fence = False
        code_fence_lang = ""

        def flush_current_block():
            nonlocal current_block_lines, current_block_type
            if not current_block_lines:
                return

            block_str = "\n".join(current_block_lines).strip()
            if block_str:
                current_section_path = [h[1] for h in heading_stack]
                blocks.append(
                    DocumentBlock(
                        text=block_str,
                        block_type=current_block_type,
                        page_number=1,
                        heading_level=None,
                        section_path=list(current_section_path),
                        metadata={
                            "lang": code_fence_lang if current_block_type == BlockType.CODE else None,
                        },
                    )
                )
            current_block_lines = []
            current_block_type = BlockType.PARAGRAPH

        for line in lines:
            stripped = line.strip()

            # Handle code fence toggle
            if stripped.startswith("```"):
                if not in_code_fence:
                    flush_current_block()
                    in_code_fence = True
                    code_fence_lang = stripped[3:].strip()
                    current_block_type = BlockType.CODE
                    current_block_lines.append(line)
                    continue
                else:
                    current_block_lines.append(line)
                    in_code_fence = False
                    flush_current_block()
                    code_fence_lang = ""
                    continue

            if in_code_fence:
                current_block_lines.append(line)
                continue

            # Heading match
            heading_match = self.HEADING_PATTERN.match(line)
            if heading_match:
                flush_current_block()
                hashes, heading_text = heading_match.groups()
                level = len(hashes)
                clean_heading = heading_text.strip()

                if level == 1 and not title:
                    title = clean_heading

                # Update heading stack
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, clean_heading))

                current_section_path = [h[1] for h in heading_stack]
                blocks.append(
                    DocumentBlock(
                        text=clean_heading,
                        block_type=BlockType.TITLE if level == 1 and clean_heading == title else BlockType.HEADING,
                        page_number=1,
                        heading_level=level,
                        section_path=list(current_section_path),
                        metadata={"level": level},
                    )
                )
                continue

            # Blank line flushes paragraphs
            if not stripped:
                flush_current_block()
                continue

            # Table row
            if stripped.startswith("|") and stripped.endswith("|"):
                if current_block_type != BlockType.TABLE:
                    flush_current_block()
                    current_block_type = BlockType.TABLE
                current_block_lines.append(line)
                continue

            # List item
            if stripped.startswith(("- ", "* ", "+ ")) or (len(stripped) > 2 and stripped[:2].isdigit() and stripped[2] == "."):
                if current_block_type != BlockType.LIST:
                    flush_current_block()
                    current_block_type = BlockType.LIST
                current_block_lines.append(line)
                continue

            # Standard paragraph line
            if current_block_type not in (BlockType.PARAGRAPH,):
                flush_current_block()
            current_block_lines.append(line)

        flush_current_block()

        return ParsedDocument(
            source_filename=filename,
            file_type="text/markdown",
            title=title,
            total_pages=1,
            blocks=blocks,
            metadata=frontmatter_meta,
        )

    def _read_text(self, content: str | Path | bytes | BinaryIO) -> str:
        """Decodes raw input into string with UTF-8 fallback."""
        if isinstance(content, Path) or (isinstance(content, str) and "\n" not in content and Path(content).exists()):
            return Path(content).read_text(encoding="utf-8", errors="replace")
        elif isinstance(content, str):
            return content
        elif isinstance(content, bytes):
            return content.decode("utf-8", errors="replace")
        elif hasattr(content, "read"):
            data = content.read()
            if isinstance(data, bytes):
                return data.decode("utf-8", errors="replace")
            return str(data)
        raise ValueError(f"Unsupported content type for Markdown parser: {type(content)}")

    def _extract_frontmatter(self, text: str) -> tuple[dict[str, Any], str]:
        """Extracts simple key-value YAML frontmatter if present."""
        match = self.FRONTMATTER_PATTERN.match(text)
        if not match:
            return {}, text

        fm_text = match.group(1)
        body = text[match.end():]
        metadata: dict[str, Any] = {}

        for line in fm_text.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                k = key.strip()
                v = val.strip().strip("\"'")
                if k:
                    metadata[k] = v

        return metadata, body
