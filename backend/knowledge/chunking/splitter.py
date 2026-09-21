"""
Token-Aware Recursive Character Splitter with Mandatory Metadata Attachment.

Splits parsed document blocks or raw text into token-bounded chunks (512-1024 tokens)
with 10-20% overlap, tracking section breadcrumbs, page ranges, and token metrics.
"""

from dataclasses import dataclass, field
import uuid
from typing import Any
import tiktoken

from knowledge.parsers.base import BlockType, DocumentBlock, ParsedDocument


@dataclass
class Chunk:
    """
    Standardized knowledge chunk ready for vectorization and database insertion.

    Attributes:
        content: The text content of the chunk.
        chunk_index: 0-indexed position within the document.
        metadata: Enriched mandatory and auxiliary metadata.
        tenant_id: Optional tenant isolation identifier.
        document_id: Optional parent document identifier.
        embedding: Optional dense vector embedding.
    """
    content: str
    chunk_index: int
    metadata: dict[str, Any]
    tenant_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializes chunk to dictionary matching DocumentChunk table schema."""
        return {
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "document_id": str(self.document_id) if self.document_id else None,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata,
        }


class RecursiveTokenSplitter:
    """
    Token-aware recursive text splitter.

    Parameters:
        chunk_size_tokens: Maximum target tokens per chunk (default: 768, recommended: 512-1024).
        chunk_overlap_tokens: Number of overlapping tokens between consecutive chunks (default: 128, ~16%).
        encoding_name: tiktoken tokenizer encoding (default: 'cl100k_base').
        separators: Priority list of string separators for recursive decomposition.
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]

    def __init__(
        self,
        chunk_size_tokens: int = 768,
        chunk_overlap_tokens: int = 128,
        encoding_name: str = "cl100k_base",
        separators: list[str] | None = None,
    ) -> None:
        if chunk_overlap_tokens >= chunk_size_tokens:
            raise ValueError("chunk_overlap_tokens must be strictly smaller than chunk_size_tokens")

        self.chunk_size_tokens = chunk_size_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens
        self.separators = separators or self.DEFAULT_SEPARATORS

        try:
            self.tokenizer = tiktoken.get_encoding(encoding_name)
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Computes exact token count using tiktoken."""
        if not text:
            return 0
        return len(self.tokenizer.encode(text, disallowed_special=()))

    def split_document(
        self,
        parsed_doc: ParsedDocument,
        tenant_id: uuid.UUID | str | None = None,
        document_id: uuid.UUID | str | None = None,
    ) -> list[Chunk]:
        """
        Splits a ParsedDocument into token-bounded Chunks preserving section and page metadata.

        Args:
            parsed_doc: Parsed document containing structured layout blocks.
            tenant_id: Tenant UUID for multi-tenant isolation.
            document_id: Parent document UUID.

        Returns:
            List of Chunk objects with mandatory metadata attached.
        """
        t_uuid = uuid.UUID(str(tenant_id)) if tenant_id else None
        d_uuid = uuid.UUID(str(document_id)) if document_id else None

        chunks: list[Chunk] = []
        chunk_index = 0

        # Accumulated state for current chunk
        current_texts: list[str] = []
        current_tokens = 0
        current_pages: set[int] = set()
        current_sections: list[str] = []

        for block in parsed_doc.blocks:
            block_text = block.text.strip()
            if not block_text:
                continue

            block_tokens = self.count_tokens(block_text)

            # Case 1: Single block exceeds max chunk size -> split recursively
            if block_tokens > self.chunk_size_tokens:
                # Flush existing buffer first
                if current_texts:
                    chunk = self._build_chunk(
                        texts=current_texts,
                        chunk_index=chunk_index,
                        parsed_doc=parsed_doc,
                        pages=current_pages,
                        sections=current_sections,
                        tenant_id=t_uuid,
                        document_id=d_uuid,
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_texts = []
                    current_tokens = 0
                    current_pages = set()
                    current_sections = []

                sub_fragments = self._split_text_recursively(block_text, self.chunk_size_tokens)
                for frag in sub_fragments:
                    frag_tokens = self.count_tokens(frag)
                    frag_pages = {block.page_number}
                    frag_sections = block.section_path or ([block_text] if block.block_type == BlockType.HEADING else [])

                    chunk = self._build_chunk(
                        texts=[frag],
                        chunk_index=chunk_index,
                        parsed_doc=parsed_doc,
                        pages=frag_pages,
                        sections=frag_sections,
                        tenant_id=t_uuid,
                        document_id=d_uuid,
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                continue

            # Case 2: Adding this block exceeds chunk_size_tokens -> emit chunk with overlap
            if current_tokens + block_tokens > self.chunk_size_tokens and current_texts:
                chunk = self._build_chunk(
                    texts=current_texts,
                    chunk_index=chunk_index,
                    parsed_doc=parsed_doc,
                    pages=current_pages,
                    sections=current_sections,
                    tenant_id=t_uuid,
                    document_id=d_uuid,
                )
                chunks.append(chunk)
                chunk_index += 1

                # Calculate overlap: retain trailing text blocks that fit within chunk_overlap_tokens
                overlap_texts, overlap_pages, overlap_tokens = self._calculate_overlap(
                    current_texts, current_pages
                )

                current_texts = overlap_texts
                current_tokens = overlap_tokens
                current_pages = overlap_pages

            # Append current block to buffer
            current_texts.append(block_text)
            current_tokens += block_tokens
            current_pages.add(block.page_number)
            if block.section_path:
                current_sections = list(block.section_path)
            elif block.block_type == BlockType.HEADING:
                current_sections = [block_text]

        # Flush trailing chunk
        if current_texts:
            chunk = self._build_chunk(
                texts=current_texts,
                chunk_index=chunk_index,
                parsed_doc=parsed_doc,
                pages=current_pages,
                sections=current_sections,
                tenant_id=t_uuid,
                document_id=d_uuid,
            )
            chunks.append(chunk)

        return chunks

    def split_text(
        self,
        text: str,
        filename: str = "raw_text",
        title: str | None = None,
        tenant_id: uuid.UUID | str | None = None,
        document_id: uuid.UUID | str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Convenience method to split raw text with mandatory metadata attachment."""
        t_uuid = uuid.UUID(str(tenant_id)) if tenant_id else None
        d_uuid = uuid.UUID(str(document_id)) if document_id else None

        fragments = self._split_text_recursively(text, self.chunk_size_tokens)
        chunks: list[Chunk] = []

        for idx, frag in enumerate(fragments):
            token_count = self.count_tokens(frag)
            metadata = {
                "tenant_id": str(t_uuid) if t_uuid else None,
                "document_id": str(d_uuid) if d_uuid else None,
                "filename": filename,
                "chunk_index": idx,
                "title": title,
                "section_headings": [],
                "page_numbers": [1],
                "token_count": token_count,
                "char_count": len(frag),
            }
            if extra_metadata:
                metadata.update(extra_metadata)

            chunk = Chunk(
                content=frag,
                chunk_index=idx,
                metadata=metadata,
                tenant_id=t_uuid,
                document_id=d_uuid,
            )
            chunks.append(chunk)

        return chunks

    def _split_text_recursively(self, text: str, max_tokens: int) -> list[str]:
        """Recursively splits text using the hierarchy of separators until each piece fits max_tokens."""
        if self.count_tokens(text) <= max_tokens:
            return [text.strip()] if text.strip() else []

        # Find first separator present in text
        chosen_sep = ""
        for sep in self.separators:
            if sep in text:
                chosen_sep = sep
                break

        if chosen_sep:
            splits = text.split(chosen_sep)
        else:
            # Character slice fallback
            mid = len(text) // 2
            splits = [text[:mid], text[mid:]]

        result: list[str] = []
        current_piece = ""

        for split in splits:
            candidate = f"{current_piece}{chosen_sep}{split}" if current_piece else split
            if self.count_tokens(candidate) <= max_tokens:
                current_piece = candidate
            else:
                if current_piece:
                    result.append(current_piece.strip())
                if self.count_tokens(split) > max_tokens:
                    # Sub-split oversized fragment
                    result.extend(self._split_text_recursively(split, max_tokens))
                    current_piece = ""
                else:
                    current_piece = split

        if current_piece.strip():
            result.append(current_piece.strip())

        return [r for r in result if r]

    def _calculate_overlap(
        self, texts: list[str], pages: set[int]
    ) -> tuple[list[str], set[int], int]:
        """Selects trailing texts that fit within chunk_overlap_tokens."""
        if self.chunk_overlap_tokens <= 0 or not texts:
            return [], set(), 0

        overlap_texts: list[str] = []
        overlap_tokens = 0

        # Scan backwards from end
        for t in reversed(texts):
            t_tokens = self.count_tokens(t)
            if overlap_tokens + t_tokens <= self.chunk_overlap_tokens:
                overlap_texts.insert(0, t)
                overlap_tokens += t_tokens
            else:
                break

        return overlap_texts, set(pages), overlap_tokens

    def _build_chunk(
        self,
        texts: list[str],
        chunk_index: int,
        parsed_doc: ParsedDocument,
        pages: set[int],
        sections: list[str],
        tenant_id: uuid.UUID | None,
        document_id: uuid.UUID | None,
    ) -> Chunk:
        """Constructs a Chunk with mandatory enriched metadata."""
        content = "\n\n".join(texts).strip()
        token_count = self.count_tokens(content)

        # Mandatory metadata fields
        mandatory_metadata: dict[str, Any] = {
            "tenant_id": str(tenant_id) if tenant_id else None,
            "document_id": str(document_id) if document_id else None,
            "filename": parsed_doc.source_filename,
            "chunk_index": chunk_index,
            "title": parsed_doc.title,
            "section_headings": list(sections),
            "page_numbers": sorted(list(pages)) if pages else [1],
            "token_count": token_count,
            "char_count": len(content),
            "file_type": parsed_doc.file_type,
        }

        # Include document-level metadata without overriding mandatory fields
        for k, v in parsed_doc.metadata.items():
            if k not in mandatory_metadata and v is not None:
                mandatory_metadata[k] = v

        return Chunk(
            content=content,
            chunk_index=chunk_index,
            metadata=mandatory_metadata,
            tenant_id=tenant_id,
            document_id=document_id,
        )
