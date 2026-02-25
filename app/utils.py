"""Shared validation helpers."""

import re

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_DIGITS_RE = re.compile(r'\D')


def is_valid_email(value: str) -> bool:
    """Return True if *value* looks like a valid email address."""
    return bool(value and _EMAIL_RE.match(value.strip()))


def is_valid_phone(value: str) -> bool:
    """Return True if *value* contains 7–15 digits (international-friendly).

    Accepts any mix of digits, spaces, hyphens, parentheses, dots, and a
    leading +.  Strips all non-digit characters before counting.
    """
    if not value:
        return True  # phone is always optional; blank is fine
    digits = _DIGITS_RE.sub('', value.strip())
    return 7 <= len(digits) <= 15
