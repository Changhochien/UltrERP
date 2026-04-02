"""
Data cleaner - fixes mojibake and cleans Taiwan-specific data.
"""
import re
from typing import Optional

# Pre-compiled patterns
HEX_ESCAPE_PATTERN = re.compile(r'\\x[0-9a-fA-F]{2}')
CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')


class MojibakeCleaner:
    """
    Detect and fix mojibake in Chinese text.
    """

    REPLACEMENT_CHARS = ["\ufffd", "�"]
    MOJIBAKE_CHARS = ["¤", "¨", "¥", "§", "©", "®", "™"]

    @staticmethod
    def is_corrupted(text: str) -> bool:
        """Check if text has mojibake corruption."""
        if not isinstance(text, str):
            return False
        if any(c in text for c in MojibakeCleaner.REPLACEMENT_CHARS):
            return True
        if HEX_ESCAPE_PATTERN.search(text):
            return True
        return False

    @staticmethod
    def clean_text(text: str) -> str:
        """Remove mojibake corruption markers."""
        for char in MojibakeCleaner.REPLACEMENT_CHARS:
            text = text.replace(char, "")
        text = HEX_ESCAPE_PATTERN.sub("", text)
        text = re.sub(r'\s+', " ", text)
        return text.strip()

    @staticmethod
    def try_fixing_mojibake(text: str) -> str:
        """
        Attempt to fix mojibake by re-interpreting as Big5.
        """
        try:
            latin1_bytes = text.encode("latin1", errors="ignore")
            fixed = latin1_bytes.decode("big5hkscs", errors="ignore")
            if has_chinese(fixed):
                return fixed
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
        return text


def has_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return bool(CHINESE_PATTERN.search(text))


class TaiwanDataCleaner:
    """
    Clean Taiwan-specific data fields.
    """

    WHITESPACE_HYPHEN = re.compile(r'[\s\-]+')

    @staticmethod
    def clean_phone(phone: str) -> str:
        """Clean Taiwan phone number."""
        return re.sub(r'[\s\-\(\)]', "", phone)

    @staticmethod
    def clean_business_number(number: str) -> str:
        """Clean business number (統一編號)."""
        return TaiwanDataCleaner.WHITESPACE_HYPHEN.sub("", number)

    @staticmethod
    def format_roc_date(date_str: str) -> Optional[str]:
        """
        Convert ROC date to AD date.

        Example: 民國113年09月12日 -> 2024-09-12
        """
        patterns = [
            (r'民國(\d+)年(\d+)月(\d+)日', r'\1-\2-\3'),
            (r'(\d+)年(\d+)月(\d+)日', r'\1-\2-\3'),
            (r'(\d+)/(\d+)/(\d+)', r'\1-\2-\3'),
        ]

        for pattern, replacement in patterns:
            match = re.match(pattern, date_str.strip())
            if match:
                parts = match.groups()
                year = int(parts[0])
                # ROC year + 1911 = AD year
                if year < 1911:
                    year = year + 1911
                return f"{year}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"

        return None

    @staticmethod
    def clean_invoice_number(invoice: str) -> str:
        """Clean invoice number."""
        return TaiwanDataCleaner.WHITESPACE_HYPHEN.sub("", invoice)
