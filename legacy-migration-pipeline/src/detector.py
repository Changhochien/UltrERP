"""
Encoding detection for legacy SQL dumps.
"""
import os
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class EncodingResult:
    encoding: str
    confidence: float
    has_taiwan_content: bool = False


# Taiwan-specific Big5 byte sequences
TAIWAN_PATTERNS = [
    (b"\xa4\xa4\xb5\xd8", "中華"),
    (b"\xa5\xc1\xb0\xea", "民國"),
    (b"\xa4\xbd\xa5\x71", "公司"),
    (b"\xc1`", "總"),
    (b"\xa8t\xb2\xce", "系統"),
    (b"\xba\xde\xb2z", "管理"),
]

# Encoding alias map for conversion
ENCODING_MAP = {
    "big5-hkscs": "big5hkscs",
    "cp950": "big5hkscs",
    "big5": "big5hkscs",
}


def has_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def check_taiwan_content(sample: bytes) -> Optional[EncodingResult]:
    """Check if sample contains Taiwan-specific content."""
    for pattern, _ in TAIWAN_PATTERNS:
        if pattern in sample:
            return EncodingResult(
                encoding="big5-hkscs",
                confidence=0.95,
                has_taiwan_content=True,
            )

    try:
        decoded = sample.decode("big5hkscs", errors="strict")
        if has_chinese(decoded):
            return EncodingResult(
                encoding="big5-hkscs",
                confidence=0.85,
                has_taiwan_content=True,
            )
    except (UnicodeDecodeError, LookupError):
        pass

    return None


class EncodingDetector:
    """
    Detect encoding from SQL dump content.
    Samples from multiple positions since data may appear after DDL.
    """

    def detect(self, content: bytes) -> EncodingResult:
        """
        Detect encoding from byte content.
        """
        file_size = len(content)

        sample_positions = [
            0,
            file_size // 4,
            file_size // 2,
            int(file_size * 0.7),
            int(file_size * 0.8),
        ]
        sample_size = min(50000, max(1000, file_size // 20))

        for pos in sample_positions:
            if pos >= file_size:
                continue
            sample = content[pos:pos + sample_size]
            result = check_taiwan_content(sample)
            if result:
                return result

        return EncodingResult(encoding="utf-8", confidence=0.7)

    def detect_from_file(self, filepath: str) -> EncodingResult:
        """Detect encoding by reading file in chunks."""
        file_size = os.path.getsize(filepath)

        # Sample from data section (after 1MB where DDL often ends)
        sample_positions = [1000000, file_size // 2, int(file_size * 0.7)]

        with open(filepath, "rb") as f:
            for pos in sample_positions:
                if pos >= file_size:
                    continue
                f.seek(pos)
                sample = f.read(50000)
                result = check_taiwan_content(sample)
                if result:
                    return result

        return EncodingResult(encoding="utf-8", confidence=0.7)

    def convert_to_utf8(self, content: bytes, encoding: str) -> str:
        """Convert content to UTF-8."""
        codec = ENCODING_MAP.get(encoding, encoding)
        return content.decode(codec, errors="replace")
