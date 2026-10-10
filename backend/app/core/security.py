"""Password hashing using bcrypt directly.

`passlib` is deliberately not used: it is unmaintained and broken against
current `bcrypt` releases (a value that this project fell over on before).
bcrypt itself truncates at 72 bytes, so both hashing and verification clip
the encoded password identically.
"""

import bcrypt

BCRYPT_MAX_BYTES = 72


def get_password_hash(password: str) -> str:
    encoded = password.encode("utf-8")[:BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        encoded = plain_password.encode("utf-8")[:BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(encoded, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False