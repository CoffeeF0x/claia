"""
Text utilities for processing text files.

Provides functions for:
- Encoding detection and conversion
- Text normalization
- Content validation
"""

import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def to_base64(text: str, encoding: str = 'utf-8') -> str:
    """
    Convert text to base64 string.
    
    Args:
        text: Text content
        encoding: Text encoding (default: utf-8)
        
    Returns:
        str: Base64-encoded string
    """
    text_bytes = text.encode(encoding)
    return base64.b64encode(text_bytes).decode('ascii')


def from_base64(base64_string: str, encoding: str = 'utf-8') -> str:
    """
    Convert base64 string to text.
    
    Args:
        base64_string: Base64-encoded text
        encoding: Text encoding (default: utf-8)
        
    Returns:
        str: Decoded text
    """
    text_bytes = base64.b64decode(base64_string)
    return text_bytes.decode(encoding)


def detect_encoding(content_bytes: bytes) -> str:
    """
    Detect encoding of text bytes.
    
    Attempts to detect the encoding, falling back to utf-8.
    
    Args:
        content_bytes: Raw text data
        
    Returns:
        str: Detected encoding name
    """
    try:
        import chardet
        result = chardet.detect(content_bytes)
        return result.get('encoding', 'utf-8') or 'utf-8'
    except ImportError:
        logger.debug("chardet not available, assuming utf-8")
        return 'utf-8'
    except Exception as e:
        logger.warning(f"Failed to detect encoding: {e}, assuming utf-8")
        return 'utf-8'


def convert_encoding(text: str, 
                     from_encoding: str, 
                     to_encoding: str = 'utf-8') -> Optional[str]:
    """
    Convert text from one encoding to another.
    
    Args:
        text: Text content
        from_encoding: Source encoding
        to_encoding: Target encoding (default: utf-8)
        
    Returns:
        Optional[str]: Converted text or None if conversion failed
    """
    try:
        # Encode to bytes with source encoding
        text_bytes = text.encode(from_encoding)
        # Decode with target encoding
        return text_bytes.decode(to_encoding)
    except Exception as e:
        logger.error(f"Failed to convert encoding from {from_encoding} to {to_encoding}: {e}")
        return None


def normalize_line_endings(text: str, line_ending: str = '\n') -> str:
    """
    Normalize line endings in text.
    
    Converts all line endings (\r\n, \r, \n) to the specified format.
    
    Args:
        text: Text content
        line_ending: Target line ending (default: \n)
        
    Returns:
        str: Text with normalized line endings
    """
    # Replace Windows line endings
    text = text.replace('\r\n', '\n')
    # Replace old Mac line endings
    text = text.replace('\r', '\n')
    # Convert to target line ending if not \n
    if line_ending != '\n':
        text = text.replace('\n', line_ending)
    return text


def truncate_text(text: str, 
                 max_length: int, 
                 ellipsis: str = '...') -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text content
        max_length: Maximum length including ellipsis
        ellipsis: String to append when truncating (default: '...')
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    # Account for ellipsis length
    truncate_at = max_length - len(ellipsis)
    if truncate_at <= 0:
        return ellipsis[:max_length]
    
    return text[:truncate_at] + ellipsis


def count_words(text: str) -> int:
    """
    Count words in text.
    
    Simple word counting by splitting on whitespace.
    
    Args:
        text: Text content
        
    Returns:
        int: Word count
    """
    return len(text.split())


def count_lines(text: str) -> int:
    """
    Count lines in text.
    
    Args:
        text: Text content
        
    Returns:
        int: Line count
    """
    return len(text.splitlines())


def extract_preview(text: str, 
                   max_lines: int = 10, 
                   max_chars: int = 500) -> str:
    """
    Extract a preview of text content.
    
    Takes the first N lines or M characters, whichever is shorter.
    
    Args:
        text: Text content
        max_lines: Maximum number of lines
        max_chars: Maximum number of characters
        
    Returns:
        str: Preview text
    """
    lines = text.splitlines()[:max_lines]
    preview = '\n'.join(lines)
    
    if len(preview) > max_chars:
        preview = truncate_text(preview, max_chars)
    
    return preview

