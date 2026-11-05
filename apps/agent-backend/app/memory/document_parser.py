import io
import re
from typing import List


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    """
    Split text into overlapping chunks of approximately `chunk_size` characters.
    Uses sentence-boundary-aware splitting for semantic coherence.
    """
    text = re.sub(r'\s+', ' ', text.strip())
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            # Try to break at sentence boundary
            boundary = text.rfind('. ', start, end)
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0

    return chunks


def parse_text(content: bytes) -> str:
    """Parse raw UTF-8 text bytes."""
    return content.decode("utf-8", errors="ignore")


def parse_pdf(content: bytes) -> str:
    """Extract text from PDF bytes using pypdf."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    except Exception as e:
        raise ValueError(f"PDF parsing failed: {e}")


def parse_docx(content: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(content))
        return "\n".join(para.text for para in doc.paragraphs)
    except Exception as e:
        raise ValueError(f"DOCX parsing failed: {e}")


def parse_document(filename: str, content: bytes) -> str:
    """Route document to appropriate parser based on file extension."""
    ext = filename.lower().rsplit(".", 1)[-1]
    parsers = {
        "txt": parse_text,
        "md": parse_text,
        "pdf": parse_pdf,
        "docx": parse_docx,
    }
    parser = parsers.get(ext)
    if not parser:
        raise ValueError(f"Unsupported file type: .{ext}")
    return parser(content)

