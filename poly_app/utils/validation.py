# poly_app/utils/validation.py
import re
from datetime import datetime
from typing import Optional

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_\-]{3,32}$")


def validate_email(email: str) -> bool:
    if not email:
        return False
    return bool(EMAIL_RE.match(email.strip()))


def validate_password(password: str, min_length: int = 6) -> bool:
    """
    Basic password validation.
    You can harden this later if needed.
    """
    if not password:
        return False
    password = password.strip()
    if len(password) < min_length:
        return False
    return True


def validate_username(username: str) -> bool:
    """
    Letters, numbers, underscore, dash; 3–32 chars.
    """
    if not username:
        return False
    return bool(USERNAME_RE.match(username.strip()))


def parse_date_yyyy_mm_dd(s: str) -> Optional[datetime.date]:
    """
    Parse 'YYYY-MM-DD' into a date, or return None.
    """
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def validate_rating(value: int) -> bool:
    """
    Rating must be an int 1–5.
    """
    try:
        v = int(value)
    except (TypeError, ValueError):
        return False
    return 1 <= v <= 5
