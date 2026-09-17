import base64
import hashlib
import re
from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


_URL_CREDENTIALS = re.compile(r"(?P<scheme>[a-z]+://)[^/@\s]+:[^/@\s]+@", re.IGNORECASE)
_SECRET_TAGS = re.compile(
    r"<(?P<tag>password|passwd|secretKey|userPassword)>[^<]*</(?P=tag)>", re.IGNORECASE
)


def redact(text: str) -> str:
    """Quita credenciales de URLs y de XML antes de guardar evidencia o logs."""
    text = _URL_CREDENTIALS.sub(r"\g<scheme>***:***@", text)
    return _SECRET_TAGS.sub(r"<\g<tag>>***</\g<tag>>", text)
